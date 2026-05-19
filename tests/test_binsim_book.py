'''Tests for praxis.binsim.book.OrderBook.'''

from __future__ import annotations

from decimal import Decimal

import pytest

from praxis.binsim.book import OrderBook
from praxis.core.domain.enums import OrderSide


_BIDS: list[tuple[Decimal, Decimal]] = [
    (Decimal('100.00'), Decimal('1.0')),
    (Decimal('99.50'), Decimal('2.0')),
    (Decimal('99.00'), Decimal('3.0')),
]

_ASKS: list[tuple[Decimal, Decimal]] = [
    (Decimal('101.00'), Decimal('1.0')),
    (Decimal('101.50'), Decimal('2.0')),
    (Decimal('102.00'), Decimal('3.0')),
]

_UID = 1000
_TS = 1_700_000_000_000


def _seeded() -> OrderBook:

    book = OrderBook()
    book.replace(_BIDS, _ASKS, _UID, _TS)

    return book


def test_replace_populates_book_and_metadata() -> None:

    book = _seeded()

    assert book.bids == _BIDS
    assert book.asks == _ASKS
    assert book.last_update_id == _UID
    assert book.ts_ms == _TS


def test_bids_and_asks_properties_return_copies() -> None:

    book = _seeded()
    snapshot = book.bids
    snapshot.append((Decimal('1.0'), Decimal('1.0')))

    assert book.bids == _BIDS


def test_replace_rejects_empty_bids() -> None:

    book = OrderBook()

    with pytest.raises(ValueError, match='bids cannot be empty'):
        book.replace([], _ASKS, _UID, _TS)


def test_replace_rejects_empty_asks() -> None:

    book = OrderBook()

    with pytest.raises(ValueError, match='asks cannot be empty'):
        book.replace(_BIDS, [], _UID, _TS)


@pytest.mark.parametrize(
    'level',
    [
        (Decimal('0'), Decimal('1.0')),
        (Decimal('-1'), Decimal('1.0')),
        (Decimal('100'), Decimal('0')),
        (Decimal('100'), Decimal('-1')),
    ],
)
def test_replace_rejects_non_positive_bid_levels(
    level: tuple[Decimal, Decimal],
) -> None:

    book = OrderBook()

    with pytest.raises(ValueError, match='bid level has non-positive value'):
        book.replace([level], _ASKS, _UID, _TS)


@pytest.mark.parametrize(
    'level',
    [
        (Decimal('0'), Decimal('1.0')),
        (Decimal('-1'), Decimal('1.0')),
        (Decimal('100'), Decimal('0')),
        (Decimal('100'), Decimal('-1')),
    ],
)
def test_replace_rejects_non_positive_ask_levels(
    level: tuple[Decimal, Decimal],
) -> None:

    book = OrderBook()

    with pytest.raises(ValueError, match='ask level has non-positive value'):
        book.replace(_BIDS, [level], _UID, _TS)


def test_replace_rejects_non_descending_bids() -> None:

    book = OrderBook()
    bad_bids = [
        (Decimal('100'), Decimal('1.0')),
        (Decimal('100'), Decimal('1.0')),
    ]

    with pytest.raises(ValueError, match='bids must be strictly descending'):
        book.replace(bad_bids, _ASKS, _UID, _TS)


def test_replace_rejects_ascending_in_bids() -> None:

    book = OrderBook()
    bad_bids = [
        (Decimal('100'), Decimal('1.0')),
        (Decimal('101'), Decimal('1.0')),
    ]

    with pytest.raises(ValueError, match='bids must be strictly descending'):
        book.replace(bad_bids, _ASKS, _UID, _TS)


def test_replace_rejects_non_ascending_asks() -> None:

    book = OrderBook()
    bad_asks = [
        (Decimal('101'), Decimal('1.0')),
        (Decimal('101'), Decimal('1.0')),
    ]

    with pytest.raises(ValueError, match='asks must be strictly ascending'):
        book.replace(_BIDS, bad_asks, _UID, _TS)


def test_replace_rejects_descending_in_asks() -> None:

    book = OrderBook()
    bad_asks = [
        (Decimal('101'), Decimal('1.0')),
        (Decimal('100'), Decimal('1.0')),
    ]

    with pytest.raises(ValueError, match='asks must be strictly ascending'):
        book.replace(_BIDS, bad_asks, _UID, _TS)


