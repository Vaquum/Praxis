'''
Tests for the TWAP execution scheme in ExecutionManager
(WP-Praxis-0007 item 4, happy path): interval-scheduled MARKET slices,
per-slice scheme state, and a single aggregated terminal outcome.
'''

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, UTC
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
    CommandAccepted,
    FillReceived,
    OrderRejected,
    OrderSubmitIntent,
    OrderSubmitted,
    SchemeInitialized,
    SchemeStateChanged,
)
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.twap_params import TwapParams
from praxis.core.execution_manager import ExecutionManager
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    ImmediateFill,
    OrderRejectedError,
    SubmitResult,
    SymbolFilters,
    VenueAdapter,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_PRICE = Decimal('50000')
_BIG_STEP = timedelta(hours=1)


def _twap_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.TWAP,
        'execution_params': TwapParams(num_slices=4, interval_seconds=10),
        'timeout': 3600,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


_QTY_ARG_INDEX = 4


def _fill_echo(*args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
    '''Return a fully filled MARKET result echoing the submitted qty.'''

    qty = args[_QTY_ARG_INDEX]

    return SubmitResult(
        venue_order_id=f'v-{client_order_id}',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id=f't-{client_order_id}',
                qty=qty,
                price=_PRICE,
                fee=Decimal('0'),
                fee_asset='USDT',
                is_maker=False,
            ),
        ),
    )


@pytest.fixture
def clock_holder() -> list[datetime]:
    return [_T0]


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.side_effect = _fill_echo
    mock.cached_filters.return_value = None
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> AsyncGenerator[tuple[ExecutionManager, list[TradeOutcome]], None]:
    outcomes: list[TradeOutcome] = []

    async def _capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    em = ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=_capture,
        clock=lambda: clock_holder[0],
    )
    yield em, outcomes
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


async def _advance(clock_holder: list[datetime]) -> None:
    '''Jump the clock past any pending interval and let the loop settle.'''

    clock_holder[0] = clock_holder[0] + _BIG_STEP
    await asyncio.sleep(0.3)


@pytest.mark.asyncio
async def test_twap_runs_all_slices_and_produces_one_filled_outcome(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    clock_holder: list[datetime],
) -> None:
    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_twap_kwargs())
    await asyncio.sleep(0.3)

    for _ in range(3):
        await _advance(clock_holder)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.FILLED
    assert outcome.command_id == command_id
    assert outcome.filled_qty == Decimal('1')
    assert outcome.target_qty == Decimal('1')
    assert outcome.avg_fill_price == _PRICE
    assert outcome.cumulative_notional == _PRICE
    assert outcome.slices_completed == 4
    assert outcome.slices_total == 4

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.COMPLETED
    assert scheme.cursor == 4
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_emits_expected_spine_sequence(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    spine: EventSpine,
    clock_holder: list[datetime],
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)
    await em.submit_command(**_twap_kwargs(execution_params=TwapParams(num_slices=2, interval_seconds=10)))
    await asyncio.sleep(0.3)
    await _advance(clock_holder)

    events = await spine.read(_EPOCH, after_seq=0)
    types = [type(e).__name__ for _, e in events]

    assert types == [
        'CommandAccepted',
        'SchemeInitialized',
        'OrderSubmitIntent',
        'OrderSubmitted',
        'FillReceived',
        'SchemeStateChanged',
        'OrderSubmitIntent',
        'OrderSubmitted',
        'FillReceived',
        'SchemeStateChanged',
        'TradeOutcomeProduced',
    ]

    init = events[1][1]
    assert init.execution_mode is ExecutionMode.TWAP
    assert init.total_qty == Decimal('1')
    assert init.slices_total == 2

    terminal_state_change = events[9][1]
    assert terminal_state_change.state is SchemeState.COMPLETED
    assert terminal_state_change.next_run_at is None


@pytest.mark.asyncio
async def test_twap_slice_failure_finalizes_terminal_rejected(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    calls = {'n': 0}

    def _fail_second(*args: Any, **kwargs: Any) -> SubmitResult:
        calls['n'] += 1
        if calls['n'] == 2:
            raise OrderRejectedError(
                'insufficient balance', venue_code=-1013, reason='insufficient balance'
            )
        return _fill_echo(*args, **kwargs)

    adapter.submit_order.side_effect = _fail_second

    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_twap_kwargs())
    await asyncio.sleep(0.3)
    await _advance(clock_holder)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.REJECTED
    assert outcome.filled_qty == Decimal('0.25')
    assert outcome.slices_completed == 1

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.FAILED
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_pre_abort_cancels_before_first_slice(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
) -> None:
    em, outcomes = mgr
    em.register_account(_ACCT)
    em.set_reconciling(_ACCT, True)
    command_id = await em.submit_command(**_twap_kwargs())
    em.submit_abort(
        TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='operator cancel',
            created_at=_T0,
        )
    )
    await asyncio.sleep(0.3)
    em.set_reconciling(_ACCT, False)
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.CANCELED
    assert outcome.filled_qty == Decimal('0')
    assert outcome.slices_completed == 0
    assert outcome.slices_total == 4
    assert outcome.reason == 'operator cancel'

    adapter.submit_order.assert_not_awaited()
    assert command_id not in em.get_trading_state(_ACCT).schemes


