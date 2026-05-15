'''Disk-persisted kline cache for Praxis market data.

`MainCache` holds 1-min klines in a single host-bind-mounted
parquet file fed from two sources: a daily refresh from the
Limen-backed Hugging Face dataset (the foundational backfill) and
a per-minute refresh from `binancial.get_spot_klines` (the
trailing-edge top-up). Both refresh paths write to the same
on-disk parquet and the same in-memory `polars.DataFrame` mirror
so the hot path never touches disk and never has to stitch two
sources at read time.

Cache refreshes never fire on a hot-path read; a separate
scheduler drives the two refresh methods on their own cadences.
A single `_write_lock` serializes the two paths so the daily
Limen refresh and the per-minute binancial refresh cannot collide
at 05:00 UTC.
'''

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import polars as pl
from binancial.compute.get_spot_klines import get_spot_klines
from limen.data.historical_data import HistoricalData
from limen.data.historical_data import (
    _aggregate_spot_klines as _limen_aggregate_spot_klines,
)

__all__ = ['CacheScheduler', 'MainCache']

_log = logging.getLogger(__name__)

_BASE_KLINE_SIZE_SECONDS = 60
_BINANCE_SYMBOL = 'BTCUSDT'
_DATETIME_FMT = '%Y-%m-%d %H:%M:%S'
_BINANCIAL_BOOTSTRAP_HOURS = 1
_BINANCIAL_DROP_COLUMNS = ('median', 'iqr')


