'''Write the Conduit/Arrow frames a replay step exposes to PredictLoop.

A replay run reproduces what Furnace and the control plane publish live:
per bar it writes the OHLCV frame, the prediction frame, and the serving
manifest into the run's conduit/arrow directories, then advances the
clock and calls `PredictLoop.tick_once`. `PredictLoop` reads these exact
artifacts (serving manifest -> prediction frame max-ts usable row ->
OHLCV close joined on `ts`), so materializing them is the whole data
contract a replay must satisfy.

Rows are cumulative: callers pass every bar up to and including the
current one, so `PredictLoop._latest_usable_row` selects the current bar
as the max-ts row and the OHLCV `ts` join and mark-price reads resolve.
'''

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import polars as pl

__all__ = ['materialize_bar_frames']

_MANIFEST_NAME = 'serving_manifest.json'
_LATEST_ARROW = 'latest.arrow'
_PREDICTIONS_ARROW = 'predictions.arrow'
_USABLE_REASON_CODE = 0


def materialize_bar_frames(
    *,
    conduit_dir: Path,
    arrow_dir: Path,
    series: str,
    generated_at: datetime,
    ohlcv_rows: list[tuple[int, float]],
    prediction_rows: list[tuple[int, int, float]],
    start_ts: list[int] | None = None,
) -> None:
    '''Write the OHLCV frame, prediction frame, and serving manifest.

    Args:
        conduit_dir: Run-local mount for the serving manifest and the
            per-series prediction frame.
        arrow_dir: Run-local mount for the per-series OHLCV frame.
        series: Series identifier, e.g. 'time_15m'.
        generated_at: Manifest freshness stamp; set to the current bar's
            settle so PredictLoop's staleness gate passes against the
            replay clock.
        ohlcv_rows: Cumulative `(ts_ns, close)` rows up to the current
            bar.
        prediction_rows: Cumulative `(ts_ns, prediction, probability)`
            rows up to the current bar; every row is marked usable.
        start_ts: Cumulative dollar-bar open `ts` values, aligned with
            `ohlcv_rows`. When provided the OHLCV frame carries a
            `start_ts` column, which marks the series as dollar-family
            (its `ts` is the settle); omit for time bars.
    '''

    series_arrow_dir = arrow_dir / series
    series_arrow_dir.mkdir(parents=True, exist_ok=True)

    ohlcv_columns: dict[str, list[int] | list[float]] = {
        'ts': [ts for ts, _ in ohlcv_rows],
        'close': [close for _, close in ohlcv_rows],
    }
    ohlcv_schema: dict[str, type[pl.DataType] | pl.DataType] = {
        'ts': pl.Int64,
        'close': pl.Float64,
    }

    if start_ts is not None:
        ohlcv_columns['start_ts'] = start_ts
        ohlcv_schema['start_ts'] = pl.Int64

    pl.DataFrame(ohlcv_columns, schema=ohlcv_schema).write_ipc(
        series_arrow_dir / _LATEST_ARROW,
    )

    series_conduit_dir = conduit_dir / series
    series_conduit_dir.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {
            'ts': [ts for ts, _, _ in prediction_rows],
            'prediction': [prediction for _, prediction, _ in prediction_rows],
            'probability': [probability for _, _, probability in prediction_rows],
            'reason_code': [_USABLE_REASON_CODE] * len(prediction_rows),
        },
        schema={
            'ts': pl.Int64,
            'prediction': pl.Int64,
            'probability': pl.Float64,
            'reason_code': pl.Int64,
        },
    ).write_ipc(series_conduit_dir / _PREDICTIONS_ARROW)

    manifest = {
        'generated_at': generated_at.isoformat(),
        'series': {series: {'path': f'{series}/{_PREDICTIONS_ARROW}'}},
    }
    (conduit_dir / _MANIFEST_NAME).write_text(json.dumps(manifest), encoding='utf-8')
