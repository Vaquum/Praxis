'''
Tests for ExecutionManager admission control (WP-Praxis-0007):
stale-command expiry at dispatch and the bounded, fail-closed command queue.
'''

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.events import CommandAccepted
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.twap_params import TwapParams
from praxis.core import execution_manager as em_module
from praxis.core.execution_manager import CommandQueueFullError, ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import SubmitResult, VenueAdapter

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_EPOCH = 1


def _cmd(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': 'trade-1',
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.SINGLE_SHOT,
        'execution_params': SingleShotParams(),
        'timeout': 10,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


@pytest.fixture
def clock_holder() -> list[datetime]:
    return [_T0]


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='v-1', status=OrderStatus.FILLED, immediate_fills=(),
    )
    mock.cached_filters.return_value = None
    return mock


def _manager(
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
    outcomes: list[TradeOutcome],
) -> ExecutionManager:
    async def _capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    return ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=_capture,
        clock=lambda: clock_holder[0],
    )


@pytest.mark.asyncio
async def test_stale_command_expires_at_dispatch(
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, adapter, clock_holder, outcomes)
    em.register_account(_ACCT)
    em.set_reconciling(_ACCT, True)

    await em.submit_command(
        **_cmd(
            timeout=10,
            execution_mode=ExecutionMode.TWAP,
            execution_params=TwapParams(num_slices=2, interval_seconds=10),
        )
    )
    clock_holder[0] = _T0 + timedelta(seconds=100)
    em.set_reconciling(_ACCT, False)
    await asyncio.sleep(0.3)

    assert len(outcomes) == 1
    assert outcomes[0].status is TradeStatus.EXPIRED
    assert outcomes[0].filled_qty == Decimal('0')
    adapter.submit_order.assert_not_awaited()

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_command_queue_full_rejects_fail_closed(
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, adapter, clock_holder, outcomes)

    monkeypatch.setattr(em_module, '_COMMAND_QUEUE_MAXSIZE', 1)
    em.register_account(_ACCT)
    em.set_reconciling(_ACCT, True)

    await em.submit_command(**_cmd())

    with pytest.raises(CommandQueueFullError, match='at capacity'):
        await em.submit_command(**_cmd())

    events = await spine.read(_EPOCH, after_seq=0)
    accepted = [e for _, e in events if isinstance(e, CommandAccepted)]
    assert len(accepted) == 1

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_queue_reservation_released_on_append_failure(
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, adapter, clock_holder, outcomes)
    em.register_account(_ACCT)
    runtime = em._accounts[_ACCT]

    em._event_spine.append = AsyncMock(side_effect=RuntimeError('spine down'))

    with pytest.raises(RuntimeError, match='spine down'):
        await em.submit_command(**_cmd())

    assert runtime.queue_reservations == 0
    assert runtime.command_queue.qsize() == 0

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_concurrent_submit_at_capacity_writes_one_accept(
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, adapter, clock_holder, outcomes)

    monkeypatch.setattr(em_module, '_COMMAND_QUEUE_MAXSIZE', 1)
    em.register_account(_ACCT)
    em.set_reconciling(_ACCT, True)

    results = await asyncio.gather(
        em.submit_command(**_cmd()),
        em.submit_command(**_cmd()),
        return_exceptions=True,
    )

    accepted_ok = [r for r in results if isinstance(r, str)]
    rejected = [r for r in results if isinstance(r, CommandQueueFullError)]
    assert len(accepted_ok) == 1
    assert len(rejected) == 1

    events = await spine.read(_EPOCH, after_seq=0)
    accepted = [e for _, e in events if isinstance(e, CommandAccepted)]
    assert len(accepted) == 1

    await em.unregister_account(_ACCT)
