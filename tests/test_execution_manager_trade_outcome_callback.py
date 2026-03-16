from __future__ import annotations

import asyncio
from datetime import datetime, timezone
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
)
from praxis.core.domain.events import TradeOutcomeProduced
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import SubmitResult, VenueAdapter

_TS = datetime(2099, 1, 1, tzinfo=timezone.utc)
_ACCT = 'acc-1'
_EPOCH = 1
_CMD_KWARGS: dict[str, Any] = {
    'trade_id': 'trade-1',
    'account_id': _ACCT,
    'symbol': 'BTCUSDT',
    'side': OrderSide.BUY,
    'qty': Decimal('1'),
    'order_type': OrderType.LIMIT,
    'execution_mode': ExecutionMode.SINGLE_SHOT,
    'execution_params': SingleShotParams(price=Decimal('50000')),
    'timeout': 60,
    'reference_price': None,
    'maker_preference': MakerPreference.NO_PREFERENCE,
    'stp_mode': STPMode.NONE,
    'created_at': _TS,
}



@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.OPEN,
        immediate_fills=(),
    )
    return mock


@pytest.mark.asyncio
async def test_callback_awaited_once_per_produced_outcome(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    callback = AsyncMock()
    mgr = ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=callback,
    )
    mgr.register_account(_ACCT)

    await mgr.submit_command(**_CMD_KWARGS)
    await mgr.submit_command(**{**_CMD_KWARGS, 'trade_id': 'trade-2'})
    await asyncio.sleep(0.5)

    events = await spine.read(_EPOCH, after_seq=0)
    produced = [e for _, e in events if isinstance(e, TradeOutcomeProduced)]
    assert len(produced) == 2
    assert callback.await_count == len(produced)

    await mgr.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_callback_failure_does_not_block_outcome_production(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    callback_calls = 0

    async def callback(outcome: TradeOutcome) -> None:
        nonlocal callback_calls
        callback_calls += 1
        events = await spine.read(_EPOCH, after_seq=0)
        assert any(
            isinstance(event, TradeOutcomeProduced)
            and event.command_id == outcome.command_id
            for _, event in events
        )
        raise RuntimeError('callback failed')

    mgr = ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=callback,
    )
    mgr.register_account(_ACCT)

    await mgr.submit_command(**_CMD_KWARGS)
    await mgr.submit_command(**{**_CMD_KWARGS, 'trade_id': 'trade-2'})
    await asyncio.sleep(0.5)

    events = await spine.read(_EPOCH, after_seq=0)
    produced = [e for _, e in events if isinstance(e, TradeOutcomeProduced)]
    assert len(produced) == 2
    assert callback_calls == len(produced)

    await mgr.unregister_account(_ACCT)
