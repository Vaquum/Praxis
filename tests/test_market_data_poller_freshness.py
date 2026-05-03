'''Tests for MarketDataPoller cache freshness (MAJOR-005).

Pre-fix `_fetch` swallowed exceptions and `get_market_data` returned
the previous DataFrame indefinitely. Post-fix every cache entry is
stamped with `fetched_at`; reads beyond `max_age_seconds` raise
`StaleMarketDataError`. The launcher's `fallback_price_provider`
swallows the exception per kline_size and falls back to None so the
validator's PRICE stage rejects ENTERs with a clear reason.
'''

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from praxis.market_data_poller import MarketDataPoller, StaleMarketDataError


_KLINE_SIZE = 60


def _seed_cache(
    poller: MarketDataPoller,
    kline_size: int,
    fetched_at: datetime,
    df: pl.DataFrame | None = None,
) -> None:
    '''Inject a cache entry with a chosen `fetched_at` timestamp.'''

    if df is None:
        df = pl.DataFrame({'close': [50000.0]})
    with poller._lock:
        poller._data[kline_size] = df
        poller._fetched_at[kline_size] = fetched_at


class TestGetMarketDataFreshness:

    def test_fresh_cache_returns_dataframe(self) -> None:
        poller = MarketDataPoller()
        now = datetime.now(tz=UTC)
        _seed_cache(poller, _KLINE_SIZE, fetched_at=now)

        df = poller.get_market_data(_KLINE_SIZE)

        assert df.height == 1

    def test_no_cache_returns_empty_dataframe(self) -> None:
        poller = MarketDataPoller()

        df = poller.get_market_data(_KLINE_SIZE)

        assert df.is_empty()

    def test_stale_cache_raises(self) -> None:
        poller = MarketDataPoller()
        stale_ts = datetime.now(tz=UTC) - timedelta(seconds=200)
        _seed_cache(poller, _KLINE_SIZE, fetched_at=stale_ts)

        with pytest.raises(StaleMarketDataError) as exc_info:
            poller.get_market_data(_KLINE_SIZE)

        assert exc_info.value.kline_size == _KLINE_SIZE
        assert exc_info.value.max_age_seconds == 120.0
        assert exc_info.value.age_seconds > 120.0

    def test_max_age_override_honoured(self) -> None:
        '''Custom per-kline max_age_seconds overrides the 2 * kline_size default.'''

        poller = MarketDataPoller(max_age_seconds={_KLINE_SIZE: 30.0})
        ts = datetime.now(tz=UTC) - timedelta(seconds=60)
        _seed_cache(poller, _KLINE_SIZE, fetched_at=ts)

        with pytest.raises(StaleMarketDataError) as exc_info:
            poller.get_market_data(_KLINE_SIZE)

        assert exc_info.value.max_age_seconds == 30.0

    def test_is_stale_returns_true_for_stale_cache(self) -> None:
        poller = MarketDataPoller()
        stale_ts = datetime.now(tz=UTC) - timedelta(seconds=200)
        _seed_cache(poller, _KLINE_SIZE, fetched_at=stale_ts)

        assert poller.is_stale(_KLINE_SIZE) is True

    def test_is_stale_returns_false_for_fresh_cache(self) -> None:
        poller = MarketDataPoller()
        _seed_cache(poller, _KLINE_SIZE, fetched_at=datetime.now(tz=UTC))

        assert poller.is_stale(_KLINE_SIZE) is False

    def test_is_stale_returns_true_when_no_cache(self) -> None:
        poller = MarketDataPoller()

        assert poller.is_stale(_KLINE_SIZE) is True

    def test_max_age_overrides_reject_zero_value(self) -> None:
        '''PR #87 review: a misconfigured `{60: 0}` would make every read
        immediately stale. Validate at construction.'''

        with pytest.raises(ValueError, match=r'must be > 0\.0'):
            MarketDataPoller(max_age_seconds={_KLINE_SIZE: 0.0})

    def test_max_age_overrides_reject_negative_value(self) -> None:
        with pytest.raises(ValueError, match=r'must be > 0\.0'):
            MarketDataPoller(max_age_seconds={_KLINE_SIZE: -1.0})

    def test_max_age_overrides_reject_non_positive_kline_size(self) -> None:
        with pytest.raises(ValueError, match='must be positive'):
            MarketDataPoller(max_age_seconds={0: 30.0})

    def test_fetch_skips_cache_write_when_stop_event_set(self) -> None:
        '''PR #87 review: a fetch in flight when `remove_kline_size`
        sets `stop_event` (and the join times out) must not write to
        the cache and resurrect a removed kline_size. `_fetch` checks
        `stop_event.is_set()` under the lock and returns without
        mutating `_data` / `_fetched_at`.
        '''

        import threading
        from unittest.mock import patch

        poller = MarketDataPoller()
        stop_event = threading.Event()
        stop_event.set()

        fake_pd_df = pl.DataFrame({'close': [50000.0]}).to_pandas()
        with patch(
            'praxis.market_data_poller.get_spot_klines',
            return_value=fake_pd_df,
        ):
            poller._fetch(_KLINE_SIZE, client=None, stop_event=stop_event)

        assert _KLINE_SIZE not in poller._data
        assert _KLINE_SIZE not in poller._fetched_at

    def test_fetch_writes_cache_when_stop_event_not_set(self) -> None:
        '''Inverse case: when `stop_event` is clear the fetch path
        writes the new DataFrame and `fetched_at` stamp as before.
        '''

        import threading
        from unittest.mock import patch

        poller = MarketDataPoller()
        stop_event = threading.Event()

        fake_pd_df = pl.DataFrame({'close': [50000.0]}).to_pandas()
        with patch(
            'praxis.market_data_poller.get_spot_klines',
            return_value=fake_pd_df,
        ):
            poller._fetch(_KLINE_SIZE, client=None, stop_event=stop_event)

        assert _KLINE_SIZE in poller._data
        assert poller._data[_KLINE_SIZE].height == 1
        assert _KLINE_SIZE in poller._fetched_at


