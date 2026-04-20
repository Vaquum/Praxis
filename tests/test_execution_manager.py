'''
Tests for praxis.core.execution_manager.ExecutionManager.
'''

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.events import CommandAccepted, OrderExpired, OrderSubmitIntent, OrderSubmitted, TradeOutcomeProduced
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import AccountNotRegisteredError, ExecutionManager
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    CancelResult,
    ImmediateFill,
    NotFoundError,
    OrderRejectedError,
    SubmitResult,
    TransientError,
    VenueAdapter,
)

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_PAST_TS = datetime(2020, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_ACCT2 = 'acc-2'
_TRADE = 'trade-1'
_EPOCH = 1

_CMD_KWARGS: dict[str, Any] = {
    'trade_id': _TRADE,
    'account_id': _ACCT,
    'symbol': 'BTCUSDT',
    'side': OrderSide.BUY,
    'qty': Decimal('1'),
    'order_type': OrderType.LIMIT,
    'execution_mode': ExecutionMode.SINGLE_SHOT,
    'execution_params': SingleShotParams(price=Decimal('50000')),
    'timeout': 300,
    'reference_price': None,
    'maker_preference': MakerPreference.NO_PREFERENCE,
    'stp_mode': STPMode.NONE,
    'created_at': _TS,
}



@pytest.fixture
def adapter() -> AsyncMock:
    '''Venue adapter mock with default no-fill success response.'''

    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.OPEN,
        immediate_fills=(),
    )
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine, adapter: AsyncMock
) -> AsyncGenerator[ExecutionManager, None]:
    em = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    yield em
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