def test_replace_rejects_crossed_book() -> None:

    book = OrderBook()
    crossed_bids = [(Decimal('102'), Decimal('1.0'))]
    crossed_asks = [(Decimal('101'), Decimal('1.0'))]

    with pytest.raises(ValueError, match='book is crossed'):
        book.replace(crossed_bids, crossed_asks, _UID, _TS)


def test_replace_rejects_equal_best_bid_and_ask() -> None:

    book = OrderBook()
    bids = [(Decimal('100'), Decimal('1.0'))]
    asks = [(Decimal('100'), Decimal('1.0'))]

    with pytest.raises(ValueError, match='book is crossed'):
        book.replace(bids, asks, _UID, _TS)


def test_replace_rejects_backwards_update_id() -> None:

    book = _seeded()

    with pytest.raises(ValueError, match='last_update_id moved backwards'):
        book.replace(_BIDS, _ASKS, _UID - 1, _TS)


def test_replace_accepts_equal_update_id() -> None:

    book = _seeded()
    book.replace(_BIDS, _ASKS, _UID, _TS)


def test_consume_buy_walks_asks_ascending_first_level() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.BUY, Decimal('0.5'))

    assert fills == [(Decimal('101.00'), Decimal('0.5'))]


def test_consume_buy_walks_asks_into_second_level() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.BUY, Decimal('1.5'))

    assert fills == [
        (Decimal('101.00'), Decimal('1.0')),
        (Decimal('101.50'), Decimal('0.5')),
    ]


def test_consume_buy_walks_all_three_ask_levels() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.BUY, Decimal('4.5'))

    assert fills == [
        (Decimal('101.00'), Decimal('1.0')),
        (Decimal('101.50'), Decimal('2.0')),
        (Decimal('102.00'), Decimal('1.5')),
    ]


def test_consume_sell_walks_bids_descending_first_level() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.SELL, Decimal('0.5'))

    assert fills == [(Decimal('100.00'), Decimal('0.5'))]


def test_consume_sell_walks_bids_into_second_level() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.SELL, Decimal('1.5'))

    assert fills == [
        (Decimal('100.00'), Decimal('1.0')),
        (Decimal('99.50'), Decimal('0.5')),
    ]


def test_consume_buy_returns_partial_when_asks_exhausted() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.BUY, Decimal('100'))

    assert fills == [
        (Decimal('101.00'), Decimal('1.0')),
        (Decimal('101.50'), Decimal('2.0')),
        (Decimal('102.00'), Decimal('3.0')),
    ]

    summed = sum((qty for _, qty in fills), Decimal('0'))
    assert summed == Decimal('6')


def test_consume_sell_returns_partial_when_bids_exhausted() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.SELL, Decimal('100'))

    assert fills == [
        (Decimal('100.00'), Decimal('1.0')),
        (Decimal('99.50'), Decimal('2.0')),
        (Decimal('99.00'), Decimal('3.0')),
    ]


def test_consume_exact_level_qty_does_not_emit_zero_take() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.BUY, Decimal('1.0'))

    assert fills == [(Decimal('101.00'), Decimal('1.0'))]


def test_consume_raises_on_empty_book_buy() -> None:

    book = OrderBook()

    with pytest.raises(RuntimeError, match='order book is empty'):
        book.consume_qty_for_market_order(OrderSide.BUY, Decimal('1'))


def test_consume_raises_on_empty_book_sell() -> None:

    book = OrderBook()

    with pytest.raises(RuntimeError, match='order book is empty'):
        book.consume_qty_for_market_order(OrderSide.SELL, Decimal('1'))


@pytest.mark.parametrize('qty', [Decimal('0'), Decimal('-1'), Decimal('-0.0001')])
def test_consume_raises_on_non_positive_qty(qty: Decimal) -> None:

    book = _seeded()

    with pytest.raises(ValueError, match='qty must be positive'):
        book.consume_qty_for_market_order(OrderSide.BUY, qty)


def test_vwap_matches_walked_levels() -> None:

    book = _seeded()
    fills = book.consume_qty_for_market_order(OrderSide.BUY, Decimal('2.5'))

    total_qty = sum((qty for _, qty in fills), Decimal('0'))
    total_notional = sum((price * qty for price, qty in fills), Decimal('0'))
    vwap = total_notional / total_qty
    expected = (
        Decimal('101.00') * Decimal('1.0')
        + Decimal('101.50') * Decimal('1.5')
    ) / Decimal('2.5')

    assert vwap == expected
