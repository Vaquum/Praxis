'''Load replay bars from the mounted prediction and OHLCV frames.

A replay run over real history slices a `[start, end]` window out of the
projection frames Praxis already mounts read-only: the Conduit prediction
frame (`<conduit>/<series>/latest.arrow`, full history of
`ts, prediction, probability, reason_code`) and the control-plane OHLCV
frame (`<arrow>/<series>/latest.arrow`, `ts, close`, plus `start_ts` for
dollar series). The two are joined on the shared `ts`, usable rows are
kept, and each surviving row becomes a `ReplayBar`.

Family is read from the OHLCV frame: a `start_ts` column means the series
is dollar (its `ts` is the settle and `start_ts` the open), otherwise it
is a time series (its `ts` is the open and the settle is
`ts + interval_seconds`).
'''

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path

import polars as pl

from praxis.replay.replay_scenario import ReplayBar

__all__ = ['load_replay_bars']

_LATEST_ARROW = 'latest.arrow'
_USABLE_REASON_CODE = 0
_DOLLAR_OPEN_COLUMN = 'start_ts'
_NS_PER_SECOND = 1_000_000_000


def load_replay_bars(
    *,
    arrow_dir: Path,
    conduit_dir: Path,
    series: str,
    interval_seconds: int,
    start: datetime,
    end: datetime,
) -> tuple[ReplayBar, ...]:
    '''Build settle-ordered ReplayBars for a series over `[start, end]`.

    Args:
        arrow_dir: Read-only mount holding per-series OHLCV frames.
        conduit_dir: Read-only mount holding per-series prediction frames.
        series: Series identifier, e.g. 'time_15m' or 'dollar_60M'.
        interval_seconds: Bar width for time series; ignored for dollar
            series, whose `ts` already carries the settle.
        start: Inclusive lower bound on a bar's settle (timezone-aware).
        end: Inclusive upper bound on a bar's settle (timezone-aware).

    Returns:
        ReplayBars whose settle falls in `[start, end]`, ordered by `ts`.
    '''

    if start.tzinfo is None or end.tzinfo is None:
        msg = 'start and end must be timezone-aware'
        raise ValueError(msg)

    ohlcv = pl.read_ipc(arrow_dir / series / _LATEST_ARROW, memory_map=True)
    predictions = pl.read_ipc(conduit_dir / series / _LATEST_ARROW, memory_map=True)

    is_dollar = _DOLLAR_OPEN_COLUMN in ohlcv.columns
    ohlcv_columns = ['ts', 'close']

    if is_dollar:
        ohlcv_columns.append(_DOLLAR_OPEN_COLUMN)

    usable = predictions.filter(pl.col('reason_code') == _USABLE_REASON_CODE)
    joined = usable.join(ohlcv.select(ohlcv_columns), on='ts', how='inner').sort('ts')

    interval_ns = interval_seconds * _NS_PER_SECOND
    start_ns = int(start.timestamp() * _NS_PER_SECOND)
    end_ns = int(end.timestamp() * _NS_PER_SECOND)

    bars: list[ReplayBar] = []

    for row in joined.iter_rows(named=True):
        ts_ns = int(row['ts'])
        settle_ns = ts_ns if is_dollar else ts_ns + interval_ns

        if settle_ns < start_ns or settle_ns > end_ns:
            continue

        bars.append(
            ReplayBar(
                ts_ns=ts_ns,
                settle=datetime.fromtimestamp(settle_ns / _NS_PER_SECOND, tz=UTC),
                close=float(row['close']),
                prediction=int(row['prediction']),
                probability=float(row['probability']),
                start_ts_ns=int(row[_DOLLAR_OPEN_COLUMN]) if is_dollar else None,
            ),
        )

    return tuple(bars)
