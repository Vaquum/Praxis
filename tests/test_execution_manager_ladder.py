'''
Tests for the Ladder DCA execution mode in ExecutionManager
(WP-Praxis-0007): a static grid of resting LIMIT orders at explicit price
levels, posted all at once, aggregating fills on the shared scheme engine.
'''

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
    SchemeState,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.events import (
    Event,
    FillReceived,
    OrderSubmitIntent,
    OrderSubmitted,
    SchemeInitialized,
)
from praxis.core.domain.ladder_dca_params import LadderDcaParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    SubmitResult,
    SymbolFilters,
    VenueAdapter,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_LEVELS = (Decimal('49000'), Decimal('48000'))
_PRICE_ARG_KW = 'price'
_QTY_ARG_INDEX = 4


def _ladder_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.LIMIT,
        'execution_mode': ExecutionMode.LADDER_DCA,
        'execution_params': LadderDcaParams(
            price_levels=_LEVELS,
            level_weights=(Decimal('0.6'), Decimal('0.4')),
        ),
        'timeout': 3600,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)

    def _rest(*_args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
        return SubmitResult(
            venue_order_id=f'v-{client_order_id}',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )

    mock.submit_order.side_effect = _rest
    mock.cached_filters.return_value = SymbolFilters(
        symbol='BTCUSDT',
        tick_size=Decimal('0.01'),
        lot_step=Decimal('0.001'),
        lot_min=Decimal('0.001'),
        lot_max=Decimal('100'),
        min_notional=Decimal('10'),
    )
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine,
    adapter: AsyncMock,
) -> AsyncGenerator[tuple[ExecutionManager, list[TradeOutcome]], None]:
    outcomes: list[TradeOutcome] = []

    async def _capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    em = ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=_capture,
        clock=lambda: _T0,
    )
    yield em, outcomes
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


def _rung_fill(command_id: str, index: int, qty: Decimal, price: Decimal) -> FillReceived:
    client_order_id = generate_client_order_id(
        ExecutionMode.LADDER_DCA, command_id, sequence=index,
    )
    return FillReceived(
        account_id=_ACCT,
        timestamp=_T0,
        client_order_id=client_order_id,
        venue_order_id=f'v-{client_order_id}',
        venue_trade_id=f't-{index}',
        trade_id=_TRADE,
        command_id=command_id,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        price=price,
        fee=Decimal('0'),
        fee_asset='USDT',
        is_maker=True,
    )


class TestLadderSubmit:

    @pytest.mark.asyncio
    async def test_posts_weighted_resting_limits_at_each_level(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_ladder_kwargs())
        await asyncio.sleep(0.3)

        calls = adapter.submit_order.call_args_list
        assert len(calls) == 2
        assert [c.args[_QTY_ARG_INDEX] for c in calls] == [Decimal('0.6'), Decimal('0.4')]
        assert [c.kwargs[_PRICE_ARG_KW] for c in calls] == list(_LEVELS)
        assert all(c.args[3] is OrderType.LIMIT for c in calls)

        assert not outcomes
        scheme = em.get_trading_state(_ACCT).schemes[command_id]
        assert scheme.state is SchemeState.RUNNING

    @pytest.mark.asyncio
    async def test_equal_split_when_no_weights(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        await em.submit_command(
            **_ladder_kwargs(
                execution_params=LadderDcaParams(price_levels=_LEVELS),
            ),
        )
        await asyncio.sleep(0.3)

        qtys = [c.args[_QTY_ARG_INDEX] for c in adapter.submit_order.call_args_list]
        assert qtys == [Decimal('0.5'), Decimal('0.5')]

    @pytest.mark.asyncio
    async def test_persists_price_levels_on_init(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], spine: EventSpine,
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        await em.submit_command(**_ladder_kwargs())
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        init = next(e for _, e in events if type(e).__name__ == 'SchemeInitialized')
        assert init.execution_mode is ExecutionMode.LADDER_DCA
        assert init.price_levels == _LEVELS
        assert init.slices_total == 2


class TestLadderLifecycle:

    @pytest.mark.asyncio
    async def test_rungs_filling_produce_one_filled_outcome(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_ladder_kwargs())
        await asyncio.sleep(0.3)

        em.enqueue_ws_event(_ACCT, _rung_fill(command_id, 0, Decimal('0.6'), _LEVELS[0]))
        await asyncio.sleep(0.2)
        assert not any(o.status.is_terminal for o in outcomes)

        em.enqueue_ws_event(_ACCT, _rung_fill(command_id, 1, Decimal('0.4'), _LEVELS[1]))
        await asyncio.sleep(0.3)

        assert len(outcomes) == 1
        assert outcomes[0].status is TradeStatus.FILLED
        assert outcomes[0].filled_qty == Decimal('1')

    @pytest.mark.asyncio
    async def test_abort_cancels_all_resting_rungs(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_ladder_kwargs())
        await asyncio.sleep(0.3)

        em.submit_abort(
            TradeAbort(
                command_id=command_id,
                account_id=_ACCT,
                reason='operator abort',
                created_at=_T0,
            ),
        )
        await asyncio.sleep(0.3)

        assert adapter.cancel_order.await_count == 2
        assert outcomes[-1].status is TradeStatus.CANCELED


class TestLadderResume:

    @pytest.mark.asyncio
    async def test_resumes_resting_rungs_from_replay(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
        spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_ladder_kwargs())
        await asyncio.sleep(0.3)

        events: list[tuple[int, Event]] = await spine.read(_EPOCH, after_seq=0)
        await em.unregister_account(_ACCT)

        restart_outcomes: list[TradeOutcome] = []

        async def _capture(outcome: TradeOutcome) -> None:
            restart_outcomes.append(outcome)

        restarted = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
            on_trade_outcome=_capture,
            clock=lambda: _T0,
        )
        restarted.register_account(_ACCT)
        restarted.replay_events(_ACCT, events)

        scheme = restarted._accounts[_ACCT].schemes[command_id]
        assert scheme.state is SchemeState.RUNNING
        assert len(scheme.active_children) == 2
        assert scheme.next_run_at is None

        em0 = command_id
        restarted.enqueue_ws_event(_ACCT, _rung_fill(em0, 0, Decimal('0.6'), _LEVELS[0]))
        restarted.enqueue_ws_event(_ACCT, _rung_fill(em0, 1, Decimal('0.4'), _LEVELS[1]))
        await asyncio.sleep(0.3)

        assert restart_outcomes[-1].status is TradeStatus.FILLED
        await restarted.unregister_account(_ACCT)


