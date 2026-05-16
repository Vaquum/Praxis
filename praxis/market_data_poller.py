'''Thin staleness-aware adapter over `praxis.market_data_cache.MainCache`.

Pre-rewire `MarketDataPoller` ran a per-kline_size poller thread
that called `binancial.get_spot_klines` on a wall-clock cadence and
held a per-kline_size cache. That whole machine moved into
`MainCache` + `CacheScheduler`, which serve all kline_sizes from a
single 1-min on-disk parquet refreshed daily from Limen and per
minute from binancial.

This adapter survives only to preserve the public API the launcher
and `fallback_price_provider` still depend on:

* `get_market_data(kline_size)` returns the cache aggregated up to
  `kline_size`, raising `StaleMarketDataError` when the latest bar
  in the in-memory frame is older than `2 * kline_size` (or the
  per-kline override).
* `is_stale(kline_size)` is the non-raising counterpart.
* `StaleMarketDataError` itself is unchanged so existing
  `except StaleMarketDataError:` blocks keep working.

There is no `start()` / `stop()` / `add_kline_size` /
`remove_kline_size` here anymore — the cache is symbol-scoped, not
per-kline_size, and lifecycle is owned by `CacheScheduler`.
'''

from __future__ import annotations

import math
from datetime import UTC, datetime

import polars as pl

from praxis.market_data_cache import MainCache

__all__ = ['MarketDataPoller', 'StaleMarketDataError']

_DEFAULT_MAX_AGE_MULTIPLIER = 2


class StaleMarketDataError(Exception):

    '''Raised by `MarketDataPoller.get_market_data` when the cache is stale.

    Round-18 MAJOR-005 (pre-rewire): pre-fix the poller swallowed
    fetch failures and `get_market_data` returned the previous
    DataFrame indefinitely. Strategies could trade on hours-old
    klines after Binance public REST/testnet outages with no signal.
    Post-fix every read checks the latest bar's age against
    `max_age_seconds` (per kline_size, default `2 * kline_size`) and
    raises this exception so callers see explicit failure instead of
    silently old data.

    Args:
        kline_size: kline_size whose cache exceeded its max age.
        fetched_at: timestamp of the latest bar in the cache at
            read time (the bar's `datetime` column, not the wall
            clock when the cache was last refreshed).
        age_seconds: observed age in seconds at read time.
        max_age_seconds: configured max age the read exceeded.
    '''

    def __init__(
        self,
        kline_size: int,
        fetched_at: datetime,
        age_seconds: float,
        max_age_seconds: float,
    ) -> None:

        self.kline_size = kline_size
        self.fetched_at = fetched_at
        self.age_seconds = age_seconds
        self.max_age_seconds = max_age_seconds
        super().__init__(
            f'market data for kline_size={kline_size} is stale: '
            f'age={age_seconds:.1f}s exceeds max_age={max_age_seconds:.1f}s '
            f'(last bar at {fetched_at.isoformat()})'
        )


