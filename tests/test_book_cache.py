'''Tests for the order book cache, price-snapshot builder, and poller.'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.infrastructure.book_cache import BookCache, build_price_snapshot
from praxis.infrastructure.book_poller import BookPoller
from praxis.infrastructure.venue_adapter import OrderBookLevel, OrderBookSnapshot

_NOW = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
_FETCHED = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _book(bid: str, ask: str) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal(bid), qty=Decimal('1')),),
        asks=(OrderBookLevel(price=Decimal(ask), qty=Decimal('1')),),
        last_update_id=1,
    )


def test_build_price_snapshot_returns_none_when_empty():
    assert build_price_snapshot(BookCache(), 'BTCUSDT', _NOW) is None


def test_build_price_snapshot_computes_spread_and_timestamps():
    cache = BookCache()
    cache.update('BTCUSDT', _book('100', '101'), _FETCHED)

    snapshot = build_price_snapshot(cache, 'BTCUSDT', _NOW)

    assert snapshot is not None
    assert snapshot.spread_bps == (Decimal('1') / Decimal('100.5')) * Decimal('10000')
    assert snapshot.now_ms == int(_NOW.timestamp() * 1000)
    assert snapshot.book_timestamp_ms == int(_FETCHED.timestamp() * 1000)


def test_build_price_snapshot_none_on_crossed_book():
    cache = BookCache()
    cache.update('BTCUSDT', _book('101', '100'), _FETCHED)

    assert build_price_snapshot(cache, 'BTCUSDT', _NOW) is None


def test_build_price_snapshot_none_on_empty_levels():
    cache = BookCache()
    cache.update('BTCUSDT', OrderBookSnapshot(bids=(), asks=(), last_update_id=1), _FETCHED)

    assert build_price_snapshot(cache, 'BTCUSDT', _NOW) is None


def test_cache_returns_latest_book():
    cache = BookCache()
    cache.update('BTCUSDT', _book('100', '101'), _FETCHED)
    cache.update('BTCUSDT', _book('200', '201'), _FETCHED)

    cached = cache.get('BTCUSDT')

    assert cached is not None
    assert cached.snapshot.bids[0].price == Decimal('200')


@pytest.mark.asyncio
async def test_poller_tick_updates_cache():
    cache = BookCache()
    book = _book('100', '101')

    async def fetch() -> OrderBookSnapshot:
        return book

    poller = BookPoller('BTCUSDT', fetch, cache, lambda: _FETCHED, interval_seconds=1.0)
    await poller.tick_once()

    cached = cache.get('BTCUSDT')
    assert cached is not None
    assert cached.snapshot is book
    assert cached.fetched_at == _FETCHED


def test_poller_rejects_bad_interval():
    with pytest.raises(ValueError, match='interval_seconds must be positive'):
        BookPoller(
            'BTCUSDT', _never_fetch, BookCache(), lambda: _FETCHED, interval_seconds=0,
        )


async def _never_fetch() -> OrderBookSnapshot:
    raise AssertionError('fetch should not be called')
