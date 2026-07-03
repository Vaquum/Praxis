import json
import math
from datetime import datetime
from pathlib import Path

import pytest

from praxis.metrics.limen_snapshot import LIMEN_SNAPSHOT_METRIC_NAMES, limen_snapshot

_FIXTURE = Path(__file__).parent / 'fixtures' / 'limen_snapshot_golden.json'


def _keys() -> list[str]:
    keys = []
    for name in LIMEN_SNAPSHOT_METRIC_NAMES:
        if name == 'cvar_95_return_bps':
            keys.append(name)
        else:
            keys.extend(f'{name}_{q}' for q in ('p5', 'p50', 'p95'))
    return keys


def _equal(actual: float | None, expected: float | None) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    if math.isinf(expected) or math.isinf(actual):
        return actual == expected
    return math.isclose(actual, expected, abs_tol=1e-06)


def test_port_matches_real_limen_golden_fixtures():
    scenarios = json.loads(_FIXTURE.read_text())

    for name, case in scenarios.items():
        payload = case['input']
        datetimes = [datetime.fromisoformat(value) for value in payload['datetime']]
        result = limen_snapshot(
            payload['predictions'], payload['open'], payload['close'],
            payload['price_change'], datetimes, **case['params'],
        )

        for key in _keys():
            assert _equal(result[key], case['expected'][key]), (
                f'{name}:{key} port={result[key]} limen={case["expected"][key]}'
            )


def _bars(
    preds: list[float], open_: list[float], close: list[float], dpx: list[float],
) -> tuple[list[float], list[float], list[float], list[float], list[datetime]]:
    dt = [datetime.fromisoformat(f'2026-01-0{i + 1}T00:00:00+00:00') for i in range(len(preds))]
    return preds, open_, close, dpx, dt


def test_empty_series_raises():
    with pytest.raises(ValueError, match='at least one bar'):
        limen_snapshot([], [], [], [], [])


def test_negative_lag_raises():
    with pytest.raises(ValueError, match='execution_lag_bars'):
        limen_snapshot(*_bars([1, 1], [100, 100], [101, 101], [1, 1]), execution_lag_bars=-1)


def test_non_binary_prediction_raises():
    with pytest.raises(ValueError, match='0 or 1'):
        limen_snapshot(*_bars([1, 2], [100, 100], [101, 101], [1, 1]))


def test_nan_prediction_raises():
    with pytest.raises(ValueError, match='0 or 1'):
        limen_snapshot(*_bars([1, float('nan')], [100, 100], [101, 101], [1, 1]))


def test_price_change_mismatch_raises():
    with pytest.raises(ValueError, match='close - open'):
        limen_snapshot(*_bars([1, 1], [100, 100], [101, 101], [1, 5]))


def test_infinite_price_raises():
    with pytest.raises(ValueError, match='close - open'):
        limen_snapshot(*_bars([1, 1], [float('inf'), 100], [float('inf'), 101], [0, 1]))


def test_non_datetime_timestamp_raises():
    dt = [datetime.fromisoformat('2026-01-01T00:00:00+00:00'), None]
    with pytest.raises(ValueError, match='timezone-aware'):
        limen_snapshot([1, 1], [100, 100], [101, 101], [1, 1], dt)


def test_naive_timestamp_rejected():
    dt = [datetime(2026, 1, 1), datetime(2026, 1, 1, 1)]
    with pytest.raises(ValueError, match='timezone-aware'):
        limen_snapshot([1, 1], [100, 100], [101, 101], [1, 1], dt)


def test_mismatched_lengths_raise():
    dt = [datetime.fromisoformat('2026-01-01T00:00:00+00:00')]
    with pytest.raises(ValueError, match='same length'):
        limen_snapshot([1, 1], [100, 100], [101, 101], [1, 1], dt)
