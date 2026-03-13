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
    OrderBookLevel,
    OrderBookSnapshot,
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
            immediate_fills=(),
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
            immediate_fills=(fill,),
        )
        assert len(result.immediate_fills) == 1
        assert result.immediate_fills[0].venue_trade_id == 'vt-001'

    def test_submit_result_fills_immutable(self) -> None:

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
            immediate_fills=(fill,),
        )
        with pytest.raises(AttributeError):
            result.immediate_fills.append(fill)  # type: ignore[attr-defined]

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

    def test_order_book_level_frozen(self) -> None:
        level = OrderBookLevel(price=Decimal('50000'), qty=Decimal('1.5'))
        with pytest.raises(AttributeError):
            level.price = Decimal('49999')  # type: ignore[misc]

    def test_order_book_level_fields(self) -> None:
        level = OrderBookLevel(price=Decimal('50000.01'), qty=Decimal('0.5'))
        assert level.price == Decimal('50000.01')
        assert level.qty == Decimal('0.5')

    def test_order_book_snapshot_frozen(self) -> None:
        snap = OrderBookSnapshot(bids=(), asks=(), last_update_id=100)
        with pytest.raises(AttributeError):
            snap.last_update_id = 200  # type: ignore[misc]

    def test_order_book_snapshot_fields(self) -> None:
        bid = OrderBookLevel(price=Decimal('50000'), qty=Decimal('1.0'))
        ask = OrderBookLevel(price=Decimal('50001'), qty=Decimal('2.0'))
        snap = OrderBookSnapshot(
            bids=(bid,), asks=(ask,), last_update_id=42,
        )
        assert len(snap.bids) == 1
        assert len(snap.asks) == 1
        assert snap.bids[0].price == Decimal('50000')
        assert snap.asks[0].qty == Decimal('2.0')
        assert snap.last_update_id == 42


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

    def test_order_rejected_error_picklable(self) -> None:

        import pickle

        err = OrderRejectedError(
            'rejected',
            venue_code=_BINANCE_DUPLICATE_ORDER_CODE,
            reason='Duplicate order',
        )
        restored = pickle.loads(pickle.dumps(err))  # noqa: S301
        assert restored.venue_code == _BINANCE_DUPLICATE_ORDER_CODE
        assert restored.reason == 'Duplicate order'
        assert restored.message == 'rejected'

    def test_catch_venue_error_catches_subclass(self) -> None:
        with pytest.raises(VenueError):
            raise RateLimitError('rate limited')

    def test_rate_limit_error_retry_after(self) -> None:

        err = RateLimitError('rate limited', retry_after=30.0)
        assert err.retry_after == 30.0
        assert err.message == 'rate limited'

    def test_rate_limit_error_retry_after_default_none(self) -> None:

        err = RateLimitError('rate limited')
        assert err.retry_after is None

    def test_rate_limit_error_status_code(self) -> None:

        err = RateLimitError('rate limited', status_code=429)
        assert err.status_code == 429

    def test_rate_limit_error_status_code_default_none(self) -> None:

        err = RateLimitError('rate limited')
        assert err.status_code is None


class TestVenueAdapterProtocol:

    def test_protocol_is_runtime_checkable(self) -> None:
        assert not isinstance(object(), VenueAdapter)

    def test_conforming_class_isinstance(self) -> None:
        class _FakeAdapter:

            def register_account(self, *_args: Any, **_kwargs: Any) -> None: ...

            def unregister_account(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def submit_order(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def cancel_order(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_order(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_open_orders(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_balance(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_trades(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def get_exchange_info(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def get_server_time(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def query_order_book(self, *_args: Any, **_kwargs: Any) -> None: ...

            async def cancel_order_list(self, *_args: Any, **_kwargs: Any) -> None: ...

        assert isinstance(_FakeAdapter(), VenueAdapter)

    def test_non_conforming_class_not_isinstance(self) -> None:
        class _Incomplete:

            async def submit_order(self) -> None: ...

        assert not isinstance(_Incomplete(), VenueAdapter)
