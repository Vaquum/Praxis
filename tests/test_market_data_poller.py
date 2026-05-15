'''Tests for MarketDataPoller staleness adapter over MainCache.

Pre-rewire MarketDataPoller ran per-kline_size poller threads with
its own cache; those tests moved to test_market_data_cache.py
(MainCache + CacheScheduler). What survives here is the thin
adapter contract: get_market_data delegates to the cache and
raises StaleMarketDataError when the latest bar is too old;
is_stale is the non-raising counterpart.
'''

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from praxis.market_data_cache import MainCache
from praxis.market_data_poller import MarketDataPoller, StaleMarketDataError
from tests.conftest import make_canonical_klines as _make_klines


_BASE_TS = datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def cache_paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / 'btcusdt_1m.parquet', tmp_path / 'main_cache_state.json'


@pytest.fixture
def populated_cache(cache_paths: tuple[Path, Path]) -> MainCache:
    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines(_BASE_TS, count=20)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = snapshot
        cache.refresh_from_limen()

    return cache


def test_init_rejects_non_positive_max_age_kline_size() -> None:
    cache = MagicMock()

    with pytest.raises(ValueError, match='must be positive'):
        MarketDataPoller(cache, max_age_overrides={0: 60.0})


def test_init_rejects_non_positive_max_age_value() -> None:
    cache = MagicMock()

    with pytest.raises(ValueError, match=r'must be > 0\.0'):
        MarketDataPoller(cache, max_age_overrides={300: 0.0})


def test_get_market_data_delegates_to_cache(populated_cache: MainCache) -> None:
    '''get_market_data forwards the kline_size to MainCache and
    returns whatever MainCache returns when the cache is fresh.
    '''

    poller = MarketDataPoller(populated_cache)
    fixed_now = _BASE_TS + timedelta(minutes=20)

    with patch(
        'praxis.market_data_poller.datetime',
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now
        result = poller.get_market_data(60)

    assert result.height == populated_cache.frame.height
    assert result['datetime'].to_list() == populated_cache.frame['datetime'].to_list()


def test_get_market_data_aggregates_via_cache(populated_cache: MainCache) -> None:
    '''Requesting 5m delegates to cache.get_market_data(300) which
    aggregates 1-min bars upward; adapter only adds the staleness
    check, it does not aggregate itself.
    '''

    poller = MarketDataPoller(populated_cache)
    fixed_now = _BASE_TS + timedelta(minutes=20)

    with patch(
        'praxis.market_data_poller.datetime',
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now
        result = poller.get_market_data(300)

    assert result.height == 4


def test_get_market_data_raises_when_stale(populated_cache: MainCache) -> None:
    '''When the latest cache bar is older than `2 * kline_size`,
    get_market_data raises StaleMarketDataError instead of
    returning the data.
    '''

    poller = MarketDataPoller(populated_cache)
    last_bar = populated_cache.frame['datetime'].max()
    fixed_now = last_bar + timedelta(seconds=601)

    with patch(
        'praxis.market_data_poller.datetime',
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now

        with pytest.raises(StaleMarketDataError) as exc_info:
            poller.get_market_data(300)

    err = exc_info.value
    assert err.kline_size == 300
    assert err.fetched_at == last_bar
    assert err.max_age_seconds == 600
    assert err.age_seconds > 600


def test_get_market_data_empty_cache_does_not_raise() -> None:
    '''An empty cache (never populated) returns the empty frame
    rather than raising — pre-rewire semantics for the
    no-data-yet case.
    '''

    cache = MagicMock(spec=MainCache)
    cache.frame = pl.DataFrame()
    cache.snapshot.return_value = (pl.DataFrame(), None)

    poller = MarketDataPoller(cache)
    result = poller.get_market_data(300)

    assert result.is_empty()


def test_get_market_data_respects_max_age_override(
    populated_cache: MainCache,
) -> None:
    '''A per-kline_size max-age override replaces the
    `2 * kline_size` default.
    '''

    poller = MarketDataPoller(populated_cache, max_age_overrides={300: 60.0})
    last_bar = populated_cache.frame['datetime'].max()
    fixed_now = last_bar + timedelta(seconds=61)

    with patch(
        'praxis.market_data_poller.datetime',
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now

        with pytest.raises(StaleMarketDataError) as exc_info:
            poller.get_market_data(300)

    assert exc_info.value.max_age_seconds == 60.0


def test_get_market_data_uses_single_snapshot_call() -> None:
    '''Pin: `get_market_data` calls `cache.snapshot(kline_size)`
    exactly once and never touches `cache.frame` or
    `cache.get_market_data` separately. Without this the staleness
    decision and the returned data could be derived from different
    `_frame` references when a refresh thread swaps the frame
    between the two reads.
    '''

    cache = MagicMock(spec=MainCache)
    fresh_frame = _make_klines(_BASE_TS, count=5)
    cache.snapshot.return_value = (
        fresh_frame,
        _BASE_TS + timedelta(minutes=4),
    )
    poller = MarketDataPoller(cache)

    fixed_now = _BASE_TS + timedelta(minutes=4, seconds=30)
    with patch('praxis.market_data_poller.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_now
        result = poller.get_market_data(60)

    assert result is fresh_frame
    cache.snapshot.assert_called_once_with(60)
    cache.get_market_data.assert_not_called()


def test_is_stale_returns_true_when_empty() -> None:
    '''Non-raising counterpart: an empty cache reports stale.'''

    cache = MagicMock(spec=MainCache)
    cache.frame = pl.DataFrame()
    cache.snapshot.return_value = (pl.DataFrame(), None)
    poller = MarketDataPoller(cache)

    assert poller.is_stale(300) is True


def test_is_stale_returns_true_when_old(populated_cache: MainCache) -> None:
    poller = MarketDataPoller(populated_cache)
    last_bar = populated_cache.frame['datetime'].max()
    fixed_now = last_bar + timedelta(seconds=601)

    with patch(
        'praxis.market_data_poller.datetime',
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now
        assert poller.is_stale(300) is True


def test_is_stale_returns_false_when_fresh(populated_cache: MainCache) -> None:
    poller = MarketDataPoller(populated_cache)
    last_bar = populated_cache.frame['datetime'].max()
    fixed_now = last_bar + timedelta(seconds=300)

    with patch(
        'praxis.market_data_poller.datetime',
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now
        assert poller.is_stale(300) is False
