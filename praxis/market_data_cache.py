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
from typing import Any

import polars as pl
from binancial.compute.get_spot_klines import get_spot_klines
from limen.data.historical_data import HistoricalData, _aggregate_spot_klines

__all__ = ['MainCache']

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
                file does not exist yet (first-ever boot).
        '''

        if not self._main_cache_state_path.exists():
            return None

        payload = json.loads(self._main_cache_state_path.read_text())
        raw = payload.get('last_covered_ts')

        if raw is None:
            return None

        return datetime.fromisoformat(raw)

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
        which weighted-merges 1-min bars into `kline_size`-second
        buckets (weighted mean, sum-of-squares for std, sum for
        volume / liquidity / maker_volume, first / last for OHLC,
        etc).

        Args:
            kline_size (int): Requested kline bucket width in
                seconds. Must be a positive multiple of 60.

        Returns:
            pl.DataFrame: 17-column kline frame at the requested
                bucket width. Empty when the in-memory frame is
                empty.
        '''

        if self._frame.is_empty():
            return self._frame

        if kline_size == _BASE_KLINE_SIZE_SECONDS:
            return self._frame

        return _aggregate_spot_klines(self._frame, kline_size)

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

            new_high_water = merged['datetime'].max()
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
