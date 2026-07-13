'''Tests for ExecutionManager rescue-by-clientOrderId on POST failures (MAJOR-002).

Covers `_process_command`'s response to non-idempotent POST failures
(`OrderSubmitTimeoutError` and `DuplicateClientOrderIdError`):
- venue confirms the order is live → `OrderSubmitted` event + normal lifecycle
  instead of REJECTED;
- venue confirms no such order → `OrderSubmitFailed` + REJECTED;
- venue query itself fails → `OrderSubmitFailed` + REJECTED (conservative).
'''

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
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
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    OrderBookLevel,
    OrderBookSnapshot,
    DuplicateClientOrderIdError,
    NotFoundError,
    OrderSubmitTimeoutError,
    SubmitResult,
    TransientError,
    VenueAdapter,
    VenueOrder,
)

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
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


def _venue_order(status: OrderStatus = OrderStatus.OPEN) -> VenueOrder:
    return VenueOrder(
        venue_order_id='v-rescued-1',
        client_order_id='cid',
        status=status,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        price=Decimal('50000'),
    )


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='v-1', status=OrderStatus.OPEN, immediate_fills=(),
    )
    mock.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('2')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('2')),),
        last_update_id=1,
    )
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine, adapter: AsyncMock,
) -> AsyncGenerator[ExecutionManager, None]:
    em = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    yield em
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


class TestRescueOnSubmitTimeout:

    @pytest.mark.asyncio
    async def test_timeout_with_live_venue_order_records_submitted_not_rejected(
        self, mgr: ExecutionManager, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        '''POST timeouts but venue holds the order → OrderSubmitted, no REJECTED.'''

        adapter.submit_order.side_effect = OrderSubmitTimeoutError(
            'transport timeout', client_order_id='cid-rescue',
        )
        adapter.query_order.return_value = _venue_order(status=OrderStatus.OPEN)

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]

        assert 'OrderSubmitFailed' not in types
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitted',
            'TradeOutcomeProduced',
        ]
        adapter.query_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_timeout_with_no_venue_order_records_submit_failed(
        self, mgr: ExecutionManager, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        '''POST timeouts and venue has no such order → OrderSubmitFailed + REJECTED.'''

        adapter.submit_order.side_effect = OrderSubmitTimeoutError(
            'transport timeout', client_order_id='cid-rescue',
        )
        adapter.query_order.side_effect = NotFoundError('not found on venue')

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitFailed',
            'TradeOutcomeProduced',
        ]
        adapter.query_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rescue_query_failure_falls_back_to_submit_failed(
        self, mgr: ExecutionManager, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        '''Conservative: when the rescue query itself fails the command is
        classified REJECTED — operator sees the warn log and reconcile heals
        if the venue actually held the order.'''

        adapter.submit_order.side_effect = OrderSubmitTimeoutError(
            'transport timeout', client_order_id='cid-rescue',
        )
        adapter.query_order.side_effect = TransientError('venue 5xx')

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitFailed',
            'TradeOutcomeProduced',
        ]


class TestRescueOnDuplicateClientOrderId:

    @pytest.mark.asyncio
    async def test_duplicate_with_live_venue_order_records_submitted(
        self, mgr: ExecutionManager, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        '''-2010 + venue confirms live → OrderSubmitted, no REJECTED.'''

        adapter.submit_order.side_effect = DuplicateClientOrderIdError(
            'duplicate clientOrderId', client_order_id='cid-rescue',
        )
        adapter.query_order.return_value = _venue_order(status=OrderStatus.OPEN)

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitted',
            'TradeOutcomeProduced',
        ]

    @pytest.mark.asyncio
    async def test_duplicate_with_no_venue_order_records_submit_failed(
        self, mgr: ExecutionManager, spine: EventSpine, adapter: AsyncMock,
    ) -> None:
        '''-2010 + NotFoundError on rescue → REJECTED (defensive).'''

        adapter.submit_order.side_effect = DuplicateClientOrderIdError(
            'duplicate clientOrderId', client_order_id='cid-rescue',
        )
        adapter.query_order.side_effect = NotFoundError('not found')

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitFailed',
            'TradeOutcomeProduced',
        ]
