'''
Tests for the Iceberg execution mode in ExecutionManager (WP-Praxis-0007):
a single native-iceberg LIMIT order (Binance icebergQty) worked as the
venue refills the visible slice; incremental fills drive PARTIAL then
FILLED outcomes through the shared WebSocket-outcome path.
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
    TradeStatus,
)
from praxis.core.domain.events import FillReceived
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    SubmitResult,
    SymbolFilters,
    TransientError,
    VenueAdapter,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_LIMIT = Decimal('50000')
_ORDER_TYPE_ARG_INDEX = 3
_QTY_ARG_INDEX = 4


def _iceberg_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.LIMIT,
        'execution_mode': ExecutionMode.ICEBERG,
        'execution_params': IcebergParams(
            display_qty=Decimal('0.1'), limit_price=_LIMIT,
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
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='v-ice', status=OrderStatus.OPEN, immediate_fills=(),
    )
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


class TestIcebergSubmit:

    @pytest.mark.asyncio
    async def test_submits_limit_with_iceberg_qty_and_rests_pending(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)
        await em.submit_command(**_iceberg_kwargs())
        await asyncio.sleep(0.3)

        call = adapter.submit_order.call_args
        assert call.args[_ORDER_TYPE_ARG_INDEX] is OrderType.LIMIT
        assert call.args[_QTY_ARG_INDEX] == Decimal('1')
        assert call.kwargs['price'] == _LIMIT
        assert call.kwargs['iceberg_qty'] == Decimal('0.1')

        assert outcomes[-1].status is TradeStatus.PENDING

    @pytest.mark.asyncio
    async def test_display_equal_to_total_submits_plain_limit(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        await em.submit_command(
            **_iceberg_kwargs(
                execution_params=IcebergParams(
                    display_qty=Decimal('1'), limit_price=_LIMIT,
                ),
            ),
        )
        await asyncio.sleep(0.3)

        assert adapter.submit_order.call_args.kwargs['iceberg_qty'] is None

    @pytest.mark.asyncio
    async def test_submit_failure_rejects(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        adapter.submit_order.side_effect = TransientError('venue 5xx')
        em, outcomes = mgr
        em.register_account(_ACCT)
        await em.submit_command(**_iceberg_kwargs())
        await asyncio.sleep(0.3)

        assert outcomes[-1].status is TradeStatus.REJECTED


class TestIcebergFillProgression:

    @pytest.mark.asyncio
    async def test_incremental_ws_fills_drive_partial_then_filled(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, outcomes = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_iceberg_kwargs())
        await asyncio.sleep(0.3)

        client_order_id = generate_client_order_id(
            ExecutionMode.ICEBERG, command_id, sequence=0,
        )

        def _fill(trade_id_suffix: str, qty: Decimal) -> FillReceived:
            return FillReceived(
                account_id=_ACCT,
                timestamp=_T0,
                client_order_id=client_order_id,
                venue_order_id='v-ice',
                venue_trade_id=f't-{trade_id_suffix}',
                trade_id=_TRADE,
                command_id=command_id,
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                qty=qty,
                price=_LIMIT,
                fee=Decimal('0'),
                fee_asset='USDT',
                is_maker=True,
            )

        em.enqueue_ws_event(_ACCT, _fill('1', Decimal('0.6')))
        await asyncio.sleep(0.2)
        assert outcomes[-1].status is TradeStatus.PARTIAL

        em.enqueue_ws_event(_ACCT, _fill('2', Decimal('0.4')))
        await asyncio.sleep(0.2)
        assert outcomes[-1].status is TradeStatus.FILLED
        assert outcomes[-1].filled_qty == Decimal('1')
