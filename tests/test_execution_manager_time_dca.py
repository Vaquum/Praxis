'''
Tests for Time DCA execution on the shared equal-slice scheme engine
(WP-Praxis-0007 item 5): fixed-interval MARKET accumulation, one
aggregated terminal outcome, and mid-scheme abort.
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
from praxis.core.domain.time_dca_params import TimeDcaParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    ImmediateFill,
    SubmitResult,
    VenueAdapter,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_PRICE = Decimal('50000')
_BIG_STEP = timedelta(seconds=60)
_QTY_ARG_INDEX = 4


def _dca_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.TIME_DCA,
        'execution_params': TimeDcaParams(num_iterations=4, interval_seconds=10),
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
    clock_holder[0] = clock_holder[0] + _BIG_STEP
    await asyncio.sleep(0.3)


@pytest.mark.asyncio
async def test_time_dca_accumulates_all_iterations_to_one_filled_outcome(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    clock_holder: list[datetime],
) -> None:
    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_dca_kwargs())
    await asyncio.sleep(0.3)

    for _ in range(3):
        await _advance(clock_holder)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is TradeStatus.FILLED
    assert outcome.filled_qty == Decimal('1')
    assert outcome.avg_fill_price == _PRICE
    assert outcome.slices_completed == 4
    assert outcome.slices_total == 4

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.execution_mode is ExecutionMode.TIME_DCA
    assert scheme.state is SchemeState.COMPLETED


@pytest.mark.asyncio
async def test_time_dca_emits_time_dca_scheme_initialized(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
    spine: EventSpine,
    clock_holder: list[datetime],
) -> None:
    em, _ = mgr
    em.register_account(_ACCT)
    await em.submit_command(
        **_dca_kwargs(execution_params=TimeDcaParams(num_iterations=2, interval_seconds=10))
    )
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
    assert init.execution_mode is ExecutionMode.TIME_DCA
    assert init.total_qty == Decimal('1')
    assert init.slices_total == 2


@pytest.mark.asyncio
async def test_time_dca_mid_scheme_abort_cancels_with_partial_fills(
    mgr: tuple[ExecutionManager, list[TradeOutcome]],
) -> None:
    em, outcomes = mgr
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_dca_kwargs())
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
    assert outcome.filled_qty == Decimal('0.25')
    assert outcome.slices_completed == 1

    scheme = em.get_trading_state(_ACCT).schemes[command_id]
    assert scheme.state is SchemeState.CANCELED
