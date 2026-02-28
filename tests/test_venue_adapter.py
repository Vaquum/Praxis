'''
Tests for praxis.infrastructure.venue_adapter protocol and response types.
'''

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.infrastructure.venue_adapter import (
    AuthenticationError,
    BalanceEntry,
    CancelResult,
    ImmediateFill,
    NotFoundError,
    OrderRejectedError,
    RateLimitError,
    SubmitResult,
    SymbolFilters,
    TransientError,
    VenueAdapter,
    VenueError,
    VenueOrder,
    VenueTrade,
)


_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
_BINANCE_DUPLICATE_ORDER_CODE = -2010


class TestResponseDataclasses:

    def test_immediate_fill_frozen(self) -> None:
        fill = ImmediateFill(
            venue_trade_id='vt-001',
            qty=Decimal('0.5'),
            price=Decimal('50000'),
            fee=Decimal('0.001'),
            fee_asset='BTC',
            is_maker=False,
        )
        with pytest.raises(AttributeError):
            fill.qty = Decimal('1.0')  # type: ignore[misc]

    def test_submit_result_frozen(self) -> None:
        result = SubmitResult(
            venue_order_id='vo-001',
            status=OrderStatus.FILLED,
            immediate_fills=[],
        )
        with pytest.raises(AttributeError):
            result.status = OrderStatus.OPEN  # type: ignore[misc]

    def test_submit_result_with_immediate_fills(self) -> None:
        fill = ImmediateFill(
            venue_trade_id='vt-001',
            qty=Decimal('0.5'),
            price=Decimal('50000'),
            fee=Decimal('0.001'),
            fee_asset='BTC',
            is_maker=False,
        )
        result = SubmitResult(
            venue_order_id='vo-001',
            status=OrderStatus.FILLED,
            immediate_fills=[fill],
        )
        assert len(result.immediate_fills) == 1
        assert result.immediate_fills[0].venue_trade_id == 'vt-001'

    def test_cancel_result_frozen(self) -> None:
        result = CancelResult(
            venue_order_id='vo-001',
            status=OrderStatus.CANCELED,
        )
        with pytest.raises(AttributeError):
            result.venue_order_id = 'vo-002'  # type: ignore[misc]

    def test_venue_order_frozen(self) -> None:
        order = VenueOrder(
            venue_order_id='vo-001',
            client_order_id='new_order-cmd1-0',
            status=OrderStatus.OPEN,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal('1.0'),
            filled_qty=Decimal('0'),
            price=Decimal('50000'),
        )
        with pytest.raises(AttributeError):
            order.filled_qty = Decimal('0.5')  # type: ignore[misc]

    def test_venue_order_market_no_price(self) -> None:
        order = VenueOrder(
            venue_order_id='vo-001',
            client_order_id='new_order-cmd1-0',
            status=OrderStatus.FILLED,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal('1.0'),
            filled_qty=Decimal('1.0'),
            price=None,
        )
        assert order.price is None

    def test_venue_trade_frozen(self) -> None:
        trade = VenueTrade(
            venue_trade_id='vt-001',
            venue_order_id='vo-001',
            client_order_id='new_order-cmd1-0',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('0.5'),
            price=Decimal('50000'),
            fee=Decimal('0.001'),
            fee_asset='BTC',
            is_maker=True,
            timestamp=_TS,
        )
        with pytest.raises(AttributeError):
            trade.price = Decimal('51000')  # type: ignore[misc]

    def test_venue_trade_rejects_naive_timestamp(self) -> None:
        with pytest.raises(ValueError, match='timezone-aware'):
            VenueTrade(
                venue_trade_id='vt-001',
                venue_order_id='vo-001',
                client_order_id='new_order-cmd1-0',
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                qty=Decimal('0.5'),
                price=Decimal('50000'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=True,
                timestamp=datetime(2026, 1, 1),
            )

    def test_balance_entry_frozen(self) -> None:
        entry = BalanceEntry(
            asset='BTC',
            free=Decimal('1.5'),
            locked=Decimal('0.3'),
        )
        with pytest.raises(AttributeError):
            entry.free = Decimal('2.0')  # type: ignore[misc]

    def test_symbol_filters_frozen(self) -> None:
        filters = SymbolFilters(
            symbol='BTCUSDT',
            tick_size=Decimal('0.01'),
            lot_step=Decimal('0.00001'),
            lot_min=Decimal('0.00001'),
            lot_max=Decimal('9000'),
            min_notional=Decimal('10'),
        )
        with pytest.raises(AttributeError):
            filters.tick_size = Decimal('0.001')  # type: ignore[misc]


class TestErrorHierarchy:

    def test_venue_error_is_exception(self) -> None:
        assert issubclass(VenueError, Exception)

    @pytest.mark.parametrize(
        'cls',
        [
            OrderRejectedError,
            RateLimitError,
            AuthenticationError,
            TransientError,
            NotFoundError,
        ],
    )
    def test_subclass_of_venue_error(self, cls: type) -> None:
        assert issubclass(cls, VenueError)

    def test_venue_error_message(self) -> None:
        err = VenueError('connection failed')
        assert err.message == 'connection failed'
        assert str(err) == 'connection failed'

    def test_order_rejected_error_attributes(self) -> None:
        err = OrderRejectedError(
            'rejected',
            venue_code=_BINANCE_DUPLICATE_ORDER_CODE,
            reason='Duplicate order',
        )
        assert err.message == 'rejected'
        assert err.venue_code == _BINANCE_DUPLICATE_ORDER_CODE
        assert err.reason == 'Duplicate order'

    def test_catch_venue_error_catches_subclass(self) -> None:
        with pytest.raises(VenueError):
            raise RateLimitError('rate limited')


class TestVenueAdapterProtocol:

    def test_protocol_is_runtime_checkable(self) -> None:
        assert not isinstance(object(), VenueAdapter)

    def test_conforming_class_isinstance(self) -> None:
        class _FakeAdapter:

            async def submit_order(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def cancel_order(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_order(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_open_orders(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_balance(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_trades(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def get_exchange_info(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def get_server_time(self, *_args: Any, **_kwargs: Any) -> None: ...

        assert isinstance(_FakeAdapter(), VenueAdapter)

    def test_non_conforming_class_not_isinstance(self) -> None:
        class _Incomplete:

            async def submit_order(self) -> None: ...

        assert not isinstance(_Incomplete(), VenueAdapter)
