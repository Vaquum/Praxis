'''Shared market data poller for Nexus signal generation.

Periodically fetches klines from Binance spot REST per unique
kline_size and provides thread-safe read access for Nexus
instances. Each kline_size has its own poll interval and thread.
Supports runtime addition and removal of kline_sizes.
'''

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

import polars as pl
from binance.client import Client
from binancial.compute.get_spot_klines import get_spot_klines

__all__ = ['MarketDataPoller', 'StaleMarketDataError']

_log = logging.getLogger(__name__)

_BINANCE_SYMBOL = 'BTCUSDT'
_DEFAULT_MAX_AGE_MULTIPLIER = 2


class StaleMarketDataError(Exception):
    '''Raised by `MarketDataPoller.get_market_data` when the cache is stale.

    Round-18 MAJOR-005: pre-fix `_fetch` swallowed all exceptions and
    `get_market_data` returned the previous DataFrame indefinitely.
    Strategies could trade on hours-old klines after Binance public
    REST/testnet outages with no signal. Post-fix every cache entry
    is stamped with `fetched_at`; reads beyond `max_age_seconds` (per
    kline_size, default `2 * kline_size`) raise this exception so
    callers see explicit failure instead of silently old data.

    Args:
        kline_size: kline_size whose cache exceeded its max age.
        fetched_at: timestamp the stale entry was last written.
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
            f'(last fetched at {fetched_at.isoformat()})'
        )


@dataclass
class _PollerThread:
    thread: threading.Thread
    stop_event: threading.Event
    kline_size: int
    interval: float


class MarketDataPoller:
    '''Thread-based poller building klines from Binance spot REST trades.

    Each kline_size is polled at its own interval. Supports runtime
    addition and removal of kline_sizes without restarting.

    Args:
        kline_intervals: Initial mapping of kline_size (integer seconds) to poll interval (seconds, `float` to allow sub-second test cadences).
        n_rows: Number of klines to keep per kline_size. The fetch start date
            is computed as `now - n_rows * kline_size` seconds.
        testnet: When `True`, build poller `binance.client.Client` with
            `testnet=True` so REST calls go to `testnet.binance.vision`
            instead of mainnet `api.binance.com`. Default `False` keeps
            existing behavior. The launcher derives this flag from
            `TRADE_MODE` (`paper` → `True`, `live` → `False`) and pipes
            it through this constructor so paper trades read prices
            from the same venue they execute against — without it,
            ENTER notionals would be sized against mainnet BTCUSDT
            prices but reservations would land on the testnet capital
            pool.
    '''

    def __init__(
        self,
        kline_intervals: dict[int, float] | None = None,
        n_rows: int = 5000,
        testnet: bool = False,
        max_age_seconds: dict[int, float] | None = None,
    ) -> None:
        self._n_rows = n_rows
        self._data: dict[int, pl.DataFrame] = {}
        self._fetched_at: dict[int, datetime] = {}
        self._lock = threading.Lock()
        self._pollers: dict[int, _PollerThread] = {}
        self._refcounts: dict[int, int] = {}
        self._started = False
        self._initial_intervals = dict(kline_intervals or {})
        self._testnet = testnet
        for ks, max_age in (max_age_seconds or {}).items():
            if ks <= 0:
                msg = (
                    f'max_age_seconds key (kline_size) must be positive; '
                    f'got {ks!r}'
                )
                raise ValueError(msg)
            if max_age <= 0.0:
                msg = (
                    f'max_age_seconds value for kline_size={ks} must be > 0.0; '
                    f'got {max_age!r}'
                )
                raise ValueError(msg)
        self._max_age_overrides = dict(max_age_seconds or {})

    @property
    def running(self) -> bool:
        '''Whether the poller has been started.'''

        return self._started

    def start(self) -> None:
        '''Start poller threads for initial kline_sizes.

        Raises:
            ValueError: If any initial kline_size or interval is not positive.
        '''

        if self._started:
            return

        for kline_size, interval in self._initial_intervals.items():
            if kline_size <= 0:
                msg = f'kline_size must be positive, got {kline_size}'
                raise ValueError(msg)
            if interval <= 0:
                msg = f'interval must be positive, got {interval}'
                raise ValueError(msg)

        self._started = True

        with self._lock:
            for kline_size, interval in self._initial_intervals.items():
                self._refcounts[kline_size] = self._refcounts.get(kline_size, 0) + 1
                self._start_thread_locked(kline_size, interval)

        _log.info(
            'market data poller started',
            extra={'kline_sizes': sorted(self._pollers.keys())},
        )

    def stop(self) -> None:
        '''Stop all poller threads.'''

        with self._lock:
            self._started = False
            pollers = list(self._pollers.values())

        for pt in pollers:
            pt.stop_event.set()

        for pt in pollers:
            pt.thread.join(timeout=10)
            if pt.thread.is_alive():
                _log.warning(
                    'poller thread did not stop within timeout',
                    extra={'kline_size': pt.kline_size, 'thread_name': pt.thread.name},
                )

        with self._lock:
            self._pollers.clear()
            self._refcounts.clear()
            self._data.clear()
            self._fetched_at.clear()

        _log.info('market data poller stopped')

    def add_kline_size(self, kline_size: int, interval: float) -> None:
        '''Add a reference to a kline_size. Starts polling if first reference.

        Multiple strategies can reference the same kline_size. The poller
        thread only stops when all references are removed.

        Args:
            kline_size: Kline bucket width in seconds (integer — Binance
                kline sizes are all integer seconds: 60, 300, 900, etc.).
            interval: Poll interval in seconds, accepted as `float` so
                tests can use sub-second cadences (e.g. `0.1`) and
                production can use integer cadences (e.g. `300`) on the
                same code path. If already polling, the existing
                interval is kept (first caller wins).

        Raises:
            RuntimeError: If start() has not been called.
            ValueError: If kline_size or interval is not positive.
        '''

        if not self._started:
            msg = 'MarketDataPoller.start() must be called before add_kline_size'
            raise RuntimeError(msg)

        if kline_size <= 0:
            msg = f'kline_size must be positive, got {kline_size}'
            raise ValueError(msg)

        if interval <= 0:
            msg = f'interval must be positive, got {interval}'
            raise ValueError(msg)

        with self._lock:
            count = self._refcounts.get(kline_size, 0)
            self._refcounts[kline_size] = count + 1

            if kline_size in self._pollers:
                return

            self._start_thread_locked(kline_size, interval)

        _log.info(
            'added kline_size',
            extra={'kline_size': kline_size, 'interval': interval, 'refcount': count + 1},
        )

    def remove_kline_size(self, kline_size: int) -> None:
        '''Remove a reference to a kline_size. Stops polling when last reference removed.

        Args:
            kline_size: Kline bucket width in seconds.
        '''

        with self._lock:
            count = self._refcounts.get(kline_size, 0)

            if count <= 1:
                self._refcounts.pop(kline_size, None)
                pt = self._pollers.pop(kline_size, None)
                self._data.pop(kline_size, None)
                self._fetched_at.pop(kline_size, None)
                if pt is not None:
                    pt.stop_event.set()
            else:
                self._refcounts[kline_size] = count - 1
                return

        if pt is not None:
            pt.thread.join(timeout=10)
            if pt.thread.is_alive():
                _log.warning(
                    'poller thread did not stop within timeout',
                    extra={'kline_size': pt.kline_size, 'thread_name': pt.thread.name},
                )
            with self._lock:
                self._data.pop(kline_size, None)
                self._fetched_at.pop(kline_size, None)
            _log.info('removed kline_size', extra={'kline_size': kline_size})

    def get_market_data(self, kline_size: int) -> pl.DataFrame:
        '''Return latest kline DataFrame for a given kline_size.

        Round-18 MAJOR-005: raises `StaleMarketDataError` when the cache
        for this kline_size exceeds `max_age_seconds` (default
        `2 * kline_size`). Pre-fix the previous DataFrame was returned
        indefinitely after polling failures, letting strategies trade
        on arbitrarily old prices. Callers that want a stale-OK read
        should call `is_stale(kline_size)` and decide explicitly.

        Args:
            kline_size: Kline bucket width in seconds.

        Returns:
            Rolling DataFrame of klines. Empty DataFrame if no fetch
            has succeeded yet for this kline_size.

        Raises:
            StaleMarketDataError: When the cached entry is older than
                the configured max age.
        '''

        max_age = self._resolve_max_age(kline_size)

        with self._lock:
            df = self._data.get(kline_size)
            fetched_at = self._fetched_at.get(kline_size)
            if df is None or fetched_at is None:
                return pl.DataFrame()
            age = (datetime.now(tz=UTC) - fetched_at).total_seconds()
            if age > max_age:
                raise StaleMarketDataError(
                    kline_size=kline_size,
                    fetched_at=fetched_at,
                    age_seconds=age,
                    max_age_seconds=max_age,
                )
            return df

    def is_stale(self, kline_size: int) -> bool:
        '''Return True when cached data for `kline_size` exceeds max age.

        Non-raising counterpart to `get_market_data` for callers (e.g.,
        `fallback_price_provider`) that want to short-circuit on
        staleness without exception flow control.
        '''

        max_age = self._resolve_max_age(kline_size)

        with self._lock:
            fetched_at = self._fetched_at.get(kline_size)
            if fetched_at is None:
                return True
            age = (datetime.now(tz=UTC) - fetched_at).total_seconds()
            return age > max_age

    def _resolve_max_age(self, kline_size: int) -> float:
        '''Per-kline max age, falling back to `2 * kline_size`.'''

        override = self._max_age_overrides.get(kline_size)
        if override is not None:
            return override
        return float(_DEFAULT_MAX_AGE_MULTIPLIER * kline_size)

    def _start_thread_locked(self, kline_size: int, interval: float) -> None:
        '''Create and start a poller thread. Must be called with lock held.'''

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._poll_loop,
            args=(kline_size, interval, stop_event),
            daemon=True,
            name=f'poller-{kline_size}s',
        )

        pt = _PollerThread(
            thread=thread,
            stop_event=stop_event,
            kline_size=kline_size,
            interval=interval,
        )

        self._pollers[kline_size] = pt
        thread.start()

    def _poll_loop(self, kline_size: int, interval: float, stop_event: threading.Event) -> None:
        # Per-thread Binance client: public klines only, no credentials.
        # One client per poller thread avoids sharing a requests.Session
        # across threads. ping=False skips python-binance's default startup
        # health call against Binance — we only need the client for signed
        # or unsigned REST calls made explicitly by `get_spot_klines`.
        try:
            client = Client(None, None, ping=False, testnet=self._testnet)
        except Exception:  # noqa: BLE001 - thread-top exception; log and exit
            _log.exception(
                'failed to create Binance client; poller thread exiting',
                extra={'kline_size': kline_size, 'testnet': self._testnet},
            )
            return

        # Anchored-cadence schedule with skip-missed-slots: subsequent
        # fetches fire at `anchor + n * interval` rather than
        # `interval` after the previous fetch's body returned. After
        # each fetch returns, `n` advances to the smallest integer
        # such that `anchor + n * interval` is in the future; this
        # collapses any number of "missed" slots into a single
        # catch-up fetch instead of firing back-to-back. The
        # guarantee is "no cumulative drift": a slow fetch's overrun
        # is absorbed once (into the next fetch's wait window) and
        # the schedule remains anchored to the original timeline, so
        # `n` slow fetches do not produce `n * overrun` cumulative
        # drift. When a fetch outruns its `interval` window the next
        # fetch necessarily starts late (it cannot start before the
        # previous returned); when the overrun spans `k` intervals,
        # `k - 1` scheduled slots are skipped (their freshness goal
        # is moot — the slow fetch's return brings data through
        # `now`) and the next fetch fires at the next future slot,
        # then cadence resumes. Pre-fix the loop did `while not
        # stop_event.wait(timeout=interval): self._fetch(...)` — the
        # wait fired *after* `_fetch` returned, so realized period
        # was `interval + fetch_duration` and every slow fetch
        # shifted the entire downstream schedule by `slow_overrun`.
        # On Binance testnet under load `_fetch` regularly takes
        # 200-500s (the `get_spot_klines` HTTP call queues behind
        # rate-limited concurrent requests from the venue adapter),
        # which for `interval=300` (5m kline) pushed realized period
        # past `_DEFAULT_MAX_AGE_MULTIPLIER * kline_size = 600s` and
        # tripped `StaleMarketDataError` on the next sensor tick.
        anchor = time.monotonic()
        self._fetch(kline_size, client, stop_event)
        # The initial fetch can itself overrun `interval` on a cold
        # cache (Binance's first call needs an exchangeInfo round-trip
        # to populate the symbol filter cache, then the actual
        # historical kline fetch); advance `n` past any slots it spent
        # so iter 1 doesn't fire immediately back-to-back the same
        # way subsequent slow fetches don't.
        elapsed = time.monotonic() - anchor
        n = max(1, int(elapsed // interval) + 1)

        while True:
            wait_seconds = max(0.0, anchor + n * interval - time.monotonic())
            if stop_event.wait(timeout=wait_seconds):
                return
            self._fetch(kline_size, client, stop_event)
            elapsed = time.monotonic() - anchor
            n = max(n + 1, int(elapsed // interval) + 1)

    def _fetch(
        self,
        kline_size: int,
        client: Client,
        stop_event: threading.Event,
    ) -> None:
        try:
            start_dt = datetime.now(tz=UTC) - timedelta(
                seconds=kline_size * self._n_rows,
            )
            start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            df_pd = get_spot_klines(
                client,
                symbol=_BINANCE_SYMBOL,
                kline_size=kline_size,
                start_date=start_str,
            )
            df = pl.from_pandas(df_pd)

            with self._lock:
                # Round-18 PR #87 review: a fetch that started before
                # `remove_kline_size` set `stop_event` can land here
                # after `thread.join(timeout=10)` returned. Writing in
                # that window would resurrect a removed kline_size and
                # could race a freshly-started thread for the same
                # size. Skip the write when stopping; the post-join
                # cleanup pop in `remove_kline_size` then leaves the
                # cache empty.
                if stop_event.is_set():
                    return
                self._data[kline_size] = df
                self._fetched_at[kline_size] = datetime.now(tz=UTC)

            _log.debug(
                'fetched klines',
                extra={'kline_size': kline_size, 'rows': df.height},
            )
        except Exception:  # noqa: BLE001
            _log.exception('failed to fetch klines', extra={'kline_size': kline_size})
