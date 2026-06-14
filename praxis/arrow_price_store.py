'''Closed-bar price reader over the control-plane Arrow volume.

Reads `<root>/<series>/latest.arrow` (the OHLCV frame Furnace predicts
on) and returns the most recent closed bar's `close`. A bar with open
timestamp `ts` is closed once `ts + interval_seconds <= now`, so the
still-forming final bar is excluded. Used for ENTER reference pricing
and mark-to-market once the in-process market-data cache is retired.
'''

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from datetime import datetime, UTC
from decimal import Decimal, InvalidOperation
from pathlib import Path

import polars as pl

__all__ = ['ArrowPriceStore']

_log = logging.getLogger(__name__)

_LATEST_ARROW = 'latest.arrow'
_NS_PER_SECOND = 1_000_000_000


def _utc_now() -> datetime:
    '''Return the current UTC time.'''

    return datetime.now(tz=UTC)


class ArrowPriceStore:
    '''Stateless reader of closed-bar OHLCV close prices.

    Args:
        root: Read-only mount holding per-series OHLCV Arrow frames.
        clock: Callable returning the current UTC time, for tests.
    '''

    def __init__(
        self,
        root: Path,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        '''Store the Arrow root and clock.'''

        self._root = root
        self._clock = clock

    def latest_close(self, series: str, interval_seconds: int) -> Decimal | None:
        '''Return the latest closed bar's close for a series, or None.

        A bar with open `ts` is closed when `ts + interval_seconds`
        nanoseconds is at or before now. Returns None when the frame is
        absent (transient atomic-swap), has no closed bar yet, or the
        close is missing or non-finite.

        Args:
            series: Series identifier, e.g. 'time_15m'.
            interval_seconds: Bar width in seconds for the series.

        Returns:
            The closed-bar close as a Decimal, or None.
        '''

        path = self._root / series / _LATEST_ARROW
        if not path.is_file():
            _log.warning('ohlcv frame not found', extra={'series': series, 'path': str(path)})
            return None

        df = pl.read_ipc(path, memory_map=True)
        if df.is_empty() or 'ts' not in df.columns or 'close' not in df.columns:
            _log.warning('ohlcv frame empty or malformed', extra={'series': series})
            return None

        now_ns = int(self._clock().timestamp() * _NS_PER_SECOND)
        cutoff = now_ns - interval_seconds * _NS_PER_SECOND
        closed = df.filter(pl.col('ts') <= cutoff)

        if closed.is_empty():
            return None

        close = closed.sort('ts').tail(1).to_series(closed.columns.index('close'))[0]

        return self._to_finite_decimal(close, series)

    @staticmethod
    def _to_finite_decimal(value: object, series: str) -> Decimal | None:
        '''Coerce a finite numeric close to Decimal, or None.'''

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _log.warning('non-numeric ohlcv close', extra={'series': series})
            return None

        if not math.isfinite(value):
            _log.warning('non-finite ohlcv close', extra={'series': series})
            return None

        try:
            return Decimal(str(value))
        except InvalidOperation:
            _log.warning('uncoercible ohlcv close', extra={'series': series})
            return None
