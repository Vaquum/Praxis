from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import aiosqlite
import pytest
import pytest_asyncio

from praxis.core.domain.enums import OrderSide, OrderStatus
from praxis.core.domain.position import Position
from praxis.core.execution_manager import AccountNotRegisteredError, ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import SubmitResult, VenueAdapter

_TS = datetime(2099, 1, 1, tzinfo=timezone.utc)
_EPOCH = 1
_ACCT = 'acc-1'
_TRADE = 'trade-1'


@pytest_asyncio.fixture
async def spine() -> AsyncGenerator[EventSpine, None]:
    conn = await aiosqlite.connect(':memory:')
    es = EventSpine(conn)
    await es.ensure_schema()
    try:
        yield es
    finally:
        await conn.close()


@pytest.fixture
def adapter() -> AsyncMock:
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
    try:
        yield em
    finally:
        for account_id in list(em._accounts):
            await em.unregister_account(account_id)


@pytest.mark.asyncio
async def test_pull_positions_unregistered_account_raises(
    mgr: ExecutionManager,
) -> None:
    with pytest.raises(AccountNotRegisteredError, match='not registered'):
        mgr.pull_positions('unknown')


@pytest.mark.asyncio
async def test_pull_positions_returns_detached_snapshot(mgr: ExecutionManager) -> None:
    mgr.register_account(_ACCT)
    runtime = mgr._accounts[_ACCT]
    key = (_TRADE, _ACCT)
    runtime.trading_state.positions[key] = Position(
        account_id=_ACCT,
        trade_id=_TRADE,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        avg_entry_price=Decimal('50000'),
    )

    snapshot = mgr.pull_positions(_ACCT)

    assert key in snapshot
    assert snapshot[key] == runtime.trading_state.positions[key]
    assert snapshot[key] is not runtime.trading_state.positions[key]

    snapshot[key].qty = Decimal('2')
    assert runtime.trading_state.positions[key].qty == Decimal('1')
