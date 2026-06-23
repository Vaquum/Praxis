from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path

import polars as pl

from praxis.replay.load_replay_bars import load_replay_bars

_NS = 1_000_000_000
_INTERVAL = 900


def _write(
    root: Path,
    series: str,
    ohlcv: dict[str, list[object]],
    ohlcv_schema: dict[str, object],
    predictions: dict[str, list[object]],
) -> tuple[Path, Path]:
    arrow_dir = root / 'arrow'
    conduit_dir = root / 'conduit'
    (arrow_dir / series).mkdir(parents=True)
    (conduit_dir / series).mkdir(parents=True)

    pl.DataFrame(ohlcv, schema=ohlcv_schema).write_ipc(
        arrow_dir / series / 'latest.arrow',
    )
    pl.DataFrame(
        predictions,
        schema={
            'ts': pl.Int64,
            'prediction': pl.Int64,
            'probability': pl.Float64,
            'reason_code': pl.Int64,
        },
    ).write_ipc(conduit_dir / series / 'latest.arrow')

    return arrow_dir, conduit_dir


def test_loads_time_bars_with_settle_offset(tmp_path: Path) -> None:
    opens = [1000 * _NS, 1900 * _NS, 2800 * _NS]
    arrow_dir, conduit_dir = _write(
        tmp_path,
        'time_15m',
        {'ts': opens, 'close': [60000.0, 61000.0, 62000.0]},
        {'ts': pl.Int64, 'close': pl.Float64},
        {
            'ts': opens,
            'prediction': [1, 0, 1],
            'probability': [0.9, 0.1, 0.8],
            'reason_code': [0, 0, 0],
        },
    )

    bars = load_replay_bars(
        arrow_dir=arrow_dir,
        conduit_dir=conduit_dir,
        series='time_15m',
        interval_seconds=_INTERVAL,
        start=datetime.fromtimestamp(0, tz=UTC),
        end=datetime.fromtimestamp(100000, tz=UTC),
    )

    assert len(bars) == 3
    assert bars[0].start_ts_ns is None
    assert bars[0].ts_ns == 1000 * _NS
    assert bars[0].settle == datetime.fromtimestamp(1000 + _INTERVAL, tz=UTC)
    assert bars[0].prediction == 1
    assert bars[0].close == 60000.0


def test_loads_dollar_bars_settle_is_ts(tmp_path: Path) -> None:
    settles = [5000 * _NS, 5433 * _NS]
    opens = [4600 * _NS, 5000 * _NS]
    arrow_dir, conduit_dir = _write(
        tmp_path,
        'dollar_60M',
        {'ts': settles, 'close': [60000.0, 61000.0], 'start_ts': opens},
        {'ts': pl.Int64, 'close': pl.Float64, 'start_ts': pl.Int64},
        {
            'ts': settles,
            'prediction': [1, 0],
            'probability': [0.9, 0.1],
            'reason_code': [0, 0],
        },
    )

    bars = load_replay_bars(
        arrow_dir=arrow_dir,
        conduit_dir=conduit_dir,
        series='dollar_60M',
        interval_seconds=300,
        start=datetime.fromtimestamp(0, tz=UTC),
        end=datetime.fromtimestamp(100000, tz=UTC),
    )

    assert len(bars) == 2
    assert bars[0].ts_ns == 5000 * _NS
    assert bars[0].start_ts_ns == 4600 * _NS
    assert bars[0].settle == datetime.fromtimestamp(5000, tz=UTC)


def test_skips_unusable_rows(tmp_path: Path) -> None:
    opens = [1000 * _NS, 1900 * _NS]
    arrow_dir, conduit_dir = _write(
        tmp_path,
        'time_15m',
        {'ts': opens, 'close': [60000.0, 61000.0]},
        {'ts': pl.Int64, 'close': pl.Float64},
        {
            'ts': opens,
            'prediction': [1, 1],
            'probability': [0.9, 0.9],
            'reason_code': [0, 7],
        },
    )

    bars = load_replay_bars(
        arrow_dir=arrow_dir,
        conduit_dir=conduit_dir,
        series='time_15m',
        interval_seconds=_INTERVAL,
        start=datetime.fromtimestamp(0, tz=UTC),
        end=datetime.fromtimestamp(100000, tz=UTC),
    )

    assert len(bars) == 1
    assert bars[0].ts_ns == 1000 * _NS


def test_range_filter_on_settle(tmp_path: Path) -> None:
    opens = [1000 * _NS, 1900 * _NS, 2800 * _NS]
    arrow_dir, conduit_dir = _write(
        tmp_path,
        'time_15m',
        {'ts': opens, 'close': [60000.0, 61000.0, 62000.0]},
        {'ts': pl.Int64, 'close': pl.Float64},
        {
            'ts': opens,
            'prediction': [1, 0, 1],
            'probability': [0.9, 0.1, 0.8],
            'reason_code': [0, 0, 0],
        },
    )

    bars = load_replay_bars(
        arrow_dir=arrow_dir,
        conduit_dir=conduit_dir,
        series='time_15m',
        interval_seconds=_INTERVAL,
        start=datetime.fromtimestamp(1900 + _INTERVAL, tz=UTC),
        end=datetime.fromtimestamp(1900 + _INTERVAL, tz=UTC),
    )

    assert len(bars) == 1
    assert bars[0].ts_ns == 1900 * _NS
