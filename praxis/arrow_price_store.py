'''Closed-bar price reader over the control-plane Arrow volume.

Reads `<root>/<series>/latest.arrow` (the OHLCV frame Furnace predicts
on) and returns the most recent closed bar's `close`. The bar's settle
instant is family-dependent: for time bars `ts` is the bucket open, so
settle is `ts + interval_seconds`; for dollar bars (carrying a
`start_ts` open column) `ts` is already the settle, so settle is `ts`.
A bar is closed once its settle is at or before now, so the
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
_DEFAULT_MAX_STALENESS_INTERVALS = 3
_DOLLAR_OPEN_COLUMN = 'start_ts'


def _utc_now() -> datetime:
    '''Return the current UTC time.'''

    return datetime.now(tz=UTC)


class ArrowPriceStore:
    '''Stateless reader of closed-bar OHLCV close prices.

    Args:
        root: Read-only mount holding per-series OHLCV Arrow frames.
        clock: Callable returning the current UTC time, for tests.
        max_staleness_intervals: Reject a closed bar whose age exceeds
            this many `interval_seconds` — guards against a frozen feed
            serving an indefinitely stale price.
    '''

    def __init__(
        self,
        root: Path,
        clock: Callable[[], datetime] = _utc_now,
        max_staleness_intervals: int = _DEFAULT_MAX_STALENESS_INTERVALS,
    ) -> None:
        '''Store the Arrow root, clock, and staleness bound.'''

        self._root = root
        self._clock = clock
        self._max_staleness_intervals = max_staleness_intervals

    def latest_close(  # noqa: PLR0911 - one return per frame-rejection condition
        self,
        series: str,
        interval_seconds: int,
    ) -> Decimal | None:
        '''Return the latest closed bar's close for a series, or None.

        A bar's `ts` (Int64 UTC epoch nanoseconds) is the bucket open
        for time bars and the settle for dollar bars; the latter are
        identified by a `start_ts` open column. A bar is closed when its
        settle (`ts + interval_seconds` for time bars, `ts` for dollar
        bars) is at or before now. Returns None when the frame is absent
        (transient atomic-swap), unreadable / malformed (missing
        columns, or `ts` not Int64 — a `Datetime` or ms/s `ts` would
        otherwise compare meaninglessly against the ns cutoff and leak
        the forming bar), has no closed bar yet, the latest closed bar
        is staler than `max_staleness_intervals` intervals (frozen
        feed), or the close is missing or non-finite.

        Args:
            series: Series identifier, e.g. 'time_15m'.
            interval_seconds: For time bars the bar width; for dollar
                bars the predict cadence, used only as the staleness
                window since dollar bars have no fixed width.

        Returns:
            The closed-bar close as a Decimal, or None.
        '''

        path = self._root / series / _LATEST_ARROW
        if not path.is_file():
            _log.warning('ohlcv frame not found', extra={'series': series, 'path': str(path)})
            return None

        try:
            df = pl.read_ipc(path, memory_map=True)
        except (OSError, pl.exceptions.PolarsError):
            _log.warning('ohlcv frame unreadable', extra={'series': series, 'path': str(path)})
            return None

        if df.is_empty() or 'ts' not in df.columns or 'close' not in df.columns:
            _log.warning('ohlcv frame empty or malformed', extra={'series': series})
            return None

        if df.schema['ts'] != pl.Int64:
            _log.warning(
                'ohlcv ts column is not Int64 epoch-ns',
                extra={'series': series, 'ts_dtype': str(df.schema['ts'])},
            )
            return None

        now_ns = int(self._clock().timestamp() * _NS_PER_SECOND)
        settle_offset = 0 if _DOLLAR_OPEN_COLUMN in df.columns else interval_seconds
        cutoff = now_ns - settle_offset * _NS_PER_SECOND

        try:
            closed = df.filter(pl.col('ts') <= cutoff).sort('ts')
        except pl.exceptions.PolarsError:
            _log.warning('ohlcv frame filter/sort failed', extra={'series': series})
            return None

        if closed.is_empty():
            return None

        last = closed.tail(1)
        latest_ts = int(last.to_series(last.columns.index('ts'))[0])
        max_age_ns = self._max_staleness_intervals * interval_seconds * _NS_PER_SECOND

        if now_ns - latest_ts > max_age_ns:
            _log.warning(
                'latest closed ohlcv bar is stale',
                extra={
                    'series': series,
                    'age_seconds': (now_ns - latest_ts) // _NS_PER_SECOND,
                    'max_age_seconds': self._max_staleness_intervals * interval_seconds,
                },
            )
            return None

        close = last.to_series(last.columns.index('close'))[0]

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