class MainCache:

    '''Disk-persisted 1-min kline cache fed from Limen + binancial.

    The cache is layered as:

    * a parquet file on disk at the constructor-supplied
      `parquet_path` that survives container recreates because the
      operator typically points it at a host bind mount, and
    * an in-memory `polars.DataFrame` mirror that the hot path reads
      from without ever touching disk.

    `refresh_from_limen()` calls Limen's
    `HistoricalData.get_spot_klines` with `start_date_limit` set to
    the cached `last_covered_ts` so only bars added since the
    previous refresh are pulled. `refresh_from_binancial()` calls
    `binancial.get_spot_klines` for the trailing window from
    `last_covered_ts` to `now`, drops the binancial-only `median` /
    `iqr` columns to match the canonical 17-column shape, and
    appends. Both paths concat with the on-disk cache, dedupe by
    `datetime` (last write wins on overlap, so the per-minute
    binancial refresh supersedes the daily Limen bars on the
    overlapping trailing day), atomically rewrite the parquet, and
    update the state file. A single `_write_lock` serializes them.

    `load()` is a read-only path used at boot to populate the
    mirror from disk without any network call. `get_market_data`
    is the hot-path read: aggregates the in-memory 1-min frame up
    to the requested `kline_size`.

    Args:
        client (Any): `binance.client.Client` used by
            `binancial.get_spot_klines`. Passed in so tests can
            substitute a mock.
        parquet_path (Path | str): Path to the on-disk parquet
            file holding the kline buffer. Parent directory is
            created if missing.
        main_cache_state_path (Path | str): Path to the JSON state
            file holding `{"last_covered_ts": "..."}`. Parent
            directory is created if missing.
    '''

    def __init__(
        self,
        client: Any,
        parquet_path: Path | str,
        main_cache_state_path: Path | str,
    ) -> None:

        self._client = client
        self._parquet_path = Path(parquet_path)
        self._main_cache_state_path = Path(main_cache_state_path)
        self._frame: pl.DataFrame = pl.DataFrame()
        self._write_lock = threading.Lock()
        self._parquet_path.parent.mkdir(parents=True, exist_ok=True)
        self._main_cache_state_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def frame(self) -> pl.DataFrame:

        '''In-memory mirror of the on-disk parquet (1-min klines).

        Returns:
            pl.DataFrame: Empty when nothing has been loaded or
                refreshed yet, otherwise the full kline buffer
                ordered by `datetime`.
        '''

        return self._frame

    @property
    def last_covered_ts(self) -> datetime | None:

        '''Highest `datetime` covered by the on-disk cache.

        Returns:
            datetime | None: ISO 8601 UTC timestamp of the most
                recent bar in the cache, or `None` when the state
                file does not exist yet (first-ever boot) or when
                the state file is unreadable / corrupt — in the
                corrupt case a warning is logged and `None` is
                returned so the bootstrap / binancial paths can
                self-heal the cache instead of permanently breaking
                both refresh paths.
        '''

        if not self._main_cache_state_path.exists():
            return None

        try:
            payload = json.loads(self._main_cache_state_path.read_text())
            raw = payload.get('last_covered_ts')

            if raw is None:
                return None

            return datetime.fromisoformat(raw)

        except (OSError, json.JSONDecodeError, ValueError) as exc:
            _log.warning(
                'main cache state file unreadable or corrupt; treating as '
                'absent so refresh paths self-heal',
                extra={
                    'main_cache_state_path': str(self._main_cache_state_path),
                    'error': repr(exc),
                },
            )
            return None

    def load(self) -> None:

        '''Read the on-disk parquet into the in-memory mirror.

        Idempotent. When the parquet does not exist the mirror is
        left as an empty `polars.DataFrame` and no exception is
        raised; the bootstrap path will populate it on first
        `refresh_from_limen()`.

        Returns:
            None
        '''

        if not self._parquet_path.exists():
            self._frame = pl.DataFrame()
            return

        self._frame = pl.read_parquet(self._parquet_path)

    def refresh_from_limen(self) -> None:

        '''Pull bars added since `last_covered_ts` from Limen and append.

        Reads the state file to get the previous high-water
        timestamp and asks Limen for klines starting after that
        point. The returned frame is merged into the on-disk cache
        under `_write_lock` so the per-minute binancial refresh
        cannot interleave.

        On the very first refresh the state file is absent; Limen
        is asked without `start_date_limit` and the full HF
        snapshot is written.

        Returns:
            None
        '''

        last_covered_ts = self.last_covered_ts
        start_date_limit = (
            last_covered_ts.strftime(_DATETIME_FMT)
            if last_covered_ts is not None else None
        )

        new_bars = HistoricalData().get_spot_klines(
            kline_size=_BASE_KLINE_SIZE_SECONDS,
            start_date_limit=start_date_limit,
        )

        if new_bars.is_empty():
            _log.info(
                'main cache refresh_from_limen: returned no new bars',
                extra={'last_covered_ts': start_date_limit},
            )
            return

        self._apply_new_bars(new_bars, source='limen')

    def refresh_from_binancial(self) -> None:

        '''Pull trailing-edge bars from binancial and append.

        Reads the state file to get the previous high-water
        timestamp (or defaults to `now - _BINANCIAL_BOOTSTRAP_HOURS`
        on first boot) and asks `binancial.get_spot_klines` for the
        window from there to `now`. The returned pandas frame is
        stripped of `median` / `iqr` (binancial-only columns absent
        from Limen's 17-column shape), converted to polars, and
        merged into the on-disk cache under `_write_lock`. On
        overlap with previously-Limen-sourced bars, the binancial
        bars win because they are fresher (last-write-wins via
        `unique(keep='last')`).

        Returns:
            None
        '''

        now = datetime.now(tz=UTC)
        last_covered_ts = self.last_covered_ts or (
            now - timedelta(hours=_BINANCIAL_BOOTSTRAP_HOURS)
        )

        if last_covered_ts >= now:
            _log.warning(
                'main cache refresh_from_binancial: last_covered_ts is not in '
                'the past, skipping (clock skew or corrupt state file?)',
                extra={
                    'last_covered_ts': last_covered_ts.isoformat(),
                    'now': now.isoformat(),
                },
            )
            return

        start_str = last_covered_ts.strftime(_DATETIME_FMT)
        end_str = now.strftime(_DATETIME_FMT)

        df_pd = get_spot_klines(
            self._client,
            symbol=_BINANCE_SYMBOL,
            kline_size=_BASE_KLINE_SIZE_SECONDS,
            start_date=start_str,
            end_date=end_str,
        )

        if df_pd.empty:
            _log.info(
                'main cache refresh_from_binancial: returned no new bars',
                extra={
                    'last_covered_ts': start_str,
                    'window_end': end_str,
                },
            )
            return

        new_bars = pl.from_pandas(
            df_pd.drop(columns=list(_BINANCIAL_DROP_COLUMNS), errors='ignore'),
        )
        new_bars = new_bars.with_columns(
            pl.col('datetime').cast(pl.Datetime('us', 'UTC')),
        )
        self._apply_new_bars(new_bars, source='binancial')

    def bootstrap_if_empty(self) -> None:

        '''Trigger a one-shot `refresh_from_limen()` when the parquet is missing.

        Called once at process startup so a first-ever Praxis boot
        gets a usable cache without waiting for the 05:00 UTC
        scheduled Limen refresh. No-op when the parquet already
        exists, so subsequent restarts cost only a `load()`.

        Returns:
            None
        '''

        if self._parquet_path.exists():
            return

        _log.info(
            'main cache bootstrap: disk parquet missing, refreshing now',
            extra={'parquet_path': str(self._parquet_path)},
        )
        self.refresh_from_limen()

    def get_market_data(self, kline_size: int) -> pl.DataFrame:

        '''Aggregate the in-memory 1-min frame up to `kline_size` and return.

        Hot-path read used by sensors. Returns the in-memory frame
        as-is when `kline_size == 60` (the base granularity);
        otherwise delegates to Limen's `_aggregate_spot_klines`
        (imported as `_limen_aggregate_spot_klines` — see TD note
        in `docs/TechnicalDebt.md` on pushing for a public Limen API)
        which weighted-merges 1-min bars into `kline_size`-second
        buckets (weighted mean, sum-of-squares for std, sum for
        volume / liquidity / maker_volume, first / last for OHLC,
        etc).

        Args:
            kline_size (int): Requested kline bucket width in
                seconds. Must be a positive multiple of
                `_BASE_KLINE_SIZE_SECONDS` (60).

        Raises:
            ValueError: When `kline_size <= 0` or
                `kline_size % _BASE_KLINE_SIZE_SECONDS != 0`.

        Returns:
            pl.DataFrame: 17-column kline frame at the requested
                bucket width. Empty when the in-memory frame is
                empty.
        '''

        if kline_size <= 0 or kline_size % _BASE_KLINE_SIZE_SECONDS != 0:
            msg = (
                f'kline_size must be a positive multiple of '
                f'{_BASE_KLINE_SIZE_SECONDS}, got {kline_size}'
            )
            raise ValueError(msg)

        if self._frame.is_empty():
            return self._frame

        if kline_size == _BASE_KLINE_SIZE_SECONDS:
            return self._frame

        return cast(
            pl.DataFrame,
            _limen_aggregate_spot_klines(self._frame, kline_size),
        )

    def _apply_new_bars(self, new_bars: pl.DataFrame, source: str) -> None:

        '''Concat, dedupe, sort, atomic-write — under `_write_lock`.

        Shared post-fetch path used by both `refresh_from_limen`
        and `refresh_from_binancial`. The lock prevents the daily
        Limen refresh and the per-minute binancial refresh from
        interleaving their disk writes (they would otherwise both
        rewrite the parquet from `self.load()` snapshots taken at
        different points and the later writer would clobber the
        earlier writer's bars). Reload happens inside the lock too
        so the in-memory mirror is always consistent with what is
        on disk.

        Args:
            new_bars (pl.DataFrame): The freshly-fetched 17-column
                1-min frame to merge in.
            source (str): Where `new_bars` came from (`limen` or
                `binancial`). Used only in the structured log line.
        '''

        with self._write_lock:
            self.load()
            merged = (
                pl.concat([self._frame, new_bars])
                if not self._frame.is_empty() else new_bars
            )
            merged = merged.unique(
                subset=['datetime'], keep='last',
            ).sort('datetime')

            new_high_water = cast(datetime, merged['datetime'].max())
            self._atomic_write_parquet(merged)
            self._atomic_write_main_cache_state(new_high_water)
            self._frame = merged

        _log.info(
            'main cache refresh appended bars',
            extra={
                'source': source,
                'rows_appended': new_bars.height,
                'rows_total': merged.height,
                'last_covered_ts': str(new_high_water),
            },
        )

    def _atomic_write_parquet(self, frame: pl.DataFrame) -> None:

        '''Write `frame` to the parquet path via tempfile + Path.replace.

        Polars writes through to disk in one shot; a crash mid-write
        would corrupt the parquet. Writing to a sibling tempfile and
        renaming on success makes the swap atomic so the file the
        next `load()` reads is always either the prior version or
        the new version, never a half-written hybrid.

        Args:
            frame (pl.DataFrame): The full kline buffer to persist.
        '''

        fd, tmp_path = tempfile.mkstemp(
            prefix=self._parquet_path.name + '.', suffix='.tmp',
            dir=self._parquet_path.parent,
        )
        os.close(fd)
        tmp = Path(tmp_path)
        try:
            frame.write_parquet(tmp)
            tmp.replace(self._parquet_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _atomic_write_main_cache_state(self, last_covered_ts: datetime) -> None:

        '''Write `{"last_covered_ts": <iso>}` to the state file atomically.

        Args:
            last_covered_ts (datetime): The new high-water timestamp.
                Always serialized as a UTC ISO 8601 string regardless
                of the input timezone.
        '''

        if last_covered_ts.tzinfo is None:
            last_covered_ts = last_covered_ts.replace(tzinfo=UTC)
        else:
            last_covered_ts = last_covered_ts.astimezone(UTC)

        payload = {'last_covered_ts': last_covered_ts.isoformat()}

        fd, tmp_path = tempfile.mkstemp(
            prefix=self._main_cache_state_path.name + '.', suffix='.tmp',
            dir=self._main_cache_state_path.parent,
        )
        os.close(fd)
        tmp = Path(tmp_path)
        try:
            tmp.write_text(json.dumps(payload))
            tmp.replace(self._main_cache_state_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise


def _seconds_until_next_limen_fire() -> float:

    '''Seconds from `now` until the next 05:00 UTC.

    The HF dataset publisher (out-of-tree, owned by the vaquum HF
    org) updates `latest.json` daily; 05:00 UTC gives the publisher
    a wide window after midnight to land the new snapshot before
    we pull. Returns a float so tests can patch this with a tiny
    constant for fast scheduler-loop coverage.
    '''

    now = datetime.now(tz=UTC)
    today_05 = now.replace(hour=5, minute=0, second=0, microsecond=0)
    target = today_05 if now < today_05 else today_05 + timedelta(days=1)
    return (target - now).total_seconds()


class CacheScheduler:

    '''Background scheduler that drives MainCache's two refresh paths.

    Owns two daemon threads, both wait-first-then-fire:

    * a Limen thread that fires `cache.refresh_from_limen()` once a
      day at 05:00 UTC (waits until the next 05:00 UTC, then fires,
      then waits again), and
    * a binancial thread that waits `binancial_interval_seconds`
      and then fires `cache.refresh_from_binancial()`, repeating
      forever. Wait-first avoids a double refresh at boot because
      the launcher already calls `cache.refresh_from_binancial()`
      synchronously before starting the scheduler.

    Both threads catch all exceptions inside the loop body — a
    single bad refresh logs at exception level and the thread keeps
    running. Shutdown is via `stop()` which sets a `threading.Event`
    that both threads check after every cycle (and that they sleep
    on, via `Event.wait(timeout=...)`, so a stop arriving mid-sleep
    cancels the sleep promptly).

    Args:
        cache (MainCache): The cache to refresh.
        binancial_interval_seconds (float): Sleep between consecutive
            binancial refreshes. Production default 60s; tests pass
            a tiny value for fast loop coverage.
        limen_schedule_fn (callable | None): Returns seconds to wait
            until the next Limen fire. Defaults to "seconds until
            next 05:00 UTC". Tests pass a `lambda: 0.05` to drive
            the Limen loop without waiting a full day.
    '''

    def __init__(
        self,
        cache: MainCache,
        binancial_interval_seconds: float = 60.0,
        limen_schedule_fn: Any = None,
    ) -> None:

        if binancial_interval_seconds <= 0:
            msg = (
                f'binancial_interval_seconds must be positive, '
                f'got {binancial_interval_seconds}'
            )
            raise ValueError(msg)

        self._cache = cache
        self._binancial_interval_seconds = float(binancial_interval_seconds)
        self._limen_schedule_fn = (
            limen_schedule_fn or _seconds_until_next_limen_fire
        )
        self._stop_event = threading.Event()
        self._limen_thread: threading.Thread | None = None
        self._binancial_thread: threading.Thread | None = None

    def start(self) -> None:

        '''Start the two refresh threads (idempotent).

        Returns:
            None
        '''

        if self._limen_thread is not None or self._binancial_thread is not None:
            return

        self._stop_event.clear()
        self._limen_thread = threading.Thread(
            target=self._limen_loop,
            name='cache-scheduler-limen',
            daemon=True,
        )
        self._binancial_thread = threading.Thread(
            target=self._binancial_loop,
            name='cache-scheduler-binancial',
            daemon=True,
        )
        self._limen_thread.start()
        self._binancial_thread.start()

        _log.info(
            'cache scheduler started',
            extra={
                'binancial_interval_seconds': self._binancial_interval_seconds,
            },
        )

    def stop(self, timeout_seconds: float = 10.0) -> None:

        '''Signal stop and join both threads with `timeout_seconds`.

        Idempotent — calling twice is a no-op the second time.

        Args:
            timeout_seconds (float): Per-thread join timeout. Loops
                check the stop event after each tick and inside
                their sleeps, so this should rarely block.
        '''

        self._stop_event.set()

        for attr_name in ('_limen_thread', '_binancial_thread'):
            thread = getattr(self, attr_name)

            if thread is None:
                continue

            thread.join(timeout=timeout_seconds)

            if thread.is_alive():
                _log.warning(
                    'cache scheduler thread did not stop within timeout',
                    extra={'thread_name': thread.name},
                )
                continue

            setattr(self, attr_name, None)

    def _limen_loop(self) -> None:

        '''Wait until the next Limen fire time, refresh, repeat.

        Limen is wall-clock-scheduled, not interval-scheduled, so we
        wait FIRST and refresh second; the at-boot population is
        handled by `MainCache.bootstrap_if_empty()` before the
        scheduler is started.
        '''

        while not self._stop_event.is_set():
            wait_seconds = max(0.0, float(self._limen_schedule_fn()))

            if self._stop_event.wait(timeout=wait_seconds):
                return

            try:
                self._cache.refresh_from_limen()
            except Exception:  # noqa: BLE001 - daemon must survive any refresh failure
                _log.exception('limen refresh failed in scheduler')

    def _binancial_loop(self) -> None:

        '''Wait `binancial_interval_seconds`, refresh, repeat.

        Wait-FIRST-then-refresh (mirrors `_limen_loop`) so the boot
        flow is a single source of refreshes: the launcher does one
        synchronous `refresh_from_binancial()` at startup, then the
        scheduler takes over after waiting one full interval. Pre-fix
        the loop refreshed immediately on thread start, which combined
        with the launcher's synchronous boot fill produced two
        back-to-back binancial fetches (~doubled trade-walk cost +
        rate-limit pressure). The first scheduler-driven fire now
        lands at boot + `binancial_interval_seconds`, which is the
        cadence the operator already expects.
        '''

        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=self._binancial_interval_seconds):
                return

            try:
                self._cache.refresh_from_binancial()
            except Exception:  # noqa: BLE001 - daemon must survive any refresh failure
                _log.exception('binancial refresh failed in scheduler')
