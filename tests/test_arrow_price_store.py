from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path

import polars as pl

from praxis.arrow_price_store import ArrowPriceStore

_SERIES = 'time_15m'
_INTERVAL = 900
_NS = 1_000_000_000


def _now() -> datetime:
    return datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)


def _now_ns() -> int:
    return int(_now().timestamp() * _NS)


def _clock() -> datetime:
    return _now()


def _write_frame(root: Path, rows: list[dict[str, object]], *, series: str = _SERIES) -> None:
    frame = pl.DataFrame(rows, schema={'ts': pl.Int64, 'close': pl.Float64})
    series_dir = root / series
    series_dir.mkdir(parents=True, exist_ok=True)
    frame.write_ipc(series_dir / 'latest.arrow')


def test_returns_latest_closed_bar_close(tmp_path: Path) -> None:
    closed_old = _now_ns() - 1800 * _NS
    closed_recent = _now_ns() - 1000 * _NS
    forming = _now_ns() - 100 * _NS
    _write_frame(
        tmp_path,
        [
            {'ts': closed_old, 'close': 60000.0},
            {'ts': closed_recent, 'close': 64000.0},
            {'ts': forming, 'close': 99999.0},
        ],
    )

    store = ArrowPriceStore(tmp_path, clock=_clock)

    assert store.latest_close(_SERIES, _INTERVAL) == Decimal('64000.0')


def test_excludes_still_forming_bar(tmp_path: Path) -> None:
    forming = _now_ns() - 100 * _NS
    _write_frame(tmp_path, [{'ts': forming, 'close': 99999.0}])

    store = ArrowPriceStore(tmp_path, clock=_clock)

    assert store.latest_close(_SERIES, _INTERVAL) is None


def test_missing_file_returns_none(tmp_path: Path) -> None:
    store = ArrowPriceStore(tmp_path, clock=_clock)

    assert store.latest_close(_SERIES, _INTERVAL) is None


def test_empty_frame_returns_none(tmp_path: Path) -> None:
    _write_frame(tmp_path, [])

    store = ArrowPriceStore(tmp_path, clock=_clock)

    assert store.latest_close(_SERIES, _INTERVAL) is None


def test_non_finite_close_returns_none(tmp_path: Path) -> None:
    closed = _now_ns() - 1000 * _NS
    _write_frame(tmp_path, [{'ts': closed, 'close': float('nan')}])

    store = ArrowPriceStore(tmp_path, clock=_clock)

    assert store.latest_close(_SERIES, _INTERVAL) is None


def test_returns_decimal_type(tmp_path: Path) -> None:
    closed = _now_ns() - 1000 * _NS
    _write_frame(tmp_path, [{'ts': closed, 'close': 63821.99}])

    store = ArrowPriceStore(tmp_path, clock=_clock)
    result = store.latest_close(_SERIES, _INTERVAL)

    assert isinstance(result, Decimal)
    assert result == Decimal('63821.99')
