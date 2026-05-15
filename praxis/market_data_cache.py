'''Disk-persisted kline cache for Praxis market data.

`MainCache` holds the foundational 1-min klines pulled from the
Limen-backed Hugging Face dataset (`vaquum/binance_btcusdt_1m_klines`)
and refreshed once a day. The on-disk parquet survives container
recreates because the operator points it at a host bind mount; an
in-memory `polars.DataFrame` mirror serves the hot path without
ever touching disk.

Cache refreshes never fire on a hot-path read; a separate scheduler
drives them on its own cadence.
'''

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
from limen.data.historical_data import HistoricalData

__all__ = ['MainCache']

_log = logging.getLogger(__name__)

_BASE_KLINE_SIZE_SECONDS = 60


class MainCache:

    '''Disk-persisted 1-min kline cache backed by Limen's HF dataset.

    The cache is layered as:

    * a parquet file on disk at the constructor-supplied
      `parquet_path` that survives container recreates because the
      operator typically points it at a host bind mount, and
    * an in-memory `polars.DataFrame` mirror that the hot path reads
      from without ever touching disk.

    `refresh()` calls Limen's `HistoricalData.get_spot_klines` with
    `start_date_limit` set to the cached `last_covered_ts` so only
    bars added since the previous refresh are pulled, then appends
    them to the on-disk parquet, atomically updates the main cache state with
    the new high-water timestamp, and reloads the in-memory mirror.
    `load()` is a read-only path used at boot to populate the mirror
    from disk without any network call.

    Args:
        parquet_path (Path | str): Path to the on-disk parquet file
            holding the kline buffer. Parent directory is created if
            missing.
        main_cache_state_path (Path | str): Path to the JSON main cache state holding
            `{"last_covered_ts": "..."}`. Parent directory is created
            if missing.
    '''

    def __init__(
        self,
        parquet_path: Path | str,
        main_cache_state_path: Path | str,
    ) -> None:

        self._parquet_path = Path(parquet_path)
        self._main_cache_state_path = Path(main_cache_state_path)
        self._frame: pl.DataFrame = pl.DataFrame()
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

        '''Highest `datetime` covered by the on-disk cache, from the main cache state.

        Returns:
            datetime | None: ISO 8601 UTC timestamp of the most
                recent bar in the cache, or `None` when the main cache state
                does not exist yet (first-ever boot).
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
        `refresh()`.

        Returns:
            None
        '''

        if not self._parquet_path.exists():
            self._frame = pl.DataFrame()
            return

        self._frame = pl.read_parquet(self._parquet_path)

    def refresh(self) -> None:

        '''Pull bars added since `last_covered_ts` from Limen and append.

        Reads the main cache state to get the previous high-water timestamp
        and asks Limen for klines starting after that point. The
        returned frame is concatenated with the on-disk cache,
        deduped by `datetime`, atomically rewritten to disk, and
        the main cache state is updated to the new high-water timestamp.
        Finally the in-memory mirror is reloaded from disk so a
        partially-written rewrite never leaks into the hot path.

        On the very first refresh the main cache state is absent; Limen is
        asked without `start_date_limit` and the full HF snapshot
        is written.

        Returns:
            None
        '''

        last_covered_ts = self.last_covered_ts
        start_date_limit = (
            last_covered_ts.strftime('%Y-%m-%d %H:%M:%S')
            if last_covered_ts is not None else None
        )

        new_bars = HistoricalData().get_spot_klines(
            kline_size=_BASE_KLINE_SIZE_SECONDS,
            start_date_limit=start_date_limit,
        )

        if new_bars.is_empty():
            _log.info(
                'main cache refresh: limen returned no new bars',
                extra={'last_covered_ts': start_date_limit},
            )
            return

        self.load()
        merged = (
            pl.concat([self._frame, new_bars])
            if not self._frame.is_empty() else new_bars
        )
        merged = merged.unique(subset=['datetime'], keep='last').sort('datetime')

        new_high_water = merged['datetime'].max()
        self._atomic_write_parquet(merged)
        self._atomic_write_main_cache_state(new_high_water)
        self._frame = merged

        _log.info(
            'main cache refresh: appended bars',
            extra={
                'rows_appended': new_bars.height,
                'rows_total': merged.height,
                'last_covered_ts': str(new_high_water),
            },
        )

    def bootstrap_if_empty(self) -> None:

        '''Trigger a one-shot `refresh()` when the on-disk cache is missing.

        Called once at process startup so a first-ever Praxis boot
        gets a usable MainCache without waiting for the 05:00 UTC
        scheduled refresh. No-op when the parquet already exists,
        so subsequent restarts cost only a `load()`.

        Returns:
            None
        '''

        if self._parquet_path.exists():
            return

        _log.info(
            'main cache bootstrap: disk parquet missing, refreshing now',
            extra={'parquet_path': str(self._parquet_path)},
        )
        self.refresh()

    def _atomic_write_parquet(self, frame: pl.DataFrame) -> None:

        '''Write `frame` to the parquet path via tempfile + os.replace.

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

        '''Write `{"last_covered_ts": <iso>}` to the main cache state atomically.

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
