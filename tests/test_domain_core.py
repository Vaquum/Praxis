'''
Tests for praxis.core.domain dataclasses and enums.
'''

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from praxis.core.domain import (
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)

_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fill(
    venue_trade_id: str = 'vt-001',
    qty: Decimal = Decimal('0.5'),
    price: Decimal = Decimal('50000.00'),
    fee: Decimal = Decimal('0.001'),
) -> Fill:

    return Fill(
        venue_trade_id=venue_trade_id,
        venue_order_id='vo-001',
        client_order_id='new_order-cmd1-0',
        account_id='acc-1',
        trade_id='trade-1',
        command_id='cmd-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        price=price,
        fee=fee,
        fee_asset='BTC',
        is_maker=True,
        timestamp=_TS,
    )


def _order(
    status: OrderStatus = OrderStatus.SUBMITTING,
    qty: Decimal = Decimal('1.0'),
    filled_qty: Decimal = Decimal('0'),
    price: Decimal | None = Decimal('50000.00'),
    stop_price: Decimal | None = None,
    order_type: OrderType = OrderType.LIMIT,
) -> Order:

    return Order(
        client_order_id='new_order-cmd1-0',
        venue_order_id=None,
        account_id='acc-1',
        command_id='cmd-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=order_type,
        qty=qty,
        filled_qty=filled_qty,
        price=price,
        stop_price=stop_price,
        status=status,
        created_at=_TS,
        updated_at=_TS,
    )


def _position(qty: Decimal = Decimal('1.0'), avg_entry_price: Decimal = Decimal('50000.00')) -> Position:

    return Position(
        account_id='acc-1',
        trade_id='trade-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        avg_entry_price=avg_entry_price,
    )


def test_order_side_members() -> None:

    assert set(OrderSide) == {OrderSide.BUY, OrderSide.SELL}


def test_order_type_members() -> None:

    expected = {
        OrderType.MARKET,
        OrderType.LIMIT,
        OrderType.LIMIT_IOC,
        OrderType.STOP,
        OrderType.STOP_LIMIT,
        OrderType.TAKE_PROFIT,
        OrderType.TP_LIMIT,
        OrderType.OCO,
    }
    assert set(OrderType) == expected


def test_order_status_members() -> None:

    expected = {
        OrderStatus.SUBMITTING,
        OrderStatus.OPEN,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    }
    assert set(OrderStatus) == expected


def test_enum_values_are_strings() -> None:

    for enum_cls in (OrderSide, OrderType, OrderStatus):
        for member in enum_cls:
            assert isinstance(member.value, str)


def test_fill_creation() -> None:

    fill = _fill()
    assert fill.symbol == 'BTCUSDT'
    assert fill.side == OrderSide.BUY
    assert fill.qty == Decimal('0.5')


def test_fill_frozen() -> None:

    fill = _fill()
    with pytest.raises(AttributeError):
        fill.qty = Decimal('999')  # type: ignore[misc]


def test_fill_dedup_key_with_venue_trade_id() -> None:

    fill = _fill(venue_trade_id='vt-001')
    assert fill.dedup_key == 'vt-001'


def test_fill_dedup_key_fallback() -> None:

    fill = _fill(venue_trade_id='')
    assert fill.dedup_key == (
        fill.venue_order_id,
        fill.price,
        fill.qty,
        fill.timestamp,
    )


def test_fill_financial_values_are_decimal() -> None:

    fill = _fill()
    assert isinstance(fill.qty, Decimal)
    assert isinstance(fill.price, Decimal)
    assert isinstance(fill.fee, Decimal)


def test_order_creation() -> None:

    order = _order()
    assert order.symbol == 'BTCUSDT'
    assert order.status == OrderStatus.SUBMITTING
    assert order.venue_order_id is None


def test_order_is_terminal_for_terminal_statuses() -> None:

    for status in (
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    ):
        assert _order(status=status).is_terminal is True


def test_order_is_terminal_for_non_terminal_statuses() -> None:

    for status in (
        OrderStatus.SUBMITTING,
        OrderStatus.OPEN,
        OrderStatus.PARTIALLY_FILLED,
    ):
        assert _order(status=status).is_terminal is False


def test_order_remaining_qty() -> None:

    order = _order(qty=Decimal('1.0'), filled_qty=Decimal('0.3'))
    assert order.remaining_qty == Decimal('0.7')


def test_order_status_mutation() -> None:

    order = _order(status=OrderStatus.SUBMITTING)
    order.status = OrderStatus.OPEN
    assert order.status == OrderStatus.OPEN


def test_order_financial_values_are_decimal() -> None:

    order = _order()
    assert isinstance(order.qty, Decimal)
    assert isinstance(order.filled_qty, Decimal)
    assert isinstance(order.price, Decimal)


def test_position_creation() -> None:

    pos = _position()
    assert pos.symbol == 'BTCUSDT'
    assert pos.side == OrderSide.BUY
    assert pos.qty == Decimal('1.0')


def test_position_is_closed_at_zero() -> None:

    assert _position(qty=Decimal('0')).is_closed is True


def test_position_is_not_closed_with_quantity() -> None:

    assert _position(qty=Decimal('0.5')).is_closed is False


def test_position_financial_values_are_decimal() -> None:

    pos = _position()
    assert isinstance(pos.qty, Decimal)
    assert isinstance(pos.avg_entry_price, Decimal)