class TestRegisterAccount:
    @pytest.mark.asyncio
    async def test_register_starts_task(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        runtime = mgr._accounts[_ACCT]
        assert runtime.task is not None
        assert not runtime.task.done()

    @pytest.mark.asyncio
    async def test_register_empty_account_id_raises(
        self, mgr: ExecutionManager
    ) -> None:
        with pytest.raises(ValueError, match='non-empty'):
            mgr.register_account('')

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        with pytest.raises(ValueError, match='already registered'):
            mgr.register_account(_ACCT)


class TestUnregisterAccount:
    @pytest.mark.asyncio
    async def test_unregister_cancels_task(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        task = mgr._accounts[_ACCT].task
        await mgr.unregister_account(_ACCT)
        assert _ACCT not in mgr._accounts
        assert task is not None
        assert task.done()

    @pytest.mark.asyncio
    async def test_unregister_unknown_raises(self, mgr: ExecutionManager) -> None:
        with pytest.raises(AccountNotRegisteredError, match='not registered'):
            await mgr.unregister_account('unknown')


class TestSubmitCommand:
    @pytest.mark.asyncio
    async def test_returns_uuid(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        uuid.UUID(command_id)

    @pytest.mark.asyncio
    async def test_unregistered_account_raises(self, mgr: ExecutionManager) -> None:
        with pytest.raises(AccountNotRegisteredError, match='not registered'):
            await mgr.submit_command(**_CMD_KWARGS)

    @pytest.mark.asyncio
    async def test_appends_command_accepted_to_spine(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        events = await spine.read(_EPOCH, after_seq=0)
        assert len(events) == 1
        _seq, event = events[0]
        assert isinstance(event, CommandAccepted)
        assert event.command_id == command_id
        assert event.trade_id == _TRADE

    @pytest.mark.asyncio
    async def test_enqueues_to_command_queue(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        runtime = mgr._accounts[_ACCT]
        assert runtime.command_queue.qsize() >= 1

    @pytest.mark.asyncio
    async def test_disallowed_order_type_raises_and_does_not_append_event(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        bad = {
            **_CMD_KWARGS,
            'execution_mode': ExecutionMode.ICEBERG,
            'order_type': OrderType.MARKET,
            'execution_params': SingleShotParams(),
        }
        with pytest.raises(ValueError, match='ICEBERG does not support'):
            await mgr.submit_command(**bad)
        events = await spine.read(_EPOCH, after_seq=0)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_records_accepted_command_mapping(
        self, mgr: ExecutionManager
    ) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        assert mgr._accepted_commands[command_id] == _ACCT


class TestSubmitAbort:
    @pytest.mark.asyncio
    async def test_enqueues_to_priority_queue(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='test',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        assert mgr._accounts[_ACCT].priority_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_unregistered_abort_account_raises(self, mgr: ExecutionManager) -> None:
        abort = TradeAbort(
            command_id='cmd-1',
            account_id='unknown',
            reason='test',
            created_at=_TS,
        )
        with pytest.raises(AccountNotRegisteredError, match='not registered'):
            mgr.submit_abort(abort)

    @pytest.mark.asyncio
    async def test_unknown_command_id_raises(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        abort = TradeAbort(
            command_id='cmd-unknown',
            account_id=_ACCT,
            reason='test',
            created_at=_TS,
        )
        with pytest.raises(ValueError, match='unknown command_id'):
            mgr.submit_abort(abort)

    @pytest.mark.asyncio
    async def test_terminal_command_is_noop(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        mgr._terminal_commands.add(command_id)
        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='test',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        assert mgr._accounts[_ACCT].priority_queue.qsize() == 0


class TestAccountLoop:
    @pytest.mark.asyncio
    async def test_priority_drained_before_command(
        self,
        mgr: ExecutionManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.INFO):
            mgr.register_account(_ACCT)
            runtime = mgr._accounts[_ACCT]

            abort = TradeAbort(
                command_id='cmd-abort',
                account_id=_ACCT,
                reason='test',
                created_at=_TS,
            )
            runtime.priority_queue.put_nowait(abort)

            await mgr.submit_command(**_CMD_KWARGS)

            await asyncio.sleep(0.3)

        messages = [r.message for r in caplog.records]
        abort_idx = next(
            (i for i, m in enumerate(messages) if 'abort received' in m),
            None,
        )
        cmd_idx = next(
            (i for i, m in enumerate(messages) if 'command dequeued' in m),
            None,
        )
        assert abort_idx is not None
        assert cmd_idx is not None
        assert abort_idx < cmd_idx


class TestIsolation:
    @pytest.mark.asyncio
    async def test_independent_queues(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        mgr.register_account(_ACCT2)

        kwargs2 = {**_CMD_KWARGS, 'account_id': _ACCT2}
        await mgr.submit_command(**_CMD_KWARGS)
        await mgr.submit_command(**kwargs2)

        rt1 = mgr._accounts[_ACCT]
        rt2 = mgr._accounts[_ACCT2]
        assert rt1.command_queue is not rt2.command_queue


class TestProcessCommand:
    @pytest.mark.asyncio
    async def test_market_fill_produces_submitted_and_fill(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-100',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-100',
                    qty=Decimal('1'),
                    price=Decimal('50000'),
                    fee=Decimal('0.001'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitted',
            'FillReceived',
            'TradeClosed',
            'TradeOutcomeProduced',
        ]

    @pytest.mark.asyncio
    async def test_limit_no_fill_produces_submitted_only(
        self, mgr: ExecutionManager, spine: EventSpine
    ) -> None:
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == ['CommandAccepted', 'OrderSubmitIntent', 'OrderSubmitted', 'TradeOutcomeProduced']

    @pytest.mark.asyncio
    async def test_venue_rejection_produces_submit_failed(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.side_effect = OrderRejectedError(
            'insufficient balance', venue_code=-1013, reason='insufficient balance'
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == ['CommandAccepted', 'OrderSubmitIntent', 'OrderSubmitFailed', 'TradeOutcomeProduced']

    @pytest.mark.asyncio
    async def test_transient_failure_produces_submit_failed(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.side_effect = TransientError('network timeout')
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == ['CommandAccepted', 'OrderSubmitIntent', 'OrderSubmitFailed', 'TradeOutcomeProduced']

    @pytest.mark.asyncio
    async def test_multiple_fills(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-200',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-201',
                    qty=Decimal('0.3'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0003'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
                ImmediateFill(
                    venue_trade_id='t-202',
                    qty=Decimal('0.3'),
                    price=Decimal('50010'),
                    fee=Decimal('0.0003'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
                ImmediateFill(
                    venue_trade_id='t-203',
                    qty=Decimal('0.4'),
                    price=Decimal('50020'),
                    fee=Decimal('0.0004'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitted',
            'FillReceived',
            'FillReceived',
            'FillReceived',
            'TradeClosed',
            'TradeOutcomeProduced',
        ]

    @pytest.mark.asyncio
    async def test_fill_dedup_skips_duplicate(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-300',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='dup-1',
                    qty=Decimal('0.5'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0005'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
                ImmediateFill(
                    venue_trade_id='dup-1',
                    qty=Decimal('0.5'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0005'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitted',
            'FillReceived',
            'TradeClosed',
            'TradeOutcomeProduced',
        ]

    @pytest.mark.asyncio
    async def test_client_order_id_matches_generator(
        self, mgr: ExecutionManager, spine: EventSpine
    ) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        submitted = next(e for _, e in events if isinstance(e, OrderSubmitted))
        expected = generate_client_order_id(
            ExecutionMode.SINGLE_SHOT, command_id, sequence=0
        )
        assert submitted.client_order_id == expected

    @pytest.mark.asyncio
    async def test_trading_state_has_closed_order_after_fill(
        self,
        mgr: ExecutionManager,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-400',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-400',
                    qty=Decimal('1'),
                    price=Decimal('50000'),
                    fee=Decimal('0.001'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        runtime = mgr._accounts[_ACCT]
        assert len(runtime.trading_state.closed_orders) > 0

    @pytest.mark.asyncio
    async def test_loop_continues_after_failure(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.side_effect = [
            TransientError('network down'),
            SubmitResult(
                venue_order_id='v-500',
                status=OrderStatus.OPEN,
                immediate_fills=(),
            ),
        ]
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await mgr.submit_command(**{**_CMD_KWARGS, 'trade_id': 'trade-2'})
        await asyncio.sleep(0.5)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'OrderSubmitFailed' in types
        assert 'OrderSubmitted' in types
        assert 'OrderSubmitIntent' in types


class TestTradeOutcome:
    @pytest.mark.asyncio
    async def test_filled_outcome_delivered_via_callback(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-o1',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-o1',
                    qty=Decimal('1'),
                    price=Decimal('50000'),
                    fee=Decimal('0.001'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.FILLED
        assert outcome.is_terminal

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_rejected_outcome_has_reason(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.side_effect = OrderRejectedError(
            'bad qty', venue_code=-1013, reason='bad qty'
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.REJECTED
        assert outcome.is_terminal
        assert outcome.reason is not None
        assert 'bad qty' in outcome.reason
        assert outcome.filled_qty == Decimal(0)
        assert outcome.avg_fill_price is None

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_pending_outcome_for_limit_no_fill(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.PENDING
        assert not outcome.is_terminal
        assert outcome.filled_qty == Decimal(0)
        assert outcome.avg_fill_price is None

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_partial_fill_outcome(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-p1',
            status=OrderStatus.PARTIALLY_FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-p1',
                    qty=Decimal('0.3'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0003'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.PARTIAL
        assert not outcome.is_terminal
        assert outcome.filled_qty == Decimal('0.3')
        assert outcome.avg_fill_price == Decimal('50000')

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_vwap_computation_multiple_fills(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-vw',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-vw1',
                    qty=Decimal('0.6'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0006'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
                ImmediateFill(
                    venue_trade_id='t-vw2',
                    qty=Decimal('0.4'),
                    price=Decimal('50100'),
                    fee=Decimal('0.0004'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        outcome: TradeOutcome = callback.call_args[0][0]
        notional = (
            Decimal('0.6') * Decimal('50000')
            + Decimal('0.4') * Decimal('50100')
        )
        expected_vwap = notional / Decimal('1')
        assert outcome.avg_fill_price == expected_vwap
        assert outcome.filled_qty == Decimal('1')

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_no_callback_does_not_raise(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'TradeOutcomeProduced' in types

    @pytest.mark.asyncio
    async def test_outcome_field_correctness(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-fc',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-fc',
                    qty=Decimal('1'),
                    price=Decimal('50000'),
                    fee=Decimal('0.001'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.command_id == command_id
        assert outcome.trade_id == _TRADE
        assert outcome.account_id == _ACCT
        assert outcome.target_qty == Decimal('1')
        assert outcome.slices_completed == 1
        assert outcome.slices_total == 1
        assert outcome.missed_iterations is None
        assert outcome.missed_reason is None
        assert outcome.created_at.tzinfo is not None

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_outcome_produced_event_in_spine(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        produced = [e for _, e in events if isinstance(e, TradeOutcomeProduced)]
        assert len(produced) == 1
        assert produced[0].command_id is not None
        assert produced[0].trade_id == _TRADE
        assert produced[0].status == TradeStatus.PENDING

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_overfill_clamped_with_correct_vwap(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-of',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-of1',
                    qty=Decimal('0.7'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0007'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
                ImmediateFill(
                    venue_trade_id='t-of2',
                    qty=Decimal('0.5'),
                    price=Decimal('50200'),
                    fee=Decimal('0.0005'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.filled_qty == Decimal('1')
        assert outcome.status == TradeStatus.FILLED
        unclamped_qty = Decimal('0.7') + Decimal('0.5')
        expected_vwap = (
            Decimal('0.7') * Decimal('50000')
            + Decimal('0.5') * Decimal('50200')
        ) / unclamped_qty
        assert outcome.avg_fill_price == expected_vwap

        await mgr.unregister_account(_ACCT)


class TestDeadlineHandling:
    @pytest.mark.asyncio
    async def test_pending_order_past_deadline_expires(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**{**_CMD_KWARGS, 'created_at': _PAST_TS})
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.EXPIRED
        assert outcome.is_terminal
        assert outcome.reason == 'deadline exceeded'
        assert outcome.filled_qty == Decimal(0)
        assert outcome.avg_fill_price is None

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_partial_fill_past_deadline_preserves_fill_data(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-dl',
            status=OrderStatus.PARTIALLY_FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-dl1',
                    qty=Decimal('0.3'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0003'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**{**_CMD_KWARGS, 'created_at': _PAST_TS})
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.EXPIRED
        assert outcome.is_terminal
        assert outcome.filled_qty == Decimal('0.3')
        assert outcome.avg_fill_price == Decimal('50000')
        assert outcome.reason == 'deadline exceeded'

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_expired_outcome_produced_event_in_spine(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**{**_CMD_KWARGS, 'created_at': _PAST_TS})
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        produced = [e for _, e in events if isinstance(e, TradeOutcomeProduced)]
        assert len(produced) == 1
        assert produced[0].status == TradeStatus.EXPIRED

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_expired_path_appends_order_expired(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**{**_CMD_KWARGS, 'created_at': _PAST_TS})
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        expired_events = [e for _, e in events if isinstance(e, OrderExpired)]
        assert len(expired_events) == 1
        adapter.cancel_order.assert_awaited_once()

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_expired_path_not_found_still_emits_order_expired(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.cancel_order.side_effect = NotFoundError('order not found')
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**{**_CMD_KWARGS, 'created_at': _PAST_TS})
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        expired_events = [e for _, e in events if isinstance(e, OrderExpired)]
        assert len(expired_events) == 1

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_expired_path_venue_error_skips_order_expired(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        adapter.cancel_order.side_effect = TransientError('network timeout')
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**{**_CMD_KWARGS, 'created_at': _PAST_TS})
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        expired_events = [e for _, e in events if isinstance(e, OrderExpired)]
        assert len(expired_events) == 0

        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.EXPIRED
        assert 'cancel failed' in (outcome.reason or '')

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_expired_command_is_terminal_for_abort(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**{**_CMD_KWARGS, 'created_at': _PAST_TS})
        await asyncio.sleep(0.3)

        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.EXPIRED

        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='user cancel',
            created_at=datetime.now(UTC),
        )
        mgr.submit_abort(abort)
        callback.assert_awaited_once()
        adapter.cancel_order.assert_awaited_once()
        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_non_expired_command_within_deadline(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.PENDING
        assert not outcome.is_terminal
        adapter.cancel_order.assert_not_awaited()

        await mgr.unregister_account(_ACCT)


class TestProcessAbort:
    @pytest.mark.asyncio
    async def test_abort_pending_order_produces_canceled(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='user requested',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitted',
            'TradeOutcomeProduced',
            'OrderCanceled',
            'TradeOutcomeProduced',
        ]

        outcomes = [call.args[0] for call in callback.call_args_list]
        assert len(outcomes) == 2
        assert outcomes[0].status == TradeStatus.PENDING
        assert outcomes[1].status == TradeStatus.CANCELED
        assert outcomes[1].is_terminal
        assert outcomes[1].filled_qty == Decimal(0)
        assert outcomes[1].avg_fill_price is None

        adapter.cancel_order.assert_awaited_once()

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_abort_partial_fill_preserves_fill_data(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-pf',
            status=OrderStatus.PARTIALLY_FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-pf1',
                    qty=Decimal('0.3'),
                    price=Decimal('50000'),
                    fee=Decimal('0.0003'),
                    fee_asset='BTC',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='timeout',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitted',
            'FillReceived',
            'TradeOutcomeProduced',
            'OrderCanceled',
            'TradeClosed',
            'TradeOutcomeProduced',
        ]

        outcomes = [call.args[0] for call in callback.call_args_list]
        canceled = outcomes[1]
        assert canceled.status == TradeStatus.CANCELED
        assert canceled.filled_qty == Decimal('0.3')
        assert canceled.avg_fill_price == Decimal('50000')

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_abort_not_found_still_emits_order_canceled(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        adapter.cancel_order.side_effect = NotFoundError('order gone')
        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='stale cancel',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'OrderCanceled' in types

        outcomes = [call.args[0] for call in callback.call_args_list]
        assert outcomes[1].status == TradeStatus.CANCELED

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_abort_venue_error_skips_order_canceled(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        adapter.cancel_order.side_effect = TransientError('cancel timeout')
        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='abort reason',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'OrderCanceled' not in types

        outcomes = [call.args[0] for call in callback.call_args_list]
        canceled = outcomes[1]
        assert canceled.status == TradeStatus.CANCELED
        assert 'abort reason' in canceled.reason
        assert 'cancel failed' in canceled.reason

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_pre_submission_abort_skips_venue_call(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='user cancelled before submission',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        await asyncio.sleep(0.3)

        adapter.submit_order.assert_not_awaited()
        adapter.cancel_order.assert_not_awaited()

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.CANCELED
        assert outcome.filled_qty == Decimal(0)
        assert outcome.reason == 'user cancelled before submission'

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'OrderSubmitIntent' not in types
        assert 'OrderSubmitted' not in types

        await mgr.unregister_account(_ACCT)


class TestModeDispatch:
    @pytest.mark.asyncio
    async def test_unsupported_mode_produces_rejected_outcome(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        kwargs = {**_CMD_KWARGS, 'execution_mode': ExecutionMode.TWAP}
        await mgr.submit_command(**kwargs)

        await asyncio.sleep(0.3)

        adapter.submit_order.assert_not_awaited()

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.REJECTED
        assert outcome.filled_qty == Decimal(0)
        assert outcome.reason is not None
        assert 'TWAP' in outcome.reason
        assert 'not yet supported' in outcome.reason

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'TradeOutcomeProduced' in types
        assert 'OrderSubmitIntent' not in types

        await mgr.unregister_account(_ACCT)


class TestStopLimitPassthrough:
    @pytest.mark.asyncio
    async def test_oco_stop_limit_price_reaches_intent_and_venue(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-oco',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        oco_params = SingleShotParams(
            price=Decimal('50000'),
            stop_price=Decimal('48000'),
            stop_limit_price=Decimal('47500'),
        )
        await mgr.submit_command(
            **{**_CMD_KWARGS, 'order_type': OrderType.OCO, 'execution_params': oco_params},
        )

        await asyncio.sleep(0.3)

        adapter.submit_order.assert_awaited_once()
        call_kwargs = adapter.submit_order.call_args
        assert call_kwargs.kwargs['stop_limit_price'] == Decimal('47500')
        assert call_kwargs.kwargs['stop_price'] == Decimal('48000')
        assert call_kwargs.kwargs['price'] == Decimal('50000')

        events = await spine.read(_EPOCH, after_seq=0)
        intents = [e for _, e in events if isinstance(e, OrderSubmitIntent)]
        assert len(intents) == 1
        assert intents[0].stop_limit_price == Decimal('47500')
        assert intents[0].stop_price == Decimal('48000')
        assert intents[0].price == Decimal('50000')

        await mgr.unregister_account(_ACCT)


class TestOcoAbortRouting:
    @pytest.mark.asyncio
    async def test_abort_oco_calls_cancel_order_list(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-oco',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        adapter.cancel_order_list.return_value = CancelResult(
            venue_order_id='v-oco',
            status=OrderStatus.CANCELED,
        )
        mgr.register_account(_ACCT)
        oco_params = SingleShotParams(
            price=Decimal('50000'),
            stop_price=Decimal('48000'),
            stop_limit_price=Decimal('47500'),
        )
        command_id = await mgr.submit_command(
            **{**_CMD_KWARGS, 'order_type': OrderType.OCO, 'execution_params': oco_params},
        )

        await asyncio.sleep(0.3)

        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='oco abort',
            created_at=_TS,
        )
        mgr.submit_abort(abort)

        await asyncio.sleep(0.3)

        adapter.cancel_order_list.assert_awaited_once()
        adapter.cancel_order.assert_not_awaited()

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_abort_succeeds_after_restart_replay(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Abort works for orders replayed from spine after restart.'''

        command_id = 'cmd-replay-1'
        trade_id = 'trade-replay-1'
        client_order_id = 'SS-replay-00'

        await spine.append(CommandAccepted(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
        ), _EPOCH)
        await spine.append(OrderSubmitIntent(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
            client_order_id=client_order_id, symbol='BTCUSDT',
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            qty=Decimal('1'), price=Decimal('50000'),
            stop_price=None, stop_limit_price=None,
        ), _EPOCH)
        await spine.append(OrderSubmitted(
            account_id=_ACCT, timestamp=_TS,
            client_order_id=client_order_id, venue_order_id='v-replay-1',
        ), _EPOCH)

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)

        events = await spine.read(_EPOCH, after_seq=0)
        account_events = [(s, e) for s, e in events if e.account_id == _ACCT]
        mgr.replay_events(_ACCT, account_events)

        abort = TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='abort after restart',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        await asyncio.sleep(0.15)

        adapter.cancel_order.assert_awaited_once_with(
            _ACCT, 'BTCUSDT', client_order_id=client_order_id,
        )

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.CANCELED
        assert outcome.command_id == command_id
        assert outcome.trade_id == trade_id
        assert outcome.is_terminal

        await mgr.unregister_account(_ACCT)
