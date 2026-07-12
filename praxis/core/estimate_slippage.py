'''
Walk-the-book slippage estimation for pre-submission order analysis.

Simulate executing a given quantity against order book depth to compute
expected VWAP and slippage in basis points relative to the mid-price.
'''

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from praxis.core.domain.enums import OrderSide
from praxis.infrastructure.venue_adapter import OrderBookSnapshot

__all__ = ['SlippageEstimate', 'estimate_slippage', 'estimate_slippage_for_quote']

_log = logging.getLogger(__name__)

_ZERO = Decimal('0')
_TWO = Decimal('2')
_BPS_MULTIPLIER = Decimal('10000')


@dataclass(frozen=True)
class SlippageEstimate:
    '''
    Pre-submission slippage estimate from walking the order book.

    Args:
        mid_price (Decimal): Mid-price at time of estimate, (best_bid + best_ask) / 2.
        simulated_vwap (Decimal): Volume-weighted average price from walking the book.
        slippage_estimate_bps (Decimal): Expected slippage in basis points,
            (simulated_vwap - mid_price) / mid_price * 10_000.
    '''

    mid_price: Decimal
    simulated_vwap: Decimal
    slippage_estimate_bps: Decimal


def _mid_price(book: OrderBookSnapshot) -> Decimal | None:
    '''Return the book mid-price, or `None` for an empty, non-positive, or crossed book.

    Degrades to `None` on a bad book (a side is empty, the best bid is not
    positive, or the best ask is below the best bid) rather than returning
    a negative or misleading mid into the slippage estimate and guard,
    consistent with `book_mid_price` and `build_price_snapshot`.
    '''

    if not book.bids or not book.asks:
        return None

    best_bid = book.bids[0].price
    best_ask = book.asks[0].price

    if best_bid <= _ZERO or best_ask < best_bid:
        return None

    return (best_bid + best_ask) / _TWO


def _slippage_from_fill(mid_price: Decimal, cost: Decimal, filled: Decimal) -> SlippageEstimate:
    '''Build a `SlippageEstimate` from the walked cost and filled base quantity.'''

    simulated_vwap = cost / filled
    slippage_bps = (simulated_vwap - mid_price) / mid_price * _BPS_MULTIPLIER

    return SlippageEstimate(
        mid_price=mid_price,
        simulated_vwap=simulated_vwap,
        slippage_estimate_bps=slippage_bps,
    )


def estimate_slippage(
    book: OrderBookSnapshot,
    qty: Decimal,
    side: OrderSide,
    symbol: str | None = None,
) -> SlippageEstimate | None:
    '''
    Compute expected slippage by walking the order book.

    Walk ask levels for BUY orders, bid levels for SELL orders.
    Accumulate price * qty per level until the target quantity is
    reached or book depth is exhausted.

    Args:
        book (OrderBookSnapshot): Current order book snapshot.
        qty (Decimal): Target quantity to simulate.
        side (OrderSide): Order side determining which book side to walk.
        symbol (str | None): Symbol used for warning-log correlation.

    Returns:
        SlippageEstimate | None: Estimate with mid-price, simulated VWAP,
            and slippage in bps. When available depth is insufficient to
            fill qty, the estimate still returns and uses only filled
            quantity (with a warning log). None when the book lacks either
            a bid or an ask (mid-price cannot be computed).
    '''

    mid_price = _mid_price(book)

    if mid_price is None:
        return None

    levels = book.asks if side == OrderSide.BUY else book.bids
    remaining = qty
    cost = _ZERO

    for level in levels:
        if remaining <= _ZERO:
            break
        fill_qty = min(remaining, level.qty)
        cost += fill_qty * level.price
        remaining -= fill_qty

    filled = qty - remaining

    if filled == _ZERO:
        return None

    if remaining > _ZERO:
        _log.warning(
            'book depth insufficient: symbol=%s needed=%s available=%s side=%s',
            symbol,
            qty,
            filled,
            side.value,
        )

    return _slippage_from_fill(mid_price, cost, filled)


def estimate_slippage_for_quote(
    book: OrderBookSnapshot,
    quote_qty: Decimal,
    side: OrderSide,
    symbol: str | None = None,
) -> SlippageEstimate | None:
    '''
    Compute expected slippage for a quote-denominated order by walking the book.

    Walk ask levels for BUY orders, bid levels for SELL orders, consuming
    the quote amount level by level until it is exhausted or book depth
    runs out. Used for quote-native MARKET orders that have no base target.

    Args:
        book (OrderBookSnapshot): Current order book snapshot.
        quote_qty (Decimal): Quote-asset amount — the spend for a BUY, the
            proceeds target for a SELL.
        side (OrderSide): Order side determining which book side to walk.
        symbol (str | None): Symbol used for warning-log correlation.

    Returns:
        SlippageEstimate | None: Estimate with mid-price, simulated VWAP,
            and slippage in bps. None when the book lacks a bid or an ask,
            or when no base could be filled.
    '''

    mid_price = _mid_price(book)

    if mid_price is None:
        return None

    levels = book.asks if side == OrderSide.BUY else book.bids
    remaining_quote = quote_qty
    filled_base = _ZERO

    for level in levels:
        if remaining_quote <= _ZERO:
            break
        spend = min(remaining_quote, level.qty * level.price)
        filled_base += spend / level.price
        remaining_quote -= spend

    if filled_base == _ZERO:
        return None

    if remaining_quote > _ZERO:
        _log.warning(
            'book depth insufficient for quote amount: symbol=%s needed_quote=%s side=%s',
            symbol,
            quote_qty,
            side.value,
        )

    return _slippage_from_fill(mid_price, quote_qty - remaining_quote, filled_base)