class TestFallbackPriceProviderStaleGuard:
    '''The launcher's `fallback_price_provider` calls
    `_last_close_from_poller`, which must skip stale kline_sizes
    rather than returning their cached values (MAJOR-005 M05.5).
    '''

    def test_last_close_returns_none_when_all_kline_sizes_stale(
        self,
    ) -> None:
        from praxis.launcher import _last_close_from_poller

        poller = MarketDataPoller()
        stale_ts = datetime.now(tz=UTC) - timedelta(seconds=10000)
        _seed_cache(poller, 60, fetched_at=stale_ts)
        _seed_cache(poller, 300, fetched_at=stale_ts)

        result = _last_close_from_poller(poller, kline_sizes=(60, 300))

        assert result is None

    def test_last_close_returns_value_when_kline_fresh(self) -> None:
        from decimal import Decimal

        from praxis.launcher import _last_close_from_poller

        poller = MarketDataPoller()
        _seed_cache(poller, 60, fetched_at=datetime.now(tz=UTC))

        result = _last_close_from_poller(poller, kline_sizes=(60,))

        assert result == Decimal('50000.0')

    def test_last_close_falls_through_stale_to_fresh_kline(self) -> None:
        '''If the smallest kline is stale but a larger one is fresh,
        return the larger one's last close instead of swallowing both.'''

        from decimal import Decimal

        from praxis.launcher import _last_close_from_poller

        poller = MarketDataPoller()
        stale_ts = datetime.now(tz=UTC) - timedelta(seconds=10000)
        _seed_cache(poller, 60, fetched_at=stale_ts)
        _seed_cache(
            poller,
            300,
            fetched_at=datetime.now(tz=UTC),
            df=pl.DataFrame({'close': [49500.0]}),
        )

        result = _last_close_from_poller(poller, kline_sizes=(60, 300))

        assert result == Decimal('49500.0')