@pytest.mark.asyncio
async def test_twap_lot_aligned_slices_complete(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    adapter.cached_filters.return_value = SymbolFilters(
        symbol='BTCUSDT',
        tick_size=Decimal('0.01'),
        lot_step=Decimal('0.001'),
        lot_min=Decimal('0.0001'),
        lot_max=Decimal('1000'),
        min_notional=Decimal('0'),
    )

    em, outcomes = mgr
    em.register_account(_ACCT)
    await em.submit_command(
        **_twap_kwargs(execution_params=TwapParams(num_slices=3, interval_seconds=10))
    )
    await asyncio.sleep(0.3)
    await _advance(clock_holder)
    await _advance(clock_holder)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.FILLED
    assert outcome.filled_qty == Decimal('1')
    assert outcome.avg_fill_price == _PRICE
    assert outcome.slices_completed == 3


@pytest.mark.asyncio
async def test_twap_mid_scheme_abort_cancels_with_partial_fills(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
) -> None:
    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_twap_kwargs())
    await asyncio.sleep(0.3)

    assert command_id in em._accounts[_ACCT].schemes

    em.submit_abort(
        TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='operator stop',
            created_at=_T0,
        )
    )
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.CANCELED
    assert outcome.reason == 'operator stop'
    assert outcome.filled_qty == Decimal('0.25')
    assert outcome.slices_completed == 1
    assert outcome.slices_total == 4

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.CANCELED
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_planning_failure_rejects_before_any_slice(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
) -> None:
    adapter.cached_filters.return_value = SymbolFilters(
        symbol='BTCUSDT',
        tick_size=Decimal('0.01'),
        lot_step=Decimal('1'),
        lot_min=Decimal('0.0001'),
        lot_max=Decimal('1000'),
        min_notional=Decimal('0'),
    )

    em, outcomes = mgr
    em.register_account(_ACCT)
    await em.submit_command(**_twap_kwargs())
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    assert outcomes[0].status is TradeStatus.REJECTED
    assert outcomes[0].filled_qty == Decimal('0')
    adapter.submit_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_twap_partial_immediate_fill_completes_via_ws(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    def _half_fill(*args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
        qty = args[_QTY_ARG_INDEX]
        return SubmitResult(
            venue_order_id=f'v-{client_order_id}',
            status=OrderStatus.PARTIALLY_FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id=f'ti-{client_order_id}',
                    qty=qty / 2,
                    price=_PRICE,
                    fee=Decimal('0'),
                    fee_asset='USDT',
                    is_maker=False,
                ),
            ),
        )

    adapter.submit_order.side_effect = _half_fill

    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(
        **_twap_kwargs(execution_params=TwapParams(num_slices=2, interval_seconds=10))
    )
    await asyncio.sleep(0.3)

    runtime_scheme = em._accounts[_ACCT].schemes[command_id]
    assert len(outcomes) == 0
    assert len(runtime_scheme.active_children) == 1

    await _advance(clock_holder)

    assert len(outcomes) == 0
    assert len(runtime_scheme.active_children) == 2

    for client_order_id in sorted(runtime_scheme.active_children):
        em.enqueue_ws_event(
            _ACCT,
            FillReceived(
                account_id=_ACCT,
                timestamp=_T0,
                client_order_id=client_order_id,
                venue_order_id=f'v-{client_order_id}',
                venue_trade_id=f'tw-{client_order_id}',
                trade_id=_TRADE,
                command_id=command_id,
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                qty=Decimal('0.25'),
                price=_PRICE,
                fee=Decimal('0'),
                fee_asset='USDT',
                is_maker=False,
            ),
        )
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.FILLED
    assert outcome.filled_qty == Decimal('1')
    assert outcome.avg_fill_price == _PRICE

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.COMPLETED
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_async_rejected_child_fails_not_filled(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    calls = {'n': 0}

    def _fill_then_ack(*args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
        calls['n'] += 1
        qty = args[_QTY_ARG_INDEX]
        if calls['n'] == 1:
            return SubmitResult(
                venue_order_id=f'v-{client_order_id}',
                status=OrderStatus.FILLED,
                immediate_fills=(
                    ImmediateFill(
                        venue_trade_id=f'ti-{client_order_id}',
                        qty=qty,
                        price=_PRICE,
                        fee=Decimal('0'),
                        fee_asset='USDT',
                        is_maker=False,
                    ),
                ),
            )
        return SubmitResult(
            venue_order_id=f'v-{client_order_id}',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )

    adapter.submit_order.side_effect = _fill_then_ack

    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(
        **_twap_kwargs(execution_params=TwapParams(num_slices=2, interval_seconds=10))
    )
    await asyncio.sleep(0.3)
    await _advance(clock_holder)

    runtime_scheme = em._accounts[_ACCT].schemes[command_id]
    assert len(outcomes) == 0
    assert len(runtime_scheme.active_children) == 1
    child = next(iter(runtime_scheme.active_children))

    em.enqueue_ws_event(
        _ACCT,
        OrderRejected(
            account_id=_ACCT,
            timestamp=_T0,
            client_order_id=child,
            venue_order_id=f'v-{child}',
            reason='insufficient balance',
        ),
    )
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.REJECTED
    assert outcome.filled_qty == Decimal('0.5')

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.FAILED
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_abort_cancels_live_child_then_finalizes(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
) -> None:
    def _half_fill(*args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
        qty = args[_QTY_ARG_INDEX]
        return SubmitResult(
            venue_order_id=f'v-{client_order_id}',
            status=OrderStatus.PARTIALLY_FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id=f'ti-{client_order_id}',
                    qty=qty / 2,
                    price=_PRICE,
                    fee=Decimal('0'),
                    fee_asset='USDT',
                    is_maker=False,
                ),
            ),
        )

    adapter.submit_order.side_effect = _half_fill

    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(
        **_twap_kwargs(execution_params=TwapParams(num_slices=2, interval_seconds=10))
    )
    await asyncio.sleep(0.3)

    assert len(em._accounts[_ACCT].schemes[command_id].active_children) == 1

    em.submit_abort(
        TradeAbort(
            command_id=command_id,
            account_id=_ACCT,
            reason='operator stop',
            created_at=_T0,
        )
    )
    await asyncio.sleep(0.3)

    adapter.cancel_order.assert_awaited()

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.CANCELED
    assert outcome.filled_qty == Decimal('0.25')

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.CANCELED
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_slice_submit_failure_cancels_active_child_then_fails(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    calls = {'n': 0}

    def _ack_then_reject(*_args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
        calls['n'] += 1
        if calls['n'] == 1:
            return SubmitResult(
                venue_order_id=f'v-{client_order_id}',
                status=OrderStatus.OPEN,
                immediate_fills=(),
            )
        raise OrderRejectedError(
            'insufficient balance', venue_code=-1013, reason='insufficient balance'
        )

    adapter.submit_order.side_effect = _ack_then_reject

    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(
        **_twap_kwargs(execution_params=TwapParams(num_slices=2, interval_seconds=10))
    )
    await asyncio.sleep(0.3)

    assert len(em._accounts[_ACCT].schemes[command_id].active_children) == 1

    await _advance(clock_holder)

    adapter.cancel_order.assert_awaited()

    assert len(outcomes) == 1
    assert outcomes[0].status is TradeStatus.REJECTED

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.FAILED
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_advance_exception_finalizes_failed(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    em, outcomes = mgr

    async def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError('slice submit exploded')

    monkeypatch.setattr(em, '_submit_market_slice', _boom)

    em.register_account(_ACCT)
    command_id = await em.submit_command(**_twap_kwargs())
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    assert outcomes[0].status is TradeStatus.REJECTED

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.FAILED
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_twap_resumes_from_replay_and_completes(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_twap_kwargs())
    await asyncio.sleep(0.3)

    events = await spine.read(_EPOCH, after_seq=0)
    await em.unregister_account(_ACCT)

    restart_outcomes: list[TradeOutcome] = []

    async def _capture(outcome: TradeOutcome) -> None:
        restart_outcomes.append(outcome)

    restarted = ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=_capture,
        clock=lambda: clock_holder[0],
    )
    restarted.register_account(_ACCT)
    restarted.replay_events(_ACCT, events)
    await restarted.reconcile_orphan_commands(_ACCT, events)

    resumed = restarted._accounts[_ACCT].schemes[command_id]
    assert len(restart_outcomes) == 0
    assert resumed.state is SchemeState.RUNNING
    assert resumed.cursor == 1

    for _ in range(3):
        await _advance(clock_holder)

    assert len(restart_outcomes) == 1
    outcome = restart_outcomes[0]
    assert outcome.status is TradeStatus.FILLED
    assert outcome.filled_qty == Decimal('1')
    assert outcome.slices_completed == 4
    assert restarted.get_trading_state(_ACCT).schemes[command_id].state is SchemeState.COMPLETED

    await restarted.unregister_account(_ACCT)


def _child_fill(command_id: str, client_order_id: str, qty: Decimal) -> FillReceived:
    return FillReceived(
        account_id=_ACCT,
        timestamp=_T0,
        client_order_id=client_order_id,
        venue_order_id=f'v-{client_order_id}',
        venue_trade_id=f't-{client_order_id}',
        trade_id=_TRADE,
        command_id=command_id,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        price=_PRICE,
        fee=Decimal('0'),
        fee_asset='USDT',
        is_maker=False,
    )


def _intent(command_id: str, client_order_id: str, qty: Decimal) -> OrderSubmitIntent:
    return OrderSubmitIntent(
        account_id=_ACCT,
        timestamp=_T0,
        command_id=command_id,
        trade_id=_TRADE,
        client_order_id=client_order_id,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=qty,
    )


@pytest.mark.asyncio
async def test_twap_resume_prunes_already_filled_active_child_and_finalizes(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
) -> None:
    em, outcomes = mgr
    command_id = 'cmd-stale0000000000000000000000000'
    coid0 = generate_client_order_id(ExecutionMode.TWAP, command_id, 0)
    coid1 = generate_client_order_id(ExecutionMode.TWAP, command_id, 1)
    half = Decimal('0.5')

    events = [
        (1, CommandAccepted(account_id=_ACCT, timestamp=_T0, command_id=command_id, trade_id=_TRADE)),
        (2, SchemeInitialized(
            account_id=_ACCT, timestamp=_T0, command_id=command_id, trade_id=_TRADE,
            execution_mode=ExecutionMode.TWAP, symbol='BTCUSDT', side=OrderSide.BUY,
            total_qty=Decimal('1'), slices_total=2, interval_seconds=10,
        )),
        (3, _intent(command_id, coid0, half)),
        (4, OrderSubmitted(account_id=_ACCT, timestamp=_T0, client_order_id=coid0, venue_order_id=f'v-{coid0}')),
        (5, _child_fill(command_id, coid0, half)),
        (6, SchemeStateChanged(
            account_id=_ACCT, timestamp=_T0, command_id=command_id, cursor=1,
            filled_qty=half, active_client_order_ids=(), next_run_at=_T0, state=SchemeState.RUNNING,
        )),
        (7, _intent(command_id, coid1, half)),
        (8, OrderSubmitted(account_id=_ACCT, timestamp=_T0, client_order_id=coid1, venue_order_id=f'v-{coid1}')),
        (9, SchemeStateChanged(
            account_id=_ACCT, timestamp=_T0, command_id=command_id, cursor=2,
            filled_qty=half, active_client_order_ids=(coid1,), next_run_at=None, state=SchemeState.RUNNING,
        )),
        (10, _child_fill(command_id, coid1, half)),
    ]

    em.register_account(_ACCT)
    em.replay_events(_ACCT, events)
    await em.reconcile_orphan_commands(_ACCT, events)

    resumed = em._accounts[_ACCT].schemes[command_id]
    assert resumed.active_children == set()

    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.FILLED
    assert outcome.filled_qty == Decimal('1')
    assert command_id not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_scheme_missing_interval_is_unresumable_and_terminalized(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
) -> None:
    em, outcomes = mgr
    command_id = 'cmd-noint0000000000000000000000000'

    events = [
        (1, CommandAccepted(account_id=_ACCT, timestamp=_T0, command_id=command_id, trade_id=_TRADE)),
        (2, SchemeInitialized(
            account_id=_ACCT, timestamp=_T0, command_id=command_id, trade_id=_TRADE,
            execution_mode=ExecutionMode.TWAP, symbol='BTCUSDT', side=OrderSide.BUY,
            total_qty=Decimal('1'), slices_total=2,
        )),
        (3, SchemeStateChanged(
            account_id=_ACCT, timestamp=_T0, command_id=command_id, cursor=1,
            filled_qty=Decimal('0'), active_client_order_ids=(), next_run_at=None, state=SchemeState.RUNNING,
        )),
    ]

    em.register_account(_ACCT)
    em.replay_events(_ACCT, events)

    assert command_id not in em._accounts[_ACCT].schemes

    await em.reconcile_orphan_commands(_ACCT, events)

    assert len(outcomes) == 1
    assert outcomes[0].status is TradeStatus.CANCELED
