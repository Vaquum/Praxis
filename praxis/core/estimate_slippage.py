'''
Walk-the-book slippage estimation for pre-submission order analysis.

Simulate executing a given quantity against order book depth to compute
expected VWAP and slippage in basis points relative to the mid-price.
'''

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

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

    if not book.bids or not book.asks:
        return None

    mid_price = (book.bids[0].price + book.asks[0].price) / _TWO

    if mid_price == _ZERO:
        return None

    levels = book.asks if side == OrderSide.BUY else book.bids

    prices = np.array([float(level.price) for level in levels], dtype=np.float64)
    qtys = np.array([float(level.qty) for level in levels], dtype=np.float64)
    target = float(qty)

    cumulative = np.cumsum(qtys)
    idx = np.searchsorted(cumulative, target, side='left')

    if idx == 0:
        fill_qty = min(target, qtys[0])
        cost = fill_qty * prices[0]
        filled = fill_qty
    elif idx >= len(qtys):
        cost = float(np.dot(prices, qtys))
        filled = cumulative[-1]
    else:
        full_cost = float(np.dot(prices[:idx], qtys[:idx]))
        partial_qty = target - cumulative[idx - 1]
        cost = full_cost + partial_qty * prices[idx]
        filled = target

    if filled == 0:
        return None

    if filled < target:
        _log.warning(
            'book depth insufficient: symbol=%s needed=%s available=%s side=%s',
            symbol,
            qty,
            Decimal(str(filled)),
            side.value,
        )

    simulated_vwap = Decimal(str(cost / filled))
    slippage_bps = (simulated_vwap - mid_price) / mid_price * _BPS_MULTIPLIER

    return SlippageEstimate(
        mid_price=mid_price,
        simulated_vwap=simulated_vwap,
        slippage_estimate_bps=slippage_bps,
    )