def test_fill_rejects_naive_timestamp() -> None:

    with pytest.raises(ValueError, match='timezone-aware'):
        Fill(
            venue_trade_id='vt-001',
            venue_order_id='vo-001',
            client_order_id='new_order-cmd1-0',
            account_id='acc-1',
            trade_id='trade-1',
            command_id='cmd-1',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('0.5'),
            price=Decimal('50000.00'),
            fee=Decimal('0.001'),
            fee_asset='BTC',
            is_maker=True,
            timestamp=datetime(2026, 1, 1),
        )


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_fill_rejects_non_positive_qty(bad: Decimal) -> None:

    with pytest.raises(ValueError, match='positive'):
        _fill(qty=bad)


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_fill_rejects_non_positive_price(bad: Decimal) -> None:

    with pytest.raises(ValueError, match='positive'):
        _fill(price=bad)


def test_fill_rejects_negative_fee() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        _fill(fee=Decimal('-1'))


def test_order_rejects_naive_created_at() -> None:

    with pytest.raises(ValueError, match='timezone-aware'):
        Order(
            client_order_id='new_order-cmd1-0',
            venue_order_id=None,
            account_id='acc-1',
            command_id='cmd-1',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal('1.0'),
            filled_qty=Decimal('0'),
            price=Decimal('50000.00'),
            stop_price=None,
            status=OrderStatus.SUBMITTING,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_order_rejects_naive_updated_at() -> None:

    with pytest.raises(ValueError, match='timezone-aware'):
        Order(
            client_order_id='new_order-cmd1-0',
            venue_order_id=None,
            account_id='acc-1',
            command_id='cmd-1',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal('1.0'),
            filled_qty=Decimal('0'),
            price=Decimal('50000.00'),
            stop_price=None,
            status=OrderStatus.SUBMITTING,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1),
        )


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_order_rejects_non_positive_qty(bad: Decimal) -> None:

    with pytest.raises(ValueError, match='positive'):
        _order(qty=bad)


def test_order_rejects_negative_filled_qty() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        _order(filled_qty=Decimal('-1'))


def test_position_rejects_negative_qty() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        _position(qty=Decimal('-1'))


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_order_rejects_non_positive_price(bad: Decimal) -> None:

    with pytest.raises(ValueError, match='positive'):
        _order(price=bad)


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_order_rejects_non_positive_stop_price(bad: Decimal) -> None:

    with pytest.raises(ValueError, match='positive'):
        _order(stop_price=bad)


def test_order_rejects_filled_qty_exceeding_qty() -> None:

    with pytest.raises(ValueError, match='cannot exceed'):
        _order(qty=Decimal('1.0'), filled_qty=Decimal('2.0'))


def test_position_rejects_negative_avg_entry_price() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        _position(avg_entry_price=Decimal('-1'))


def test_order_creation_market_with_no_price() -> None:

    order = _order(order_type=OrderType.MARKET, price=None)
    assert order.price is None
    assert order.order_type == OrderType.MARKET


def test_order_rejects_market_with_price() -> None:

    with pytest.raises(ValueError, match='MARKET'):
        _order(order_type=OrderType.MARKET, price=Decimal('50000.00'))


@pytest.mark.parametrize('field', ['account_id', 'trade_id', 'symbol'])
def test_position_rejects_empty_string(field: str) -> None:

    kwargs = {
        'account_id': 'acc-1',
        'trade_id': 'trade-1',
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1.0'),
        'avg_entry_price': Decimal('50000.00'),
    }
    kwargs[field] = ''
    with pytest.raises(ValueError, match='non-empty string'):
        Position(**kwargs)


@pytest.mark.parametrize('field', ['client_order_id', 'account_id', 'command_id', 'symbol'])
def test_order_rejects_empty_string(field: str) -> None:

    kwargs = {
        'client_order_id': 'new_order-cmd1-0',
        'venue_order_id': None,
        'account_id': 'acc-1',
        'command_id': 'cmd-1',
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'order_type': OrderType.LIMIT,
        'qty': Decimal('1.0'),
        'filled_qty': Decimal('0'),
        'price': Decimal('50000.00'),
        'stop_price': None,
        'status': OrderStatus.SUBMITTING,
        'created_at': _TS,
        'updated_at': _TS,
    }
    kwargs[field] = ''
    with pytest.raises(ValueError, match='non-empty string'):
        Order(**kwargs)


@pytest.mark.parametrize('field', [
    'venue_order_id', 'client_order_id',
    'account_id', 'trade_id', 'command_id', 'symbol', 'fee_asset',
])
def test_fill_rejects_empty_string(field: str) -> None:

    kwargs = {
        'venue_trade_id': 'vt-001',
        'venue_order_id': 'vo-001',
        'client_order_id': 'new_order-cmd1-0',
        'account_id': 'acc-1',
        'trade_id': 'trade-1',
        'command_id': 'cmd-1',
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('0.5'),
        'price': Decimal('50000.00'),
        'fee': Decimal('0.001'),
        'fee_asset': 'BTC',
        'is_maker': True,
        'timestamp': _TS,
    }
    kwargs[field] = ''
    with pytest.raises(ValueError, match='non-empty string'):
        Fill(**kwargs)
