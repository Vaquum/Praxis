'''Cache of the latest order book per symbol for pre-trade price checks.

A poller writes the most recent `OrderBookSnapshot` per symbol; the
validation pipeline's price-snapshot provider reads it to derive spread
and staleness without a blocking venue call on the hot path.
'''

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from nexus.core.validator import PriceCheckSnapshot

from praxis.infrastructure.venue_adapter import OrderBookSnapshot

__all__ = ['BookCache', 'CachedBook', 'book_mid_price', 'build_price_snapshot']

_ZERO = Decimal('0')
_TWO = Decimal('2')
_BPS = Decimal('10000')
_MS_PER_SECOND = 1000
_ORIGO_MID = 'origo_mid'


@dataclass(frozen=True)
class CachedBook:
    snapshot: OrderBookSnapshot
    fetched_at: datetime


class BookCache:
    '''The most recent order book per symbol, written by the poller and read during validation.'''

    def __init__(self) -> None:
        self._books: dict[str, CachedBook] = {}
        self._lock = threading.Lock()

    def update(self, symbol: str, snapshot: OrderBookSnapshot, fetched_at: datetime) -> None:
        '''Store the latest snapshot for `symbol` with its fetch time.'''

        with self._lock:
            self._books[symbol] = CachedBook(snapshot=snapshot, fetched_at=fetched_at)

    def get(self, symbol: str) -> CachedBook | None:
        '''Return the cached book for `symbol`, or `None` when absent.'''

        with self._lock:
            return self._books.get(symbol)


def book_mid_price(cache: BookCache, symbol: str) -> Decimal | None:
    '''Return the cached top-of-book mid for `symbol`, or `None`.

    `None` when no book is cached, the book is empty, or it is crossed, so
    a caller converting a quote notional to a base size degrades safely
    rather than dividing by a bad price.

    Args:
        cache: Book cache the poller keeps current.
        symbol: Symbol to read.
    '''

    cached = cache.get(symbol)

    if cached is None:
        return None

    snapshot = cached.snapshot

    if not snapshot.bids or not snapshot.asks:
        return None

    best_bid = snapshot.bids[0].price
    best_ask = snapshot.asks[0].price

    if best_bid <= _ZERO or best_ask < best_bid:
        return None

    return (best_bid + best_ask) / _TWO


def build_price_snapshot(
    cache: BookCache, symbol: str, now: datetime,
    reference_price: Decimal | None = None,
) -> PriceCheckSnapshot | None:
    '''Build a `PriceCheckSnapshot` from the cached book, or `None`.

    Returns `None` when no book is cached or the book is empty or crossed,
    so a configured price limit rejects rather than trades on a bad book.

    When `reference_price` is supplied, the snapshot also carries
    `deviation_bps` — the absolute deviation of the book mid from the
    reference price — and `reference_price_source` set to `'origo_mid'`,
    so the price stage's per-strategy deviation collar can evaluate.

    Args:
        cache: Book cache the poller keeps current.
        symbol: Symbol to read.
        now: Current time, for the staleness reference.
        reference_price: Optional strategy reference price for the
            deviation collar; `None` or a non-positive value leaves
            `deviation_bps` unset.
    '''

    cached = cache.get(symbol)

    if cached is None:
        return None

    snapshot = cached.snapshot

    if not snapshot.bids or not snapshot.asks:
        return None

    best_bid = snapshot.bids[0].price
    best_ask = snapshot.asks[0].price

    if best_bid <= _ZERO or best_ask < best_bid:
        return None

    mid = (best_bid + best_ask) / _TWO
    spread_bps = (best_ask - best_bid) / mid * _BPS

    deviation_bps: Decimal | None = None
    reference_price_source: str | None = None

    if reference_price is not None and reference_price > _ZERO:
        deviation_bps = abs(mid - reference_price) / reference_price * _BPS
        reference_price_source = _ORIGO_MID

    return PriceCheckSnapshot(
        now_ms=int(now.timestamp() * _MS_PER_SECOND),
        book_timestamp_ms=int(cached.fetched_at.timestamp() * _MS_PER_SECOND),
        spread_bps=spread_bps,
        deviation_bps=deviation_bps,
        reference_price_source=reference_price_source,
    )
