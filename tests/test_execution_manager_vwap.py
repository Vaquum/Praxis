'''
Tests for the Scheduled VWAP execution scheme in ExecutionManager
(WP-Praxis-0007): interval-scheduled MARKET slices sized by a strategy-
supplied volume-weight curve, on the shared scheme engine.
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
    SchemeState,
    STPMode,
    OrderType,
    TradeStatus,
)
from praxis.core.domain.events import Event, SchemeInitialized
from praxis.core.domain.scheduled_vwap_params import ScheduledVwapParams
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    ImmediateFill,
    SubmitResult,
    SymbolFilters,
    VenueAdapter,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_PRICE = Decimal('50000')
_BIG_STEP = timedelta(seconds=60)
_QTY_ARG_INDEX = 4
_WEIGHTS = (Decimal('0.5'), Decimal('0.3'), Decimal('0.2'))


def _vwap_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.SCHEDULED_VWAP,
        'execution_params': ScheduledVwapParams(
            interval_seconds=10, volume_weights=_WEIGHTS,
        ),
        'timeout': 3600,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


def _fill_echo(*args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
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
    clock_holder[0] = clock_holder[0] + _BIG_STEP
    await asyncio.sleep(0.3)


@pytest.mark.asyncio
async def test_vwap_slices_are_weighted_and_produce_one_filled_outcome(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_vwap_kwargs())
    await asyncio.sleep(0.3)

    for _ in range(2):
        await _advance(clock_holder)

    submitted_qtys = [
        call.args[_QTY_ARG_INDEX] for call in adapter.submit_order.call_args_list
    ]
    assert submitted_qtys == [Decimal('0.5'), Decimal('0.3'), Decimal('0.2')]

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.FILLED
    assert outcome.command_id == command_id
    assert outcome.filled_qty == Decimal('1')
    assert outcome.slices_total == 3

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.COMPLETED


@pytest.mark.asyncio
async def test_vwap_planning_failure_rejects(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
) -> None:
    em, outcomes = mgr
    adapter.cached_filters.return_value = SymbolFilters(
        symbol='BTCUSDT',
        tick_size=Decimal('0.01'),
        lot_step=Decimal('1'),
        lot_min=Decimal('1'),
        lot_max=Decimal('100'),
        min_notional=Decimal('10'),
    )
    em.register_account(_ACCT)
    await em.submit_command(
        **_vwap_kwargs(
            qty=Decimal('0.02'),
            execution_params=ScheduledVwapParams(
                interval_seconds=10,
                volume_weights=(Decimal('0.1'), Decimal('0.9')),
            ),
        ),
    )
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    assert outcomes[0].status is TradeStatus.REJECTED
    adapter.submit_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_vwap_coarse_lot_drops_dust_into_last_slice(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    em, _ = mgr
    adapter.cached_filters.return_value = SymbolFilters(
        symbol='BTCUSDT',
        tick_size=Decimal('0.01'),
        lot_step=Decimal('0.01'),
        lot_min=Decimal('0.01'),
        lot_max=Decimal('100'),
        min_notional=Decimal('10'),
    )
    em.register_account(_ACCT)
    await em.submit_command(
        **_vwap_kwargs(
            execution_params=ScheduledVwapParams(
                interval_seconds=10,
                volume_weights=(Decimal('0.333'), Decimal('0.333'), Decimal('0.334')),
            ),
        ),
    )
    await asyncio.sleep(0.3)

    for _ in range(2):
        await _advance(clock_holder)

    submitted_qtys = [
        call.args[_QTY_ARG_INDEX] for call in adapter.submit_order.call_args_list
    ]
    assert all(q % Decimal('0.01') == 0 for q in submitted_qtys)
    assert sum(submitted_qtys) <= Decimal('1')
    assert Decimal('1') - sum(submitted_qtys) < Decimal('0.01')


@pytest.mark.asyncio
async def test_vwap_persists_volume_weights_on_init(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    spine: EventSpine,
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)
    await em.submit_command(**_vwap_kwargs())
    await asyncio.sleep(0.3)

    events = await spine.read(_EPOCH, after_seq=0)
    init = next(e for _, e in events if type(e).__name__ == 'SchemeInitialized')
    assert init.execution_mode is ExecutionMode.SCHEDULED_VWAP
    assert init.volume_weights == _WEIGHTS
    assert init.slices_total == 3


@pytest.mark.asyncio
async def test_vwap_resumes_weighted_plan_from_replay(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_vwap_kwargs())
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

    resumed = restarted._accounts[_ACCT].schemes[command_id]
    assert resumed.state is SchemeState.RUNNING
    assert resumed.slice_qtys == [Decimal('0.5'), Decimal('0.3'), Decimal('0.2')]
    assert resumed.cursor == 1

    for _ in range(2):
        await _advance(clock_holder)

    assert len(restart_outcomes) == 1
    assert restart_outcomes[0].status is TradeStatus.FILLED
    assert restart_outcomes[0].filled_qty == Decimal('1')

    await restarted.unregister_account(_ACCT)


_RESUME_COMMAND_ID = '22222222-3333-4444-5555-666666666666'


def _vwap_init(volume_weights: tuple[Decimal, ...], slices_total: int) -> list[tuple[int, Event]]:
    return [
        (
            1,
            SchemeInitialized(
                account_id=_ACCT,
                timestamp=_T0,
                command_id=_RESUME_COMMAND_ID,
                trade_id=_TRADE,
                execution_mode=ExecutionMode.SCHEDULED_VWAP,
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                total_qty=Decimal('1'),
                slices_total=slices_total,
                interval_seconds=10,
                timeout_seconds=3600,
                volume_weights=volume_weights,
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_vwap_resume_without_weights_does_not_resume(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)

    em.replay_events(_ACCT, _vwap_init((), 3))
    await asyncio.sleep(0.1)

    assert _RESUME_COMMAND_ID not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_vwap_resume_with_corrupt_weights_survives_replay(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)

    em.replay_events(_ACCT, _vwap_init((Decimal('0.5'), Decimal('0.9')), 2))
    await asyncio.sleep(0.1)

    assert _RESUME_COMMAND_ID not in em._accounts[_ACCT].schemes


@pytest.mark.asyncio
async def test_vwap_resume_aligns_slices_total_to_replanned_length(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)

    events = _vwap_init((Decimal('0.5'), Decimal('0.5')), slices_total=5)
    em.replay_events(_ACCT, events)
    await asyncio.sleep(0.1)

    scheme = em._accounts[_ACCT].schemes[_RESUME_COMMAND_ID]
    assert scheme.slices_total == len(scheme.slice_qtys) == 2
