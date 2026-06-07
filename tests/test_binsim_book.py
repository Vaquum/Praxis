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


@pytest.mark.parametrize(
    'bad_level',
    [
        (Decimal('NaN'), Decimal('1.0')),
        (Decimal('Infinity'), Decimal('1.0')),
        (Decimal('100'), Decimal('NaN')),
        (Decimal('100'), Decimal('Infinity')),
    ],
)
def test_replace_rejects_non_finite_bid_levels(bad_level: tuple[Decimal, Decimal]) -> None:
    book = OrderBook()

    with pytest.raises(ValueError, match='bid level must be finite'):
        book.replace([bad_level], _ASKS, _UID, _TS)


@pytest.mark.parametrize(
    'bad_level',
    [
        (Decimal('NaN'), Decimal('1.0')),
        (Decimal('Infinity'), Decimal('1.0')),
        (Decimal('100'), Decimal('NaN')),
    ],
)
def test_replace_rejects_non_finite_ask_levels(bad_level: tuple[Decimal, Decimal]) -> None:
    book = OrderBook()

    with pytest.raises(ValueError, match='ask level must be finite'):
        book.replace(_BIDS, [bad_level], _UID, _TS)


@pytest.mark.parametrize('bad_qty', [Decimal('NaN'), Decimal('Infinity'), Decimal('-Infinity')])
def test_consume_raises_on_non_finite_qty(bad_qty: Decimal) -> None:
    book = _seeded()

    with pytest.raises(ValueError, match='qty must be finite'):
        book.consume_qty_for_market_order(OrderSide.BUY, bad_qty)


def test_consume_quote_for_market_buy_full_level() -> None:
    book = _seeded()

    walk, remaining = book.consume_quote_for_market_buy(Decimal('101.00'))

    assert walk == [(Decimal('101.00'), Decimal('1.0'))]
    assert remaining == Decimal('0')


def test_consume_quote_for_market_buy_partial_takes_last_level() -> None:
    book = _seeded()

    walk, remaining = book.consume_quote_for_market_buy(Decimal('152.25'))

    assert walk[0] == (Decimal('101.00'), Decimal('1.0'))
    assert walk[1][0] == Decimal('101.50')
    remaining_quote = Decimal('152.25') - Decimal('101.00')
    assert walk[1][1] == remaining_quote / Decimal('101.50')
    assert remaining == Decimal('0')


def test_consume_quote_for_market_buy_sums_to_quote_qty() -> None:
    book = _seeded()
    quote_qty = Decimal('250.00')

    walk, remaining = book.consume_quote_for_market_buy(quote_qty)

    consumed_quote = sum((p * q for p, q in walk), Decimal('0'))
    assert abs(consumed_quote - quote_qty) < Decimal('1E-20')
    assert remaining == Decimal('0')


def test_consume_quote_for_market_buy_remaining_zero_after_full_walk() -> None:
    '''ULP-rounding regression: when a quote-walk fully exhausts the
    requested budget via a partial-take, `remaining_quote` is exactly
    `Decimal('0')` even though `sum(price * fill_qty)` is one ULP
    short of the budget. Callers must read `remaining_quote`, not the
    re-derived sum.

    Uses a non-clean price (`50123.45`) so `quote_qty / price` is a
    repeating decimal that gets truncated to the 28-digit context;
    `price * truncated_qty` then loses the ULP. The seeded book's
    `101.00` prices divide cleanly into common budgets and do not
    trigger the loss.
    '''

    book = OrderBook()
    asks = [
        (Decimal('50123.45'), Decimal('0.5')),
        (Decimal('50130.77'), Decimal('1.3')),
    ]
    book.replace(_BIDS, asks, _UID, _TS)
    quote_qty = Decimal('0.001')

    walk, remaining = book.consume_quote_for_market_buy(quote_qty)

    assert remaining == Decimal('0')
    consumed_quote = sum((p * q for p, q in walk), Decimal('0'))
    assert consumed_quote < quote_qty
    assert quote_qty - consumed_quote < Decimal('1E-25')


def test_consume_quote_for_market_buy_partial_when_book_exhausted() -> None:
    book = _seeded()

    walk, remaining = book.consume_quote_for_market_buy(Decimal('100000'))

    consumed_quote = sum((p * q for p, q in walk), Decimal('0'))
    assert consumed_quote == Decimal('101.00') + Decimal('203.00') + Decimal('306.00')
    assert consumed_quote < Decimal('100000')
    assert remaining == Decimal('100000') - consumed_quote
    assert remaining > 0


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_consume_quote_for_market_buy_rejects_non_positive(bad: Decimal) -> None:
    book = _seeded()

    with pytest.raises(ValueError, match='quote_qty must be positive'):
        book.consume_quote_for_market_buy(bad)


@pytest.mark.parametrize('bad', [Decimal('NaN'), Decimal('Infinity'), Decimal('-Infinity')])
def test_consume_quote_for_market_buy_rejects_non_finite(bad: Decimal) -> None:
    book = _seeded()

    with pytest.raises(ValueError, match='quote_qty must be finite'):
        book.consume_quote_for_market_buy(bad)


def test_consume_quote_for_market_buy_raises_on_empty_asks() -> None:
    book = OrderBook()

    with pytest.raises(RuntimeError, match='order book is empty'):
        book.consume_quote_for_market_buy(Decimal('100'))


def test_consume_quote_for_market_buy_partial_take_never_overspends() -> None:
    '''Decimal HALF_EVEN division can round up, making the rounded
    quotient slightly larger than the exact value and breaking the
    `quoteOrderQty` spend-cap invariant. The fix uses a `ROUND_DOWN`
    local context so the partial-take's `take_base` is always at most
    the exact quotient — guaranteeing `price * take_base <=
    remaining_quote` and therefore `consumed_quote <= quote_qty`.

    Pair `(847.4945188530934, 603.7264276408597)` is one of the
    cases empirically found to overspend under the default
    HALF_EVEN rounding. Asks are arranged so the second level
    triggers the partial take with this `(remaining_quote, price)`.
    '''

    book = OrderBook()
    bids = [
        (Decimal('600'), Decimal('1')),
    ]
    asks = [
        (Decimal('601'), Decimal('1')),
        (Decimal('603.7264276408597'), Decimal('10')),
    ]
    book.replace(bids, asks, _UID, _TS)
    remaining_at_partial_take = Decimal('847.4945188530934')
    quote_qty = Decimal('601') + remaining_at_partial_take

    walk, remaining = book.consume_quote_for_market_buy(quote_qty)

    partial_price, partial_qty = walk[-1]
    assert partial_price == Decimal('603.7264276408597')
    assert partial_price * partial_qty <= remaining_at_partial_take
    assert remaining == Decimal('0')
