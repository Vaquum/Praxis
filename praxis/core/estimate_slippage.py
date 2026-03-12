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

__all__ = ['SlippageEstimate', 'estimate_slippage']

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


def estimate_slippage(
    book: OrderBookSnapshot,
    qty: Decimal,
    side: OrderSide,
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

    Returns:
        SlippageEstimate | None: Estimate with mid-price, simulated VWAP,
            and slippage in bps. None when the book lacks either a bid or
            an ask (mid-price cannot be computed).
    '''

    if not book.bids or not book.asks:
        return None

    mid_price = (book.bids[0].price + book.asks[0].price) / _TWO

    if mid_price == _ZERO:
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
            'book depth insufficient: needed=%s available=%s side=%s',
            qty,
            filled,
            side.value,
        )

    simulated_vwap = cost / filled
    slippage_bps = (simulated_vwap - mid_price) / mid_price * _BPS_MULTIPLIER

    return SlippageEstimate(
        mid_price=mid_price,
        simulated_vwap=simulated_vwap,
        slippage_estimate_bps=slippage_bps,
    )