_RESUME_COMMAND_ID = '33333333-4444-5555-6666-777777777777'


def _rung_coid(index: int) -> str:
    return generate_client_order_id(
        ExecutionMode.LADDER_DCA, _RESUME_COMMAND_ID, sequence=index,
    )


def _partial_post_boot_events(posted_rungs: int) -> list[tuple[int, Event]]:
    '''SchemeInitialized plus only the first `posted_rungs` rungs' durable
    submit events — no SchemeStateChanged (a crash mid-posting).'''

    events: list[Event] = [
        SchemeInitialized(
            account_id=_ACCT,
            timestamp=_T0,
            command_id=_RESUME_COMMAND_ID,
            trade_id=_TRADE,
            execution_mode=ExecutionMode.LADDER_DCA,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            total_qty=Decimal('1'),
            slices_total=2,
            interval_seconds=0,
            timeout_seconds=3600,
            volume_weights=(Decimal('0.6'), Decimal('0.4')),
            price_levels=_LEVELS,
        ),
    ]

    for index in range(posted_rungs):
        coid = _rung_coid(index)
        events.append(
            OrderSubmitIntent(
                account_id=_ACCT,
                timestamp=_T0,
                command_id=_RESUME_COMMAND_ID,
                trade_id=_TRADE,
                client_order_id=coid,
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                qty=Decimal('0.6') if index == 0 else Decimal('0.4'),
                price=_LEVELS[index],
            ),
        )
        events.append(
            OrderSubmitted(
                account_id=_ACCT,
                timestamp=_T0,
                client_order_id=coid,
                venue_order_id=f'v-{coid}',
            ),
        )

    return list(enumerate(events, start=1))


class TestLadderCrashDurability:

    @pytest.mark.asyncio
    async def test_no_state_partial_post_does_not_false_finalize(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)

        em.replay_events(_ACCT, _partial_post_boot_events(posted_rungs=1))
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[_RESUME_COMMAND_ID]
        assert scheme.cursor == 1
        assert scheme.active_children == {_rung_coid(0)}
        assert scheme.state is SchemeState.RUNNING
        assert not any(o.status is TradeStatus.FILLED for o in outcomes)

    @pytest.mark.asyncio
    async def test_no_state_partial_post_fill_does_not_complete_ladder(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)

        em.replay_events(_ACCT, _partial_post_boot_events(posted_rungs=1))
        await asyncio.sleep(0.2)

        em.enqueue_ws_event(
            _ACCT, _rung_fill(_RESUME_COMMAND_ID, 0, Decimal('0.6'), _LEVELS[0]),
        )
        await asyncio.sleep(0.3)

        assert not any(o.status.is_terminal for o in outcomes)
        assert _RESUME_COMMAND_ID in em._accounts[_ACCT].schemes


class TestLadderQueueDeadline:

    @pytest.mark.asyncio
    async def test_ladder_past_deadline_at_dispatch_expires(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)
        await em.submit_command(
            **_ladder_kwargs(
                timeout=1,
                created_at=_T0 - timedelta(seconds=3600),
            ),
        )
        await asyncio.sleep(0.3)

        assert outcomes[-1].status is TradeStatus.EXPIRED
        adapter.submit_order.assert_not_awaited()
