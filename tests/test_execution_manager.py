'''
Tests for praxis.core.execution_manager.ExecutionManager.
'''

from __future__ import annotations

import ast
import asyncio
import logging
import pathlib
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from collections.abc import AsyncGenerator
from typing import Any, ClassVar
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
from praxis.core.domain.events import (
    CommandAccepted,
    FillReceived,
    FundTransaction,
    OrderCanceled,
    OrderExpired,
    OrderRejected,
    OrderSubmitIntent,
    OrderSubmitted,
    RegisterAccount,
    SchemeInitialized,
    TradeOutcomeProduced,
)
from praxis.core.account_ledger import CostBasisMethod
from praxis.core.domain.chart_of_accounts import Account
from praxis.core.domain.order import Order
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.domain.interval_slice_params import IntervalSliceParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import (
    AccountNotRegisteredError,
    ExecutionManager,
    ExecutionModeNotEnabledError,
)
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.infrastructure.event_spine import EventSpine
from praxis.trading_inbound import TradingInbound
from praxis.infrastructure.secret_store import Credentials
from praxis.infrastructure.venue_adapter import (
    OrderBookLevel,
    OrderBookSnapshot,
    CancelResult,
    ImmediateFill,
    NotFoundError,
    OrderRejectedError,
    SubmitResult,
    SymbolFilters,
    TransientError,
    VenueAdapter,
)

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_PAST_TS = datetime(2020, 1, 1, tzinfo=UTC)
_LONG_ID_VERBATIM = 'cmd-0123456789abcdef0123456789abcdef'
_LONG_ID_DUP = 'cmd-dup00000000000000000000000000000'
_LONG_ID_RACE = 'cmd-race0000000000000000000000000000'
_LONG_ID_A = 'cmd-a000000000000000000000000000000a'
_LONG_ID_B = 'cmd-b000000000000000000000000000000b'
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
    mock.cached_filters.return_value = None
    mock.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('2')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('2')),),
        last_update_id=1,
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
    async def test_live_submit_records_strategy_attribution(
        self,
        mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS, strategy_id='strat_001')

        trading_state = mgr._accounts[_ACCT].trading_state

        assert trading_state.trade_strategy_ids[_CMD_KWARGS['trade_id']] == 'strat_001'

    @pytest.mark.asyncio
    async def test_live_submit_without_strategy_records_nothing(
        self,
        mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)

        assert mgr._accounts[_ACCT].trading_state.trade_strategy_ids == {}

    @pytest.mark.asyncio
    async def test_caller_supplied_command_id_used_verbatim(
        self,
        mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(
            **_CMD_KWARGS,
            command_id=_LONG_ID_VERBATIM,
        )
        assert command_id == _LONG_ID_VERBATIM
        assert mgr._accepted_commands[_LONG_ID_VERBATIM] == _ACCT
        assert _LONG_ID_VERBATIM in mgr._commands

    @pytest.mark.asyncio
    async def test_empty_caller_supplied_command_id_raises(
        self,
        mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        with pytest.raises(ValueError, match='non-empty'):
            await mgr.submit_command(**_CMD_KWARGS, command_id='')

    @pytest.mark.asyncio
    async def test_short_caller_supplied_command_id_rejected_before_accept(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        with pytest.raises(ValueError, match='at least 16 characters'):
            await mgr.submit_command(**_CMD_KWARGS, command_id='cmd-short-1')

        assert 'cmd-short-1' not in mgr._accepted_commands
        events = await spine.read(_EPOCH, after_seq=0)
        assert events == []

    @pytest.mark.asyncio
    async def test_duplicate_caller_supplied_command_id_raises(
        self,
        mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS, command_id=_LONG_ID_DUP)
        with pytest.raises(ValueError, match='already in use'):
            await mgr.submit_command(**_CMD_KWARGS, command_id=_LONG_ID_DUP)

    @pytest.mark.asyncio
    async def test_concurrent_same_command_id_exactly_one_wins(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        results = await asyncio.gather(
            mgr.submit_command(**_CMD_KWARGS, command_id=_LONG_ID_RACE),
            mgr.submit_command(**_CMD_KWARGS, command_id=_LONG_ID_RACE),
            return_exceptions=True,
        )
        winners = [r for r in results if isinstance(r, str)]
        losers = [r for r in results if isinstance(r, ValueError)]
        assert len(winners) == 1
        assert len(losers) == 1
        events = await spine.read(_EPOCH, after_seq=0)
        accepted = [e for _seq, e in events if isinstance(e, CommandAccepted)]
        assert len(accepted) == 1

    @pytest.mark.asyncio
    async def test_failed_spine_append_frees_reserved_command_id(
        self,
        mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        original_append = mgr._event_spine.append

        async def _boom(_event: object, _epoch_id: int) -> None:
            msg = 'synthetic spine failure'
            raise OSError(msg)

        mgr._event_spine.append = _boom
        try:
            with pytest.raises(OSError, match='synthetic'):
                await mgr.submit_command(
                    **_CMD_KWARGS,
                    command_id=_LONG_ID_A,
                )
            assert _LONG_ID_A not in mgr._accepted_commands
        finally:
            mgr._event_spine.append = original_append

        command_id = await mgr.submit_command(
            **_CMD_KWARGS,
            command_id=_LONG_ID_A,
        )
        assert command_id == _LONG_ID_A

    @pytest.mark.asyncio
    async def test_cancelled_append_frees_reserved_command_id(
        self,
        mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        original_append = mgr._event_spine.append
        entered = asyncio.Event()
        gate = asyncio.Event()

        async def _stall(_event: object, _epoch_id: int) -> None:
            entered.set()
            await gate.wait()

        mgr._event_spine.append = _stall
        try:
            task = asyncio.create_task(
                mgr.submit_command(**_CMD_KWARGS, command_id=_LONG_ID_B),
            )
            await entered.wait()
            assert _LONG_ID_B in mgr._accepted_commands

            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            assert _LONG_ID_B not in mgr._accepted_commands
        finally:
            mgr._event_spine.append = original_append

        command_id = await mgr.submit_command(
            **_CMD_KWARGS,
            command_id=_LONG_ID_B,
        )
        assert command_id == _LONG_ID_B

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
            'execution_params': IcebergParams(
                display_qty=Decimal('0.1'), limit_price=Decimal('50000'),
            ),
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
            (i for i, m in enumerate(messages) if 'priority control received' in m),
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
    async def test_quote_native_filled_status_with_zero_fills_defers(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Rescue-path zero-fill regression.

        When the venue (or the rescue path) returns
        `status=FILLED` with `immediate_fills=()` on a quote-native
        command, the terminal flip must defer to WS reconcile rather
        than emit a zero-fill `FILLED` outcome that suppresses the
        real fills. Pinning the gate at `filled_qty > _ZERO`.
        '''

        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-quote-rescue',
            status=OrderStatus.FILLED,
            immediate_fills=(),
        )
        quote_native_kwargs = {
            **_CMD_KWARGS,
            'qty': None,
            'quote_qty': Decimal('100'),
            'order_type': OrderType.MARKET,
            'execution_params': SingleShotParams(),
        }
        mgr.register_account(_ACCT)
        await mgr.submit_command(**quote_native_kwargs)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'OrderQuoteNativeFilled' not in types

        outcome_events = [e for _, e in events if type(e).__name__ == 'TradeOutcomeProduced']
        assert len(outcome_events) == 1
        assert outcome_events[0].status != TradeStatus.FILLED

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

        expected_notional = (
            Decimal('0.7') * Decimal('50000')
            + Decimal('0.3') * Decimal('50200')
        )
        assert outcome.cumulative_notional == expected_notional
        assert outcome.avg_fill_price == expected_notional / Decimal('1')

        scaled_notional = (
            (Decimal('0.7') * Decimal('50000') + Decimal('0.5') * Decimal('50200'))
            * Decimal('1')
            / (Decimal('0.7') + Decimal('0.5'))
        )
        assert outcome.cumulative_notional != scaled_notional, (
            'scaling the whole notional down to the clamped quantity reports '
            'the VWAP of fills that were not all admitted, and can land below '
            'a notional already published for an earlier partial, which makes '
            'the incremental delta negative and drops the terminal outcome'
        )
        derived_avg = outcome.cumulative_notional / outcome.filled_qty
        assert derived_avg == outcome.avg_fill_price, (
            f'cumulative_notional / filled_qty must round-trip to '
            f'avg_fill_price; got {derived_avg} expected {outcome.avg_fill_price}'
        )

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
    async def test_misrouted_non_single_shot_mode_is_rejected_defensively(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Every execution mode is routed by the account loop before it can
        reach `_process_command`; this asserts the defensive backstop that
        rejects a non-single-shot command that somehow reaches the
        single-shot path (a routing bug) rather than mis-executing it.'''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)
        runtime = mgr._accounts[_ACCT]
        cmd = TradeCommand(
            command_id='cmd-misrouted-0001',
            trade_id=_TRADE,
            account_id=_ACCT,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            order_type=OrderType.MARKET,
            execution_mode=ExecutionMode.TWAP,
            execution_params=IntervalSliceParams(num_slices=4, interval_seconds=10),
            timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE,
            created_at=_TS,
        )

        outcome = await mgr._process_command(runtime, cmd)

        adapter.submit_order.assert_not_awaited()
        assert outcome.status == TradeStatus.REJECTED
        assert outcome.filled_qty == Decimal(0)
        assert outcome.reason is not None
        assert 'TWAP' in outcome.reason
        assert 'misrouted' in outcome.reason

        await mgr.unregister_account(_ACCT)


class TestCapabilityGate:
    _TWAP_KWARGS: ClassVar[dict[str, Any]] = {
        **_CMD_KWARGS,
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.TWAP,
        'execution_params': IntervalSliceParams(num_slices=4, interval_seconds=10),
    }

    @pytest.mark.asyncio
    async def test_disabled_mode_rejected_when_gate_configured(
        self, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
            enabled_modes=frozenset({ExecutionMode.SINGLE_SHOT}),
        )
        mgr.register_account(_ACCT)

        with pytest.raises(ExecutionModeNotEnabledError, match='TWAP'):
            await mgr.submit_command(**self._TWAP_KWARGS)

        adapter.submit_order.assert_not_awaited()
        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_no_gate_allows_any_mode(
        self, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)

        command_id = await mgr.submit_command(**self._TWAP_KWARGS)
        uuid.UUID(command_id)

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_enabled_mode_accepted(
        self, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
            enabled_modes=frozenset({ExecutionMode.TWAP}),
        )
        mgr.register_account(_ACCT)

        command_id = await mgr.submit_command(**self._TWAP_KWARGS)
        uuid.UUID(command_id)

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_single_shot_always_enabled(
        self, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
            enabled_modes=frozenset({ExecutionMode.TWAP}),
        )
        mgr.register_account(_ACCT)

        command_id = await mgr.submit_command(**_CMD_KWARGS)
        uuid.UUID(command_id)

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

    @pytest.mark.asyncio
    async def test_ws_fill_after_replay_reaches_callback(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''After a Praxis restart, `replay_events` must repopulate
        `_commands` so subsequent WS fills on resting LIMIT orders reach
        `_on_trade_outcome`. Pre-fix `_emit_ws_outcome` returned silently
        on `cmd is None` and Nexus never learned of post-restart fills
        until the next reboot's reconcile (where the size-mismatch path
        is also broken — see Vaquum/Nexus#46 BLOCKER-F).
        '''

        command_id = 'cmd-replay-fill-1'
        trade_id = 'trade-replay-fill-1'
        client_order_id = 'SS-replay-fill-00'

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
            client_order_id=client_order_id, venue_order_id='v-replay-fill-1',
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

        assert command_id in mgr._commands
        assert mgr._commands[command_id].trade_id == trade_id
        assert mgr._commands[command_id].qty == Decimal('1')

        fill = FillReceived(
            account_id=_ACCT, timestamp=_TS,
            client_order_id=client_order_id,
            venue_order_id='v-replay-fill-1',
            venue_trade_id='vt-replay-fill-1',
            trade_id=trade_id, command_id=command_id,
            symbol='BTCUSDT', side=OrderSide.BUY,
            qty=Decimal('1'), price=Decimal('50000'),
            fee=Decimal('0.05'), fee_asset='USDT', is_maker=True,
        )
        mgr.enqueue_ws_event(_ACCT, fill)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.FILLED
        assert outcome.command_id == command_id
        assert outcome.trade_id == trade_id
        assert outcome.filled_qty == Decimal('1')
        assert outcome.is_terminal

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_replay_does_not_repopulate_commands_for_terminal(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Replayed commands that already reached a terminal status on
        the spine must NOT enter `_commands` (memory bound + dedup).
        `_terminal_commands` membership is the gate.
        '''

        command_id = 'cmd-replay-terminal'
        trade_id = 'trade-replay-terminal'
        client_order_id = 'SS-replay-terminal-00'

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
        await spine.append(TradeOutcomeProduced(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
            status=TradeStatus.FILLED, reason=None,
        ), _EPOCH)

        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=AsyncMock(),
        )
        mgr.register_account(_ACCT)

        events = await spine.read(_EPOCH, after_seq=0)
        account_events = [(s, e) for s, e in events if e.account_id == _ACCT]
        mgr.replay_events(_ACCT, account_events)

        assert command_id in mgr._terminal_commands
        assert command_id not in mgr._commands

        await mgr.unregister_account(_ACCT)


class TestEmitWsOutcome:
    '''A LIMIT order whose initial submit returns no immediate fills
    leaves the command in PENDING after `_process_command`. Subsequent
    venue WS fills (`FillReceived`) and terminal events
    (`OrderCanceled` / `OrderRejected` / `OrderExpired`) must surface
    a `TradeOutcome` aggregate via `_on_trade_outcome` so the
    launcher's translator → Nexus queue → OutcomeProcessor chain can
    update Nexus capital and position state.
    '''

    @pytest.mark.asyncio
    async def test_ws_partial_fill_emits_partial_outcome(
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
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**{**_CMD_KWARGS, 'qty': Decimal('2')})
        await asyncio.sleep(0.3)

        callback.reset_mock()

        runtime = mgr._accounts[_ACCT]
        coid = next(iter(runtime.trading_state.orders))
        fill = FillReceived(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=coid,
            venue_order_id='v-o1',
            venue_trade_id='t-1',
            trade_id=_TRADE,
            command_id=command_id,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            price=Decimal('50000'),
            fee=Decimal('0.05'),
            fee_asset='USDT',
            is_maker=True,
        )
        mgr.enqueue_ws_event(_ACCT, fill)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.PARTIAL
        assert outcome.command_id == command_id
        assert outcome.filled_qty == Decimal('1')
        assert outcome.avg_fill_price == Decimal('50000')
        assert not outcome.is_terminal

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_ws_full_fill_emits_filled_terminal_outcome(
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
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.reset_mock()

        runtime = mgr._accounts[_ACCT]
        coid = next(iter(runtime.trading_state.orders))
        fill = FillReceived(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=coid,
            venue_order_id='v-o1',
            venue_trade_id='t-1',
            trade_id=_TRADE,
            command_id=command_id,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            price=Decimal('50000'),
            fee=Decimal('0.05'),
            fee_asset='USDT',
            is_maker=True,
        )
        mgr.enqueue_ws_event(_ACCT, fill)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.FILLED
        assert outcome.command_id == command_id
        assert outcome.filled_qty == Decimal('1')
        assert outcome.avg_fill_price == Decimal('50000')
        assert outcome.is_terminal

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_ws_cancel_after_partial_emits_canceled_with_filled_qty(
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
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**{**_CMD_KWARGS, 'qty': Decimal('2')})
        await asyncio.sleep(0.3)

        runtime = mgr._accounts[_ACCT]
        coid = next(iter(runtime.trading_state.orders))

        partial = FillReceived(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=coid,
            venue_order_id='v-o1',
            venue_trade_id='t-1',
            trade_id=_TRADE,
            command_id=command_id,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            price=Decimal('50000'),
            fee=Decimal('0.05'),
            fee_asset='USDT',
            is_maker=True,
        )
        cancel = OrderCanceled(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=coid,
            venue_order_id='v-o1',
            reason='user_canceled',
        )
        mgr.enqueue_ws_event(_ACCT, partial)
        mgr.enqueue_ws_event(_ACCT, cancel)
        await asyncio.sleep(0.3)

        statuses = [
            (call.args[0].status, call.args[0].command_id, call.args[0].filled_qty)
            for call in callback.call_args_list
            if call.args[0].command_id == command_id
        ]
        assert (TradeStatus.PARTIAL, command_id, Decimal('1')) in statuses
        assert (TradeStatus.CANCELED, command_id, Decimal('1')) in statuses

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_ws_expired_emits_expired_terminal_outcome(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''A WS-driven `OrderExpired` for a still-open LIMIT command
        must emit a terminal `TradeOutcome` with `EXPIRED` status and
        `reason=None` (the EXPIRED branch of `_emit_ws_outcome` carries
        no venue reason, distinct from REJECTED which forwards
        `event.reason`).
        '''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-o1',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.reset_mock()

        runtime = mgr._accounts[_ACCT]
        coid = next(iter(runtime.trading_state.orders))
        expired = OrderExpired(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=coid,
            venue_order_id='v-o1',
        )
        mgr.enqueue_ws_event(_ACCT, expired)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.EXPIRED
        assert outcome.command_id == command_id
        assert outcome.reason is None
        assert outcome.is_terminal

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_ws_rejected_emits_rejected_terminal_outcome(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''A WS-driven `OrderRejected` for a still-open LIMIT command
        must emit a terminal `TradeOutcome` with `REJECTED` status and
        `reason=event.reason` (forwarded from venue). Distinct from
        `EXPIRED` which carries no reason. The greybeard fix hardened
        this branch with an explicit `elif isinstance` + `RuntimeError`
        guard against silent fallthrough.
        '''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-o1',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.reset_mock()

        runtime = mgr._accounts[_ACCT]
        coid = next(iter(runtime.trading_state.orders))
        rejected = OrderRejected(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=coid,
            venue_order_id='v-o1',
            reason='post_ack_risk_reject',
        )
        mgr.enqueue_ws_event(_ACCT, rejected)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.status == TradeStatus.REJECTED
        assert outcome.command_id == command_id
        assert outcome.reason == 'post_ack_risk_reject'
        assert outcome.is_terminal

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_ws_overfill_clamps_emitted_filled_qty(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''If the order projection's `filled_qty` exceeds `cmd.qty`
        (duplicate / out-of-order venue fills, venue rounding past
        target), `_emit_ws_outcome` must clamp the emitted `filled_qty`
        to `cmd.qty` before calling `_build_outcome`. Pre-fix the
        unclamped value would trip `TradeOutcome.__post_init__`'s
        `filled_qty <= target_qty` invariant and raise, the
        `_account_loop` would log+drop, and Nexus would never see
        the outcome.
        '''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-o1',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.reset_mock()

        runtime = mgr._accounts[_ACCT]
        coid = next(iter(runtime.trading_state.orders))
        overfill = FillReceived(
            account_id=_ACCT, timestamp=_TS,
            client_order_id=coid, venue_order_id='v-o1',
            venue_trade_id='t-overfill',
            trade_id=_TRADE, command_id=command_id,
            symbol='BTCUSDT', side=OrderSide.BUY,
            qty=Decimal('5'), price=Decimal('50000'),
            fee=Decimal('0.05'), fee_asset='USDT', is_maker=True,
        )
        mgr.enqueue_ws_event(_ACCT, overfill)
        await asyncio.sleep(0.3)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.filled_qty == Decimal('1')
        assert outcome.target_qty == Decimal('1')
        assert outcome.cumulative_notional == Decimal('1') * Decimal('50000'), (
            f'The overfill admits only the increment that fits, carrying that '
            f'slice notional. Forwarding the venue cumulative verbatim kept '
            f'the cumulative monotonic — the PR #85 round-6 concern — but made '
            f'the implied average the notional of every fill over the accepted '
            f'size, which reported 250000 for a fill that happened at 50000. '
            f'Scaling the snapshot instead reports the right average and makes '
            f'the cumulative fall below an earlier PARTIAL, which is the '
            f'negative delta_notional that drops the terminal outcome. '
            f'Admitting per increment holds both: see '
            f'test_ws_partial_then_overfill_keeps_cumulative_monotonic for the '
            f'monotonicity this no longer gets for free. '
            f'got cumulative_notional={outcome.cumulative_notional}'
        )
        assert outcome.avg_fill_price == Decimal('50000')

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('name', 'fills', 'expected'),
        [
            (
                'one fill overshooting the target',
                [(Decimal('5'), Decimal('50000'))],
                (Decimal('1'), Decimal('50000')),
            ),
            (
                'a partial then a fill overshooting the remainder',
                [
                    (Decimal('0.5'), Decimal('50000')),
                    (Decimal('4.5'), Decimal('50000')),
                ],
                (Decimal('1'), Decimal('50000')),
            ),
            (
                'a partial then an overshoot after the price fell',
                [
                    (Decimal('0.5'), Decimal('50000')),
                    (Decimal('4.5'), Decimal('16000')),
                ],
                (Decimal('1'), Decimal('25000') + Decimal('0.5') * Decimal('16000')),
            ),
            (
                'a duplicate arriving once already at target',
                [
                    (Decimal('1'), Decimal('50000')),
                    (Decimal('1'), Decimal('50000')),
                ],
                (Decimal('1'), Decimal('50000')),
            ),
            (
                'many small fills totalling more than the target',
                [(Decimal('0.4'), Decimal('50000'))] * 4,
                (Decimal('1'), Decimal('50000')),
            ),
        ],
        ids=lambda v: v if isinstance(v, str) else '',
    )
    async def test_admitted_fill_totals_stop_at_the_target(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
        name: str,
        fills: list[tuple[Decimal, Decimal]],
        expected: tuple[Decimal, Decimal],
    ) -> None:
        '''Admission is a property of the fills, not of how they are observed.

        Each fill is admitted as far as the target allows, at its own price.
        The excess is discarded rather than capped after the fact, so the
        quantity holds the invariant, the notional never falls, and the
        implied average is the price of what was taken.
        '''

        del name

        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        runtime = mgr._accounts[_ACCT]
        command_id = 'cmd-admit'
        mgr._install_command(command_id, TradeCommand(
            command_id=command_id, trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('1'),
            order_type=OrderType.MARKET, execution_mode=ExecutionMode.TWAP,
            execution_params=IntervalSliceParams(num_slices=4, interval_seconds=10),
            timeout=300, reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        ))

        seen: list[Decimal] = []

        for index, (qty, price) in enumerate(fills):
            mgr._accumulate_accepted_fill(
                runtime,
                FillReceived(
                    account_id=_ACCT, timestamp=_TS, client_order_id=f'c-{index}',
                    venue_order_id=f'v-{index}', venue_trade_id=f'vt-{index}',
                    trade_id=_TRADE, command_id=command_id, symbol='BTCUSDT',
                    side=OrderSide.BUY, qty=qty, price=price, fee=Decimal('0'),
                    fee_asset='USDT', is_maker=False,
                ),
            )
            accepted_qty, accepted_notional = runtime.accepted_fill_totals[command_id]

            assert accepted_qty <= Decimal('1')

            seen.append(accepted_notional)

        assert runtime.accepted_fill_totals[command_id] == expected
        assert seen == sorted(seen)

    @pytest.mark.asyncio
    async def test_quote_native_fills_are_capped_on_spend(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''A quote-native command budgets spend, so spend is what caps it.

        Exempting quote-native orders from admission relocates the overfill
        to the one order type where notional is the controlled variable.
        The admitted quantity follows from the spend that fit, at the price
        that executed, so notional over quantity stays the real average.
        '''

        command = TradeCommand(
            command_id='cmd-quote', trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.BUY, qty=None,
            quote_qty=Decimal('1000'),
            order_type=OrderType.MARKET, execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(), timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        )
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        mgr._install_command('cmd-quote', command)
        runtime = mgr._accounts[_ACCT]

        for index, (qty, price) in enumerate(
            [(Decimal('0.01'), Decimal('50000')), (Decimal('0.02'), Decimal('50000'))],
        ):
            mgr._accumulate_accepted_fill(
                runtime,
                FillReceived(
                    account_id=_ACCT, timestamp=_TS,
                    client_order_id=f'q-{index}', venue_order_id=f'v-{index}',
                    venue_trade_id=f'vt-{index}', trade_id=_TRADE,
                    command_id='cmd-quote', symbol='BTCUSDT',
                    side=OrderSide.BUY, qty=qty, price=price,
                    fee=Decimal('0'), fee_asset='USDT', is_maker=False,
                ),
            )

        filled_qty, notional = runtime.accepted_fill_totals['cmd-quote']

        assert notional == Decimal('1000'), (
            f'spend {notional} exceeded the 1000 budget'
        )
        assert filled_qty == Decimal('0.02')
        assert notional / filled_qty == Decimal('50000')

    @pytest.mark.asyncio
    async def test_a_command_registered_without_a_budget_admits_nothing(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''The state the installer prevents must still be safe if it occurs.

        A command present with no recorded budget is the one state in which
        nothing bounds a fill. Guarding only the source that produces it
        witnesses the convention, not the danger, so admission fails closed
        on the state itself: the fill is reported as nothing rather than
        reported in full against a target that cannot contain it. The ledger
        and the position project the raw fill either way, so what is held
        and what can be closed are unaffected.
        '''

        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        runtime = mgr._accounts[_ACCT]

        mgr._commands['cmd-unbudgeted'] = TradeCommand(
            command_id='cmd-unbudgeted', trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('1'),
            order_type=OrderType.MARKET,
            execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(), timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        )

        assert 'cmd-unbudgeted' not in mgr._admission_targets

        mgr._accumulate_accepted_fill(
            runtime,
            FillReceived(
                account_id=_ACCT, timestamp=_TS,
                client_order_id='u-0', venue_order_id='v-u',
                venue_trade_id='vt-u', trade_id=_TRADE,
                command_id='cmd-unbudgeted', symbol='BTCUSDT',
                side=OrderSide.BUY, qty=Decimal('5'), price=Decimal('10'),
                fee=Decimal('0'), fee_asset='USDT', is_maker=False,
            ),
        )

        assert runtime.accepted_fill_totals['cmd-unbudgeted'] == (
            Decimal('0'), Decimal('0'),
        ), 'a fill with no budget was admitted'

        assert mgr._accepted_command_totals(runtime, 'cmd-unbudgeted') == (
            Decimal('0'), Decimal('0'),
        )

        await mgr.unregister_account(_ACCT)

    def test_only_the_installer_registers_a_command(self) -> None:
        '''Registering a command must always record its admission budget.

        A fill is capped against the budget recorded when its command was
        registered. `_install_command` writes both together, so it has to be
        the only writer of the command map — a second one that set the
        command alone would leave a command with no budget, and a lazy
        fallback cannot repair that, since by then the command may carry an
        amend replacement's smaller quantity rather than the target its
        earlier fills were admitted against.

        This checks source shape, not behaviour: it catches a direct
        subscript assignment, which is the regression it was written for,
        and not an annotated assignment, a `.update()`, an aliased write, or
        the installer itself dropping the budget. What makes the resulting
        state safe is that admission refuses a fill with no budget — see
        `test_a_command_registered_without_a_budget_admits_nothing`.
        '''

        source = pathlib.Path('praxis/core/execution_manager.py').read_text()
        tree = ast.parse(source)
        installer = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_install_command'
        )
        allowed = set(range(installer.lineno, installer.end_lineno + 1))
        writers = [
            target.value.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Attribute)
            and target.value.attr == '_commands'
        ]

        assert writers, 'found no writer at all; this test has stopped looking'

        outside = [line for line in writers if line not in allowed]

        assert not outside, (
            f'execution_manager.py:{outside} assigns into _commands outside '
            f'_install_command; route it through the installer so the '
            f'admission budget is recorded with the command'
        )

    @pytest.mark.asyncio
    async def test_a_fill_after_terminalization_is_still_capped(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Terminalization drops the command; the budget must outlive it.

        A late or duplicate fill can arrive after the command terminalized
        and was removed. Resolving the budget from the command map alone
        found nothing and admitted the fill uncapped, so the quantity a
        restart replayed disagreed with the one live recorded.
        '''

        command = TradeCommand(
            command_id='cmd-late', trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('1'),
            order_type=OrderType.MARKET, execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(), timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        )
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        mgr._install_command('cmd-late', command)

        mgr._terminal_commands.add('cmd-late')
        mgr._commands.pop('cmd-late')

        runtime = mgr._accounts[_ACCT]
        mgr._accumulate_accepted_fill(
            runtime,
            FillReceived(
                account_id=_ACCT, timestamp=_TS,
                client_order_id='late-0', venue_order_id='v-late',
                venue_trade_id='vt-late', trade_id=_TRADE,
                command_id='cmd-late', symbol='BTCUSDT',
                side=OrderSide.BUY, qty=Decimal('2'), price=Decimal('10'),
                fee=Decimal('0'), fee_asset='USDT', is_maker=False,
            ),
        )

        assert runtime.accepted_fill_totals['cmd-late'] == (
            Decimal('1'), Decimal('10'),
        )

    def test_a_flatten_keeps_the_exit_target_it_inherits(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''A flatten is sized to the remainder but targets the whole exit.

        The flatten replaces a protective exit that may already have filled
        part of the position, and it is submitted for what is left. Taking
        that remainder as the exit command's target would report the fills
        accumulated under the id across both orders as exceeding it, and
        outcome construction would reject them.
        '''

        exit_command_id = 'cmd-exit'
        original = TradeCommand(
            command_id=exit_command_id, trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.SELL, qty=Decimal('1'),
            order_type=OrderType.MARKET, execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(), timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        )
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr._install_command(exit_command_id, original)

        mgr._terminal_commands.add(exit_command_id)
        mgr._commands.pop(exit_command_id)

        flatten = mgr._flatten_exit_command(
            original, exit_command_id, OrderSide.SELL, Decimal('0.6'),
        )

        assert flatten.qty == Decimal('1'), (
            f'flatten took the {flatten.qty} remainder as the exit target'
        )

    def test_an_abort_reports_the_command_target_not_the_replacement(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''An amended command's abort answers to the original target.

        An amend rests a replacement order for what was left, so that order's
        quantity is smaller than the command's. Reporting it as the target
        alongside fills accumulated across both orders understates what was
        asked for, and can suppress the replacement's delta when the original
        partial already reached Nexus.
        '''

        command = TradeCommand(
            command_id='cmd-abort', trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('1'),
            order_type=OrderType.LIMIT, execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(price=Decimal('10')), timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        )
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr._install_command('cmd-abort', command)

        replacement = Order(
            account_id=_ACCT, client_order_id='SS-abort-01',
            venue_order_id='v-1', command_id='cmd-abort', symbol='BTCUSDT',
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            qty=Decimal('0.6'), price=Decimal('10'),
            filled_qty=Decimal('0.2'), cumulative_notional=Decimal('2'),
            stop_price=None, status=OrderStatus.CANCELED,
            created_at=_TS, updated_at=_TS,
        )

        assert mgr._abort_target_qty(replacement) == Decimal('1')

    @pytest.mark.asyncio
    async def test_accumulated_totals_cannot_round_past_the_budget(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Bounding each increment does not bound the running total.

        Both the remaining-room subtraction and the final addition round at
        Decimal's working precision, so a budget carried to full precision
        can be stepped past by a fill whose own increment fits. The
        accumulated field is bounded, not just the increment: outcome
        construction rejects a quantity above the target, and a quote budget
        stepped past is spend that was never authorized.
        '''

        budget = Decimal('1.000000000000000000000000003')
        command = TradeCommand(
            command_id='cmd-acc', trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.BUY, qty=budget,
            order_type=OrderType.MARKET, execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(), timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        )
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        mgr._install_command('cmd-acc', command)
        runtime = mgr._accounts[_ACCT]

        for index, qty in enumerate(
            [Decimal('1.5E-27'), Decimal('2'), Decimal('5')],
        ):
            mgr._accumulate_accepted_fill(
                runtime,
                FillReceived(
                    account_id=_ACCT, timestamp=_TS,
                    client_order_id=f'a-{index}', venue_order_id=f'v-{index}',
                    venue_trade_id=f'vt-{index}', trade_id=_TRADE,
                    command_id='cmd-acc', symbol='BTCUSDT',
                    side=OrderSide.BUY, qty=qty, price=Decimal('1'),
                    fee=Decimal('0'), fee_asset='USDT', is_maker=False,
                ),
            )

        filled_qty, _notional = runtime.accepted_fill_totals['cmd-acc']

        assert filled_qty <= budget, (
            f'admitted {filled_qty} stepped past the {budget} budget'
        )
        assert filled_qty == budget, (
            f'admitted {filled_qty} short of the {budget} budget'
        )

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_quote_native_spend_survives_decimal_rounding(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''The admitted spend may never round its way past the budget.

        Deriving the quantity by dividing the remaining spend by the price
        and multiplying back is not exact at Decimal's working precision: a
        budget of 2 at a price of 14 recovers a product one unit in the last
        place above 2. Nexus's capital controller rejects a notional above
        what remains, so the excess has to be clipped rather than rounded.
        '''

        command = TradeCommand(
            command_id='cmd-round', trade_id=_TRADE, account_id=_ACCT,
            symbol='BTCUSDT', side=OrderSide.BUY, qty=None,
            quote_qty=Decimal('2'),
            order_type=OrderType.MARKET, execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(), timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE, created_at=_TS,
        )
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        mgr._install_command('cmd-round', command)
        runtime = mgr._accounts[_ACCT]

        mgr._accumulate_accepted_fill(
            runtime,
            FillReceived(
                account_id=_ACCT, timestamp=_TS,
                client_order_id='r-0', venue_order_id='v-r',
                venue_trade_id='vt-r', trade_id=_TRADE,
                command_id='cmd-round', symbol='BTCUSDT',
                side=OrderSide.BUY, qty=Decimal('1000'), price=Decimal('14'),
                fee=Decimal('0'), fee_asset='USDT', is_maker=False,
            ),
        )

        _filled, notional = runtime.accepted_fill_totals['cmd-round']

        assert notional <= Decimal('2'), (
            f'admitted spend {notional} rounded past the 2 budget'
        )

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_replay_of_an_amended_order_keeps_the_original_target(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''An amend must not shrink the budget its earlier fills used.

        An amend replaces the resting remainder, so the replacement order
        carries `qty=remainder` while the command's own target is unchanged.
        Rebuilding the command from every intent let the replacement's
        smaller quantity become the target on replay, and fills already
        admitted against the original target then exceeded it, so the
        remainder was silently dropped. No overfill is involved: this is an
        ordinary amended order.
        '''

        command_id = 'cmd-amend-replay'
        trade_id = 'trade-amend-replay'

        await spine.append(CommandAccepted(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
        ), _EPOCH)
        await spine.append(OrderSubmitIntent(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
            client_order_id='SS-amend-00', symbol='BTCUSDT',
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            qty=Decimal('1'), price=Decimal('100000'),
            stop_price=None, stop_limit_price=None,
        ), _EPOCH)
        await spine.append(FillReceived(
            account_id=_ACCT, timestamp=_TS,
            client_order_id='SS-amend-00', venue_order_id='v-0',
            venue_trade_id='vt-0', trade_id=trade_id,
            command_id=command_id, symbol='BTCUSDT',
            side=OrderSide.BUY, qty=Decimal('0.5'), price=Decimal('100000'),
            fee=Decimal('0'), fee_asset='USDT', is_maker=False,
        ), _EPOCH)
        await spine.append(OrderSubmitIntent(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
            client_order_id='SS-amend-01', symbol='BTCUSDT',
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            qty=Decimal('0.5'), price=Decimal('10'),
            stop_price=None, stop_limit_price=None,
        ), _EPOCH)
        await spine.append(FillReceived(
            account_id=_ACCT, timestamp=_TS,
            client_order_id='SS-amend-01', venue_order_id='v-1',
            venue_trade_id='vt-1', trade_id=trade_id,
            command_id=command_id, symbol='BTCUSDT',
            side=OrderSide.BUY, qty=Decimal('0.1'), price=Decimal('10'),
            fee=Decimal('0'), fee_asset='USDT', is_maker=False,
        ), _EPOCH)

        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        events = await spine.read(_EPOCH, after_seq=0)
        mgr.replay_events(
            _ACCT, [(q, e) for q, e in events if e.account_id == _ACCT],
        )

        runtime = mgr._accounts[_ACCT]
        admitted = runtime.accepted_fill_totals[command_id]

        assert admitted == (Decimal('0.6'), Decimal('50001')), (
            f'replay admitted {admitted}; the replacement order\'s remainder '
            f'must not become the command target'
        )
        assert mgr._commands[command_id].qty == Decimal('1')

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_replay_of_a_scheme_admits_against_its_total(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Scheme fills must be capped on replay as they were live.

        Replay keeps scheme commands out of `_commands` until the schemes
        are resumed, which happens after every fill has projected. Fills
        reaching admission with no command were admitted uncapped, so a
        restart turned a scheme that had overfilled into a larger position
        than the one live recorded. `SchemeInitialized` carries the total,
        so the budget is seeded before the fills replay.
        '''

        command_id = 'cmd-scheme-replay'
        trade_id = 'trade-scheme-replay'

        await spine.append(CommandAccepted(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
        ), _EPOCH)
        await spine.append(SchemeInitialized(
            account_id=_ACCT, timestamp=_TS,
            command_id=command_id, trade_id=trade_id,
            execution_mode=ExecutionMode.TWAP, symbol='BTCUSDT',
            side=OrderSide.BUY, total_qty=Decimal('1'),
            slices_total=2, interval_seconds=10, timeout_seconds=300,
        ), _EPOCH)

        for index, (qty, price) in enumerate(
            [(Decimal('0.5'), Decimal('100000')), (Decimal('1'), Decimal('10'))],
        ):
            await spine.append(FillReceived(
                account_id=_ACCT, timestamp=_TS,
                client_order_id=f'TW-{index}', venue_order_id=f'v-{index}',
                venue_trade_id=f'vt-{index}', trade_id=trade_id,
                command_id=command_id, symbol='BTCUSDT',
                side=OrderSide.BUY, qty=qty, price=price,
                fee=Decimal('0'), fee_asset='USDT', is_maker=False,
            ), _EPOCH)

        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)
        events = await spine.read(_EPOCH, after_seq=0)
        mgr.replay_events(
            _ACCT, [(q, e) for q, e in events if e.account_id == _ACCT],
        )

        runtime = mgr._accounts[_ACCT]
        admitted = runtime.accepted_fill_totals[command_id]

        assert admitted == (Decimal('1'), Decimal('50005')), (
            f'replay admitted {admitted}; a scheme absent from _commands '
            f'during the fill loop must still be capped at its total_qty'
        )

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_ws_partial_then_overfill_keeps_cumulative_monotonic(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''PR #85 round-6 review: pre-fix `_emit_ws_outcome` scaled
        `cumulative_notional` by `cmd.qty / order.filled_qty` on the
        overfill clamp path. If a PARTIAL outcome was emitted earlier
        with the unscaled cumulative, the subsequent overfill clamp
        could produce a SMALLER cumulative than the previous emission
        — OutcomeTranslator then computes a negative `delta_notional`
        and the terminal outcome is silently dropped at the validator.

        Post-fix the WS path forwards `order.cumulative_notional`
        verbatim (no scaling on the clamp), so cumulative_notional
        is monotonic across the PARTIAL → overfill sequence.
        '''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH,
            venue_adapter=adapter, on_trade_outcome=callback,
        )
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-mono',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        callback.reset_mock()

        runtime = mgr._accounts[_ACCT]
        coid = next(iter(runtime.trading_state.orders))

        partial = FillReceived(
            account_id=_ACCT, timestamp=_TS,
            client_order_id=coid, venue_order_id='v-mono',
            venue_trade_id='t-partial-hi',
            trade_id=_TRADE, command_id=command_id,
            symbol='BTCUSDT', side=OrderSide.BUY,
            qty=Decimal('0.5'), price=Decimal('100000'),
            fee=Decimal('0.05'), fee_asset='USDT', is_maker=True,
        )
        mgr.enqueue_ws_event(_ACCT, partial)
        await asyncio.sleep(0.3)

        partial_outcome: TradeOutcome = callback.call_args[0][0]
        partial_cumulative = partial_outcome.cumulative_notional
        assert partial_cumulative == Decimal('0.5') * Decimal('100000')

        callback.reset_mock()

        overfill = FillReceived(
            account_id=_ACCT, timestamp=_TS,
            client_order_id=coid, venue_order_id='v-mono',
            venue_trade_id='t-overfill-lo',
            trade_id=_TRADE, command_id=command_id,
            symbol='BTCUSDT', side=OrderSide.BUY,
            qty=Decimal('1.0'), price=Decimal('10'),
            fee=Decimal('0.05'), fee_asset='USDT', is_maker=True,
        )
        mgr.enqueue_ws_event(_ACCT, overfill)
        await asyncio.sleep(0.3)

        terminal_outcome: TradeOutcome = callback.call_args[0][0]
        assert terminal_outcome.filled_qty == Decimal('1')
        assert terminal_outcome.cumulative_notional >= partial_cumulative, (
            f'PR #85 round-6: cumulative_notional must be monotonic '
            f'across emissions for the same command. Pre-fix scaling '
            f'(50010 * 1 / 1.5 = 33340) would have been LESS than the '
            f'PARTIAL emission (50000), tripping translator delta < 0. '
            f'partial={partial_cumulative} terminal={terminal_outcome.cumulative_notional}'
        )

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_ws_event_for_terminal_command_does_not_emit(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''If `_process_command` already marked the command terminal
        (e.g. immediate-fill MARKET), a stale WS echo for the same
        command_id must not double-emit.'''

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
                    venue_trade_id='t-immediate',
                    qty=Decimal('1'),
                    price=Decimal('50000'),
                    fee=Decimal('0.05'),
                    fee_asset='USDT',
                    is_maker=False,
                ),
            ),
        )
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        assert callback.await_count == 1
        callback.reset_mock()

        coid = next(iter(mgr._accounts[_ACCT].trading_state.closed_orders))
        echo = FillReceived(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=coid,
            venue_order_id='v-o1',
            venue_trade_id='t-echo',
            trade_id=_TRADE,
            command_id=command_id,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            price=Decimal('50000'),
            fee=Decimal('0.05'),
            fee_asset='USDT',
            is_maker=False,
        )
        mgr.enqueue_ws_event(_ACCT, echo)
        await asyncio.sleep(0.3)

        callback.assert_not_awaited()

        await mgr.unregister_account(_ACCT)


class _FakeVenueRegistry:
    def __init__(self) -> None:
        self.credentials: dict[str, Credentials] = {}

    def register_account(self, account_id: str, credentials: Credentials) -> None:
        self.credentials[account_id] = credentials

    def unregister_account(self, account_id: str) -> None:
        del self.credentials[account_id]


class TestSubmitCommandRealChain:
    @pytest.mark.asyncio
    async def test_supplied_command_id_flows_through_inbound_to_execution(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        em = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter
        )
        inbound = TradingInbound(
            execution_manager=em,
            venue_adapter=_FakeVenueRegistry(),
            account_credentials={_ACCT: Credentials(api_key='key-1', api_secret='secret-1')},
        )
        inbound.register_account(_ACCT)
        try:
            command_id = await inbound.submit_command(
                **_CMD_KWARGS, command_id=_LONG_ID_VERBATIM
            )

            assert command_id == _LONG_ID_VERBATIM
            events = await spine.read(_EPOCH, after_seq=0)
            accepted = [e for _seq, e in events if isinstance(e, CommandAccepted)]
            assert len(accepted) == 1
            assert accepted[0].command_id == _LONG_ID_VERBATIM
        finally:
            await em.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_short_command_id_rejected_through_inbound_chain(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        em = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter
        )
        inbound = TradingInbound(
            execution_manager=em,
            venue_adapter=_FakeVenueRegistry(),
            account_credentials={_ACCT: Credentials(api_key='key-1', api_secret='secret-1')},
        )
        inbound.register_account(_ACCT)
        try:
            with pytest.raises(ValueError, match='at least 16 characters'):
                await inbound.submit_command(
                    **_CMD_KWARGS, command_id='cmd-short-1'
                )

            events = await spine.read(_EPOCH, after_seq=0)
            assert events == []
        finally:
            await em.unregister_account(_ACCT)


class TestTradeClosedPositionSemantics:
    '''TradeClosed marks position close, not order terminal.

    Regression guard for the restart durability bug: an entry fill that
    emitted TradeClosed deleted its own position on replay, so a restart
    rebuilt zero positions and boot reconciliation evicted the live one.
    '''

    @pytest.mark.asyncio
    async def test_entry_fill_keeps_position_and_emits_no_trade_closed(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.return_value = SubmitResult(
            venue_order_id='v-entry',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-entry',
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
        assert 'TradeClosed' not in types

        positions = mgr.pull_positions(_ACCT)
        assert (_TRADE, _ACCT) in positions
        assert positions[(_TRADE, _ACCT)].qty == Decimal('0.999')

    @pytest.mark.asyncio
    async def test_closing_fill_emits_trade_closed_and_clears_position(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.side_effect = [
            SubmitResult(
                venue_order_id='v-entry',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-entry',
                        qty=Decimal('1'),
                        price=Decimal('50000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
            SubmitResult(
                venue_order_id='v-exit',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-exit',
                        qty=Decimal('0.99899'),
                        price=Decimal('51000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
        ]
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        exit_kwargs = {**_CMD_KWARGS, 'side': OrderSide.SELL, 'qty': Decimal('0.99899')}
        await mgr.submit_command(**exit_kwargs)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'TradeClosed' in types

        positions = mgr.pull_positions(_ACCT)
        assert (_TRADE, _ACCT) not in positions

    @pytest.mark.asyncio
    async def test_partial_reducing_fill_emits_no_trade_closed(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.cached_filters.return_value = SymbolFilters(
            symbol='BTCUSDT',
            tick_size=Decimal('0.01'),
            lot_step=Decimal('0.00001'),
            lot_min=Decimal('0.00001'),
            lot_max=Decimal('9000'),
            min_notional=Decimal('10'),
        )
        adapter.submit_order.side_effect = [
            SubmitResult(
                venue_order_id='v-entry',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-entry',
                        qty=Decimal('1'),
                        price=Decimal('50000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
            SubmitResult(
                venue_order_id='v-exit',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-exit',
                        qty=Decimal('0.4'),
                        price=Decimal('51000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
        ]
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        exit_kwargs = {**_CMD_KWARGS, 'side': OrderSide.SELL, 'qty': Decimal('0.4')}
        await mgr.submit_command(**exit_kwargs)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'TradeClosed' not in types

        positions = mgr.pull_positions(_ACCT)
        assert positions[(_TRADE, _ACCT)].qty == Decimal('0.599')

    @pytest.mark.asyncio
    async def test_sub_lot_residue_exit_emits_trade_closed(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.cached_filters.return_value = SymbolFilters(
            symbol='BTCUSDT',
            tick_size=Decimal('0.01'),
            lot_step=Decimal('0.0001'),
            lot_min=Decimal('0.0001'),
            lot_max=Decimal('9000'),
            min_notional=Decimal('10'),
        )
        adapter.submit_order.side_effect = [
            SubmitResult(
                venue_order_id='v-entry',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-entry',
                        qty=Decimal('1'),
                        price=Decimal('50000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
            SubmitResult(
                venue_order_id='v-exit',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-exit',
                        qty=Decimal('0.99899'),
                        price=Decimal('51000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
        ]
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        exit_kwargs = {**_CMD_KWARGS, 'side': OrderSide.SELL, 'qty': Decimal('0.99899')}
        await mgr.submit_command(**exit_kwargs)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'TradeClosed' in types

        positions = mgr.pull_positions(_ACCT)
        assert (_TRADE, _ACCT) not in positions

    @pytest.mark.asyncio
    async def test_exact_full_exit_clears_position_without_trade_closed(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.side_effect = [
            SubmitResult(
                venue_order_id='v-entry',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-entry',
                        qty=Decimal('1'),
                        price=Decimal('50000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
            SubmitResult(
                venue_order_id='v-exit',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id='t-exit',
                        qty=Decimal('1'),
                        price=Decimal('51000'),
                        fee=Decimal('0.001'),
                        fee_asset='BTC',
                        is_maker=False,
                    ),
                ),
            ),
        ]
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        exit_kwargs = {**_CMD_KWARGS, 'side': OrderSide.SELL, 'qty': Decimal('0.99899')}
        await mgr.submit_command(**exit_kwargs)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'TradeClosed' not in types

        positions = mgr.pull_positions(_ACCT)
        assert (_TRADE, _ACCT) not in positions


class TestInjectedClock:
    @pytest.mark.asyncio
    async def test_command_accepted_uses_injected_clock(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        fixed = datetime(2026, 1, 1, tzinfo=UTC)
        em = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
            clock=lambda: fixed,
        )
        em.register_account(_ACCT)

        try:
            await em.submit_command(**_CMD_KWARGS, command_id=_LONG_ID_DUP)
            events = await spine.read(_EPOCH, after_seq=0)
            accepted = [e for _seq, e in events if isinstance(e, CommandAccepted)]

            assert len(accepted) == 1
            assert accepted[0].timestamp == fixed
        finally:
            for account_id in list(em._accounts):
                await em.unregister_account(account_id)


class TestQuiesce:
    @pytest.mark.asyncio
    async def test_quiesce_waits_for_full_command_processing(
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
        await mgr.quiesce(_ACCT)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]

        assert 'FillReceived' in types
        assert 'TradeOutcomeProduced' in types

    @pytest.mark.asyncio
    async def test_quiesce_unregistered_account_returns(
        self,
        mgr: ExecutionManager,
    ) -> None:
        await mgr.quiesce('unregistered')


class TestAccountLedgerWiring:
    '''AccountLedger projection wired into the per-account spine-append path.'''

    def _fill(self, fee_asset: str = 'USDT') -> FillReceived:
        return FillReceived(
            account_id=_ACCT, timestamp=_TS, client_order_id='c-1',
            venue_order_id='v-1', venue_trade_id='vt-1', trade_id=_TRADE, command_id='cmd-1',
            symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('1'), price=Decimal('100'),
            fee=Decimal('0.1'), fee_asset=fee_asset, is_maker=False,
        )

    @pytest.mark.asyncio
    async def test_replay_legacy_history_default_registers_and_books(
        self, mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        mgr.replay_events(_ACCT, [(1, self._fill())])
        ledger = mgr._accounts[_ACCT].account_ledger

        assert ledger.cost_basis_method is CostBasisMethod.FIFO
        assert ledger.balances[Account.CRYPTO_BTC] == Decimal('100')

    @pytest.mark.asyncio
    async def test_replay_honors_registered_cost_basis_method(
        self, mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        mgr.replay_events(_ACCT, [
            (1, RegisterAccount(account_id=_ACCT, timestamp=_TS, cost_basis_method='AVERAGE')),
            (2, self._fill()),
        ])
        ledger = mgr._accounts[_ACCT].account_ledger

        assert ledger.cost_basis_method is CostBasisMethod.AVERAGE
        assert ledger.balances[Account.CRYPTO_BTC] == Decimal('100')

    @pytest.mark.asyncio
    async def test_ledger_projection_failure_is_isolated(
        self, mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        mgr.replay_events(_ACCT, [(1, self._fill(fee_asset='BNB'))])
        runtime = mgr._accounts[_ACCT]

        assert (_TRADE, _ACCT) in mgr.pull_positions(_ACCT)
        assert runtime.account_ledger.balances[Account.CRYPTO_BTC] == Decimal('0')

    @pytest.mark.asyncio
    async def test_new_account_registration_appends_and_registers(
        self, mgr: ExecutionManager, spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        await mgr.register_account_on_spine(_ACCT)
        events = await spine.read(_EPOCH)
        ledger = mgr._accounts[_ACCT].account_ledger

        assert any(isinstance(event, RegisterAccount) for _seq, event in events)
        assert ledger.cost_basis_method is CostBasisMethod.FIFO

    @pytest.mark.asyncio
    async def test_register_account_on_spine_is_idempotent(
        self, mgr: ExecutionManager, spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        await mgr.register_account_on_spine(_ACCT)
        await mgr.register_account_on_spine(_ACCT)
        events = await spine.read(_EPOCH)

        registrations = [event for _seq, event in events if isinstance(event, RegisterAccount)]
        assert len(registrations) == 1

    @pytest.mark.asyncio
    async def test_replay_books_fund_transaction(
        self, mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        mgr.replay_events(_ACCT, [
            (1, RegisterAccount(account_id=_ACCT, timestamp=_TS, cost_basis_method='FIFO')),
            (2, FundTransaction(
                account_id=_ACCT, timestamp=_TS, fund_transaction_id='f-1',
                amount=Decimal('1000'), direction='DEPOSIT',
            )),
        ])
        ledger = mgr._accounts[_ACCT].account_ledger

        assert ledger.balances[Account.CASH_USDT] == Decimal('1000')
        assert ledger.balances[Account.CONTRIBUTIONS] == Decimal('1000')

    @pytest.mark.asyncio
    async def test_read_interface_returns_balances_and_trade_pnls(
        self, mgr: ExecutionManager,
    ) -> None:
        mgr.register_account(_ACCT)
        mgr.replay_events(_ACCT, [
            (1, RegisterAccount(account_id=_ACCT, timestamp=_TS, cost_basis_method='FIFO')),
            (2, self._fill()),
        ])

        balances = mgr.get_account_balances(_ACCT)
        pnls = mgr.get_account_trade_pnls(_ACCT)

        assert balances[Account.CRYPTO_BTC] == Decimal('100')
        assert pnls[_TRADE].fees == Decimal('0.1')

    @pytest.mark.asyncio
    async def test_read_interface_raises_for_unknown_account(
        self, mgr: ExecutionManager,
    ) -> None:
        with pytest.raises(AccountNotRegisteredError):
            mgr.get_account_balances('nope')

        with pytest.raises(AccountNotRegisteredError):
            mgr.get_account_trade_pnls('nope')
