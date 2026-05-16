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
import math
import os
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast

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

        Always returned as an aware UTC `datetime` so callers
        (notably `refresh_from_binancial`'s `last_covered_ts >= now`
        check, where `now` is aware UTC) never face a naive-vs-aware
        `TypeError`. A naive ISO string on disk is assumed to be
        UTC; an aware ISO string is converted to UTC.

        Returns:
            datetime | None: Aware UTC timestamp of the most recent
                bar in the cache, or `None` when the state file
                does not exist yet (first-ever boot) or when the
                state file is unreadable / corrupt — in the corrupt
                case a warning is logged and `None` is returned so
                the bootstrap / binancial paths can self-heal the
                cache instead of permanently breaking both refresh
                paths.
        '''

        if not self._main_cache_state_path.exists():
            return None

        try:
            payload = json.loads(self._main_cache_state_path.read_text())

            if not isinstance(payload, dict):
                msg = (
                    f'expected JSON object at top level, got '
                    f'{type(payload).__name__}'
                )
                raise TypeError(msg)

            raw = payload.get('last_covered_ts')

            if raw is None:
                return None

            if not isinstance(raw, str):
                msg = (
                    f'expected `last_covered_ts` to be a string, got '
                    f'{type(raw).__name__}'
                )
                raise TypeError(msg)

            parsed = datetime.fromisoformat(raw)

            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)

            return parsed.astimezone(UTC)

        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
            AttributeError,
        ) as exc:
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

        When the parquet exists but cannot be read (corrupt bytes,
        OS error, etc.), the parquet and state file are quarantined
        (renamed to `<name>.corrupt-<UTC-iso>` so the bad bytes are
        preserved for forensic inspection), the in-memory mirror
        is reset to empty, and a warning is logged. The next
        refresh through `_apply_new_bars` will then write a fresh
        parquet and state file from the freshly-fetched bars — so
        a runtime corruption self-heals on the next refresh tick
        instead of looping forever inside the scheduler.

        Returns:
            None
        '''

        if not self._parquet_path.exists():
            self._frame = pl.DataFrame()
            return

        try:
            self._frame = pl.read_parquet(self._parquet_path)
        except Exception as exc:  # noqa: BLE001 - quarantine + self-heal
            _log.warning(
                'main cache parquet unreadable; quarantining and resetting '
                'in-memory frame so the next refresh self-heals',
                extra={
                    'parquet_path': str(self._parquet_path),
                    'error': repr(exc),
                },
            )
            self._quarantine_corrupt_files()
            self._frame = pl.DataFrame()

    def _latest_frame_ts(self) -> datetime | None:

        '''Aware-UTC max `datetime` in `self._frame`, or `None` if empty.

        Used as the second-priority fallback in
        `refresh_from_binancial` so a missing-state-file scenario
        (operator deleted it, partial atomic write, etc.) does not
        skip from the last on-disk bar back to `now - 1h`. The
        return value is always normalized to UTC (naive → `replace`,
        aware non-UTC → `astimezone`) so a downstream `strftime`
        cannot silently drop a non-zero offset and turn `start_date`
        into the wrong wall-clock window.
        '''

        if self._frame.is_empty():
            return None

        raw = self._frame['datetime'].max()

        if raw is None:
            return None

        latest = cast(datetime, raw)

        if latest.tzinfo is None:
            return latest.replace(tzinfo=UTC)

        return latest.astimezone(UTC)

    def _quarantine_corrupt_files(self) -> None:

        '''Rename parquet + state to `<name>.corrupt-<UTC-iso>`.

        Each file is handled independently and missing files are
        skipped — partial-state pairs are meaningless without their
        matching parquet so both are renamed when present. Failures
        to rename are logged but not raised; the caller has already
        reset the in-memory frame and the next refresh will overwrite
        the original paths regardless.
        '''

        suffix = f'.corrupt-{datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")}'

        for path in (self._parquet_path, self._main_cache_state_path):
            if not path.exists():
                continue

            quarantined = path.with_name(path.name + suffix)
            try:
                path.replace(quarantined)
            except OSError as exc:
                _log.warning(
                    'main cache: failed to quarantine corrupt file',
                    extra={
                        'path': str(path),
                        'quarantined_to': str(quarantined),
                        'error': repr(exc),
                    },
                )

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

        Resolves the window start in this priority order:

        1. `self.last_covered_ts` (state file present + parseable
           AND in the past — a future timestamp is treated as
           corrupt state and skipped; this prevents a clock-skew or
           manual-edit incident from permanently freezing refresh
           because pre-fix the future-ts branch only logged and
           returned)
        2. the max `datetime` in the in-memory `_frame` (parquet
           loaded but state file missing — e.g. operator deleted
           it, or an atomic write succeeded for the parquet but
           failed for the state file); this prevents a multi-hour
           gap between the newest on-disk bar and `now - 1h` that
           a naive `now - _BINANCIAL_BOOTSTRAP_HOURS` fallback
           would otherwise introduce. The state file is repaired
           automatically by `_atomic_write_main_cache_state` at
           the end of this refresh
        3. `now - _BINANCIAL_BOOTSTRAP_HOURS` (first-ever boot,
           no state, no in-memory bars)

        A final safety clamp: if the resolved `last_covered_ts` is
        STILL `>= now` (e.g. `_frame` itself contains future bars
        because something else wrote them), the window start is
        clamped to `now - _BINANCIAL_BOOTSTRAP_HOURS` so the fetch
        always covers a finite past window and the cache can
        self-heal on the next write.

        Asks `binancial.get_spot_klines` for the window from the
        resolved start to `now`. The returned pandas frame is
        stripped of `median` / `iqr` (binancial-only columns absent
        from Limen's 17-column shape), converted to polars, and
        merged into the on-disk cache under `_write_lock`. On
        overlap with previously-Limen-sourced bars, the binancial
        bars win (`_apply_new_bars` source-aware dedup).

        Returns:
            None
        '''

        now = datetime.now(tz=UTC)
        state_ts = self.last_covered_ts

        if state_ts is not None and state_ts >= now:
            _log.warning(
                'main cache refresh_from_binancial: state last_covered_ts is '
                'in the future, treating as corrupt and falling back (clock '
                'skew or manual state edit); cache self-heals when this '
                'refresh writes a fresh last_covered_ts',
                extra={
                    'state_last_covered_ts': state_ts.isoformat(),
                    'now': now.isoformat(),
                },
            )
            state_ts = None

        last_covered_ts = (
            state_ts
            or self._latest_frame_ts()
            or (now - timedelta(hours=_BINANCIAL_BOOTSTRAP_HOURS))
        )

        if last_covered_ts >= now:
            _log.warning(
                'main cache refresh_from_binancial: resolved last_covered_ts '
                'is still in the future after fallback (frame max also in '
                'the future?); clamping to bootstrap window so the cache '
                'self-heals',
                extra={
                    'resolved_last_covered_ts': last_covered_ts.isoformat(),
                    'now': now.isoformat(),
                },
            )
            last_covered_ts = now - timedelta(hours=_BINANCIAL_BOOTSTRAP_HOURS)

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

    def snapshot(
        self,
        kline_size: int,
    ) -> tuple[pl.DataFrame, datetime | None]:

        '''Return aggregated frame + latest bar ts from one frame ref.

        Captures `self._frame` once into a local name then derives
        both pieces of data from THAT reference, so a refresh that
        swaps `self._frame` between the two reads cannot make the
        caller's staleness check disagree with the data it returns.
        Used by `MarketDataPoller` to gate hot-path reads on
        per-kline_size max-age without the read-race that would
        exist if the poller called `cache.frame` and
        `cache.get_market_data` separately.

        Args:
            kline_size (int): Requested kline bucket width in
                seconds. Must be a positive multiple of
                `_BASE_KLINE_SIZE_SECONDS` (60).

        Raises:
            ValueError: When `kline_size <= 0` or
                `kline_size % _BASE_KLINE_SIZE_SECONDS != 0`.

        Returns:
            tuple[pl.DataFrame, datetime | None]: Aggregated frame
                at `kline_size` and the highest `datetime` in the
                source 1-min frame (aware UTC), or an empty frame
                + `None` when nothing has been loaded yet. Both
                values are derived from the same `self._frame`
                reference captured atomically at call entry.
        '''

        if kline_size <= 0 or kline_size % _BASE_KLINE_SIZE_SECONDS != 0:
            msg = (
                f'kline_size must be a positive multiple of '
                f'{_BASE_KLINE_SIZE_SECONDS}, got {kline_size}'
            )
            raise ValueError(msg)

        frame = self._frame

        if frame.is_empty():
            return frame, None

        raw_latest = frame['datetime'].max()
        latest = cast(datetime, raw_latest) if raw_latest is not None else None

        if latest is not None:
            latest = (
                latest.replace(tzinfo=UTC)
                if latest.tzinfo is None
                else latest.astimezone(UTC)
            )

        if kline_size == _BASE_KLINE_SIZE_SECONDS:
            return frame, latest

        aggregated = cast(
            pl.DataFrame,
            _limen_aggregate_spot_klines(frame, kline_size),
        )
        return aggregated, latest

    def _apply_new_bars(self, new_bars: pl.DataFrame, source: str) -> None:

        '''Concat, dedupe, sort, atomic-write — under `_write_lock`.

        Shared post-fetch path used by both `refresh_from_limen`
        and `refresh_from_binancial`. The lock serializes the two
        refresh threads so they cannot interleave their disk writes
        (and so `self._frame = merged` is the only write to the
        in-memory mirror in flight at any time). Because we are the
        only writer to both the parquet and `self._frame`, the
        in-memory mirror is the authoritative current state — there
        is no need to re-read the parquet from disk inside the lock
        on every refresh tick. Re-reading would scale per-refresh I/O
        as O(size_of_cache) and become a real cost as the cache grows
        (~1MB/day). The on-disk parquet is read at boot via
        `Launcher._start_poller -> cache.load()` and on a runtime
        corruption recovery via `load()`'s self-heal path; otherwise
        the in-memory frame and the on-disk parquet are kept in
        lock-step by the atomic write at the bottom of this method.

        Overlap precedence is source-aware so the documented
        "binancial wins on overlap with Limen" contract holds
        regardless of fetch order:

        * `source == 'binancial'`: `keep='last'`. With the concat
          order `[self._frame, new_bars]`, new binancial bars
          overwrite any pre-existing Limen bars at the boundary.
        * `source == 'limen'`: `keep='first'`. Existing rows in
          `self._frame` (which include all binancial-sourced bars)
          win over a re-fetched Limen snapshot. Without this branch
          a corrupt-state-triggered full Limen re-fetch could
          overwrite freshly-written binancial bars at the trailing
          edge.

        Fast path: when `new_bars.min()` is strictly greater than
        `self._frame.max()` (the common per-minute case — binancial
        returns the trailing minute(s) which are always newer than
        anything already cached), there is no overlap and both
        inputs are already sorted, so a plain `pl.concat` produces
        a correctly-sorted result without an O(N log N) full
        dedupe+sort pass. The slow path (dedupe + sort) only runs
        when there IS overlap (Limen boundary, corrupt-state full
        re-fetch, or any other case where `new_bars.min()` falls
        inside the cached window). Without this fast path, every
        per-minute refresh would re-sort the entire cache under
        `_write_lock` and the cost would scale with cache size —
        not acceptable since there is no trim policy and the cache
        grows ~1MB/day.

        Args:
            new_bars (pl.DataFrame): The freshly-fetched 17-column
                1-min frame to merge in.
            source (str): Where `new_bars` came from. Must be
                exactly `'limen'` or `'binancial'`; any other value
                raises `ValueError` so a typo cannot silently fall
                through to one of the dedup paths.
        '''

        if source not in ('limen', 'binancial'):
            msg = (
                f"_apply_new_bars source must be 'limen' or "
                f"'binancial', got {source!r}"
            )
            raise ValueError(msg)

        keep: Literal['first', 'last'] = (
            'last' if source == 'binancial' else 'first'
        )

        with self._write_lock:
            if self._frame.is_empty():
                merged = new_bars.unique(
                    subset=['datetime'], keep=keep,
                ).sort('datetime')
            else:
                current_max = cast(datetime, self._frame['datetime'].max())
                new_min = cast(datetime, new_bars['datetime'].min())

                if new_min > current_max:
                    merged = pl.concat([self._frame, new_bars])
                else:
                    merged = pl.concat([self._frame, new_bars]).unique(
                        subset=['datetime'], keep=keep,
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

        if not math.isfinite(binancial_interval_seconds):
            msg = (
                f'binancial_interval_seconds must be finite (no NaN/inf); '
                f'got {binancial_interval_seconds!r}. NaN would crash the '
                f'daemon via Event.wait(timeout=NaN); inf would stall '
                f'refresh forever.'
            )
            raise ValueError(msg)

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

        '''Start the two refresh threads (idempotent and recovery-safe).

        No-ops only when BOTH thread refs are non-None AND alive.
        Dead refs (left over from a `stop()` that timed out and
        skipped its `setattr(..., None)` cleanup, or from a thread
        that exited unexpectedly) are cleared and replaced with
        fresh threads so a stop → start cycle and recovery from a
        dead thread both work reliably. Pre-fix `start()` no-oped
        on any non-None ref and a timed-out stop made every
        subsequent start a permanent no-op even with no live
        threads.

        Returns:
            None
        '''

        limen_alive = (
            self._limen_thread is not None and self._limen_thread.is_alive()
        )
        binancial_alive = (
            self._binancial_thread is not None
            and self._binancial_thread.is_alive()
        )

        if limen_alive and binancial_alive:
            return

        if not limen_alive:
            self._limen_thread = None

        if not binancial_alive:
            self._binancial_thread = None

        self._stop_event.clear()

        if self._limen_thread is None:
            self._limen_thread = threading.Thread(
                target=self._limen_loop,
                name='cache-scheduler-limen',
                daemon=True,
            )
            self._limen_thread.start()

        if self._binancial_thread is None:
            self._binancial_thread = threading.Thread(
                target=self._binancial_loop,
                name='cache-scheduler-binancial',
                daemon=True,
            )
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
            try:
                raw_wait = float(self._limen_schedule_fn())
            except Exception:  # noqa: BLE001 - daemon must survive a broken schedule_fn
                _log.exception(
                    'limen_schedule_fn raised or returned a non-numeric '
                    'value; falling back to 1-hour wait',
                )
                raw_wait = 3600.0

            if not math.isfinite(raw_wait):
                _log.warning(
                    'limen_schedule_fn returned non-finite seconds; '
                    'falling back to 1-hour wait',
                    extra={'raw_wait_seconds': raw_wait},
                )
                wait_seconds = 3600.0
            else:
                wait_seconds = max(0.0, raw_wait)

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
