from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from typing import cast
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
    ImmediateFill,
    OrderBookLevel,
    OrderBookSnapshot,
    SubmitResult,
    TransientError,
    VenueAdapter,
)

_TS = datetime(2099, 1, 1, tzinfo=timezone.utc)
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


def _extract_decimal_arg(record: logging.LogRecord, index: int) -> Decimal:
    args = cast(tuple[Any, ...], record.args)
    return cast(Decimal, args[index])



@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.OPEN,
        immediate_fills=(),
    )
    mock.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('2')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('2')),),
        last_update_id=1,
    )
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine,
    adapter: AsyncMock,
) -> AsyncGenerator[ExecutionManager, None]:
    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter
    )
    yield manager
    for account_id in list(manager._accounts.keys()):
        await manager.unregister_account(account_id)


@pytest.mark.asyncio
async def test_logs_slippage_estimate_metrics(
    mgr: ExecutionManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

    matching = [
        record
        for record in caplog.records
        if record.msg.startswith('slippage estimate computed:')
    ]
    assert len(matching) == 1
    slippage_bps = _extract_decimal_arg(matching[0], 2)
    assert slippage_bps == Decimal('2')


@pytest.mark.asyncio
async def test_submission_proceeds_when_order_book_query_fails(
    spine: EventSpine,
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.query_order_book.side_effect = TransientError('depth unavailable')
    mgr.register_account(_ACCT)

    with caplog.at_level(logging.WARNING):
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
    messages = [r.message for r in caplog.records]
    assert any('slippage estimate skipped:' in message for message in messages)


@pytest.mark.asyncio
async def test_logs_arrival_slippage_when_estimate_is_unavailable(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.query_order_book.side_effect = TransientError('depth unavailable')
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-3',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-4',
                qty=Decimal('1'),
                price=Decimal('50020'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)

    with caplog.at_level(logging.INFO):
        await mgr.submit_command(
            **{**_CMD_KWARGS, 'reference_price': Decimal('49950')},
        )
        await asyncio.sleep(0.3)

    arrival_records = [
        record
        for record in caplog.records
        if record.msg.startswith('arrival slippage computed:')
    ]
    execution_records = [
        record
        for record in caplog.records
        if record.msg.startswith('execution slippage computed:')
    ]
    assert len(arrival_records) == 1
    assert len(execution_records) == 0


@pytest.mark.asyncio
async def test_logs_execution_slippage_bps_after_fill(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-1',
                qty=Decimal('1'),
                price=Decimal('50020'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

    matching = [
        record
        for record in caplog.records
        if record.msg.startswith('execution slippage computed:')
    ]
    assert len(matching) == 1
    execution_slippage_bps = _extract_decimal_arg(matching[0], 2)
    assert execution_slippage_bps == Decimal('4')


@pytest.mark.asyncio
async def test_logs_arrival_slippage_bps_when_reference_price_present(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-2',
                qty=Decimal('1'),
                price=Decimal('50020'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(
            **{**_CMD_KWARGS, 'reference_price': Decimal('49950')},
        )
        await asyncio.sleep(0.3)

    matching = [
        record
        for record in caplog.records
        if record.msg.startswith('arrival slippage computed:')
    ]
    assert len(matching) == 1
    arrival_slippage_bps = _extract_decimal_arg(matching[0], 2)
    assert arrival_slippage_bps == Decimal('14.01401401401401401401401401')


@pytest.mark.asyncio
async def test_logs_execution_slippage_for_sell_side(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-2',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-3',
                qty=Decimal('1'),
                price=Decimal('49980'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(
            **{
                **_CMD_KWARGS,
                'side': OrderSide.SELL,
                'reference_price': Decimal('50000'),
            },
        )
        await asyncio.sleep(0.3)

    execution_records = [
        record
        for record in caplog.records
        if record.msg.startswith('execution slippage computed:')
    ]
    arrival_records = [
        record
        for record in caplog.records
        if record.msg.startswith('arrival slippage computed:')
    ]
    assert len(execution_records) == 1
    assert len(arrival_records) == 1
    execution_slippage_bps = _extract_decimal_arg(execution_records[0], 2)
    arrival_slippage_bps = _extract_decimal_arg(arrival_records[0], 2)
    assert execution_slippage_bps == Decimal('-4')
    assert arrival_slippage_bps == Decimal('-4')