class MarketDataPoller:

    '''Staleness-aware adapter over `MainCache`.

    All actual fetching, on-disk persistence, and refresh
    scheduling lives in `MainCache` + `CacheScheduler`. This class
    exists only to gate hot-path reads on a per-kline_size max-age
    threshold so a stale cache (e.g. binancial refresh thread
    silently failing) raises an explicit `StaleMarketDataError`
    instead of returning hours-old data.

    Args:
        cache (MainCache): The cache to read from.
        max_age_overrides (dict[int, float] | None): Optional
            per-kline_size max-age in seconds, overriding the
            default `2 * kline_size`. Keys must be positive
            kline_sizes; values must be positive floats. Empty /
            `None` means defaults apply for every kline_size.
    '''

    def __init__(
        self,
        cache: MainCache,
        max_age_overrides: dict[int, float] | None = None,
    ) -> None:

        for ks, max_age in (max_age_overrides or {}).items():
            if ks <= 0:
                msg = (
                    f'max_age_overrides key (kline_size) must be '
                    f'positive; got {ks!r}'
                )
                raise ValueError(msg)

            if not isinstance(max_age, (int, float)) or isinstance(max_age, bool):
                msg = (
                    f'max_age_overrides value for kline_size={ks} '
                    f'must be int or float; got {type(max_age).__name__}'
                )
                raise TypeError(msg)

            if not math.isfinite(max_age):
                msg = (
                    f'max_age_overrides value for kline_size={ks} '
                    f'must be finite (no NaN/inf); got {max_age!r}. '
                    f'NaN would silently disable staleness '
                    f'(age > NaN is always False); inf would make '
                    f'the cache never stale.'
                )
                raise ValueError(msg)

            if max_age <= 0.0:
                msg = (
                    f'max_age_overrides value for kline_size={ks} '
                    f'must be > 0.0; got {max_age!r}'
                )
                raise ValueError(msg)

        self._cache = cache
        self._max_age_overrides = dict(max_age_overrides or {})

    def get_market_data(self, kline_size: int) -> pl.DataFrame:

        '''Return klines at `kline_size`, raising on stale cache.

        Calls `MainCache.snapshot(kline_size)` once so the staleness
        check and the returned aggregated frame both come from the
        same `MainCache._frame` reference. Without this single-call
        snapshot, a refresh that swapped `_frame` between two
        separate reads could surface a false `StaleMarketDataError`
        (decision made on the old frame, data taken from the new
        one) or vice versa.

        An empty in-memory frame is treated as fresh-but-empty and
        returned as-is — staleness only fires when there IS data
        and it is too old, mirroring the pre-rewire semantics where
        a cache that had never been written returned an empty frame
        without raising.

        Args:
            kline_size (int): Kline bucket width in seconds.

        Returns:
            pl.DataFrame: Aggregated kline frame; empty when the
                cache has not been populated yet.

        Raises:
            StaleMarketDataError: When the latest bar in the cache
                is older than the configured max age.
        '''

        aggregated, latest = self._cache.snapshot(kline_size)

        if latest is None:
            return aggregated

        max_age_seconds = self._max_age_seconds(kline_size)
        age_seconds = (datetime.now(tz=UTC) - latest).total_seconds()

        if age_seconds < 0 or age_seconds > max_age_seconds:
            raise StaleMarketDataError(
                kline_size=kline_size,
                fetched_at=latest,
                age_seconds=age_seconds,
                max_age_seconds=max_age_seconds,
            )

        return aggregated

    def is_stale(self, kline_size: int) -> bool:

        '''Non-raising staleness check.

        Uses `MainCache.snapshot(kline_size)` for the same
        single-snapshot read consistency as `get_market_data`.

        Used by `fallback_price_provider` (and any other caller
        that wants to short-circuit on stale data without
        exception flow control).

        A negative `age_seconds` (latest bar timestamped in the
        future — clock skew, manual cache edit, corruption) is also
        treated as stale: trading must not proceed on a cache whose
        most recent bar is impossible.

        Returns:
            bool: `True` when the latest bar in the cache is older
                than `max_age_seconds` for this kline_size; `True`
                when the cache is empty (no fresh data available);
                `True` when the latest bar is in the future (invalid
                cache state); `False` otherwise.
        '''

        _, latest = self._cache.snapshot(kline_size)

        if latest is None:
            return True

        max_age_seconds = self._max_age_seconds(kline_size)
        age_seconds = (datetime.now(tz=UTC) - latest).total_seconds()
        return age_seconds < 0 or age_seconds > max_age_seconds

    def _max_age_seconds(self, kline_size: int) -> float:

        '''Per-kline_size max age, falling back to `2 * kline_size`.'''

        override = self._max_age_overrides.get(kline_size)

        if override is not None:
            return override

        return float(_DEFAULT_MAX_AGE_MULTIPLIER * kline_size)
