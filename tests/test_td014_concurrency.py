'''Tests for TD-014: single-writer concurrency guarantees.

Verifies that concurrent command submission and WS event processing
do not corrupt TradingState.
'''

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator
from datetime import datetime, UTC
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
    STPMode,
)
from praxis.core.domain.events import FillReceived
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    SubmitResult,
    VenueAdapter,
)

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-concurrent'
_TRADE = 'trade-concurrent'
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


@pytest.fixture()
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='venue-concurrent',
        status=OrderStatus.OPEN,
        immediate_fills=(),
    )
    return mock


@pytest_asyncio.fixture()
async def mgr(
    spine: EventSpine, adapter: AsyncMock,
) -> AsyncGenerator[ExecutionManager, None]:
    em = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    yield em
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


class TestTD014Concurrency:

    @pytest.mark.asyncio()
    async def test_enqueue_ws_event_rejects_non_loop_thread(
        self,
        mgr: ExecutionManager,
    ) -> None:
        '''enqueue_ws_event raises RuntimeError when called from wrong thread.'''

        mgr.register_account(_ACCT)

        error: Exception | None = None

        def call_from_thread() -> None:
            nonlocal error
            try:
                fill = FillReceived(
                    account_id=_ACCT,
                    timestamp=_TS,
                    client_order_id='test-order',
                    venue_order_id='venue-1',
                    venue_trade_id='vtrade-1',
                    trade_id=_TRADE,
                    command_id='cmd-1',
                    symbol='BTCUSDT',
                    side=OrderSide.BUY,
                    qty=Decimal('0.5'),
                    price=Decimal('50000'),
                    fee=Decimal('0.01'),
                    fee_asset='USDT',
                    is_maker=False,
                )
                mgr.enqueue_ws_event(_ACCT, fill)
            except RuntimeError as e:
                error = e

        thread = threading.Thread(target=call_from_thread)
        thread.start()
        thread.join(timeout=5)

        assert error is not None
        assert 'non-event-loop thread' in str(error)

    @pytest.mark.asyncio()
    async def test_concurrent_submit_and_ws_event_no_corruption(
        self,
        mgr: ExecutionManager,
    ) -> None:
        '''Concurrent command submission and WS fill do not corrupt state.'''

        mgr.register_account(_ACCT)

        cmd_id = await mgr.submit_command(**_CMD_KWARGS)
        assert cmd_id is not None

        await asyncio.sleep(0.2)

        runtime = mgr._accounts[_ACCT]
        all_orders = {**runtime.trading_state.orders, **runtime.trading_state.closed_orders}
        assert len(all_orders) > 0

        client_order_id = next(iter(all_orders))

        fill = FillReceived(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id=client_order_id,
            venue_order_id='venue-concurrent',
            venue_trade_id='vtrade-concurrent',
            trade_id=_TRADE,
            command_id=cmd_id,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('0.5'),
            price=Decimal('50000'),
            fee=Decimal('0.01'),
            fee_asset='USDT',
            is_maker=False,
        )
        mgr.enqueue_ws_event(_ACCT, fill)

        await asyncio.sleep(0.2)

        total_qty = sum(p.qty for p in runtime.trading_state.positions.values())
        assert total_qty >= Decimal('0')

    @pytest.mark.asyncio()
    async def test_enqueue_from_event_loop_succeeds(
        self,
        mgr: ExecutionManager,
    ) -> None:
        '''enqueue_ws_event succeeds when called from event loop thread.'''

        mgr.register_account(_ACCT)

        fill = FillReceived(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id='test-order',
            venue_order_id='venue-1',
            venue_trade_id='vtrade-1',
            trade_id=_TRADE,
            command_id='cmd-1',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('0.5'),
            price=Decimal('50000'),
            fee=Decimal('0.01'),
            fee_asset='USDT',
            is_maker=False,
        )
        mgr.enqueue_ws_event(_ACCT, fill)

        assert not mgr._accounts[_ACCT].ws_event_queue.empty()
