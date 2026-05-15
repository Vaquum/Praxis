'''Tests for `_register_wired_kline_sizes` (PT-FIX-1).

Replaces the broken `_extract_kline_sizes` (which read `_limen_manifest`
on raw `SensorSpec` objects from the manifest YAML — always `None`,
poller started empty, signals never had data). The new helper reads
from `WiredSensor.limen_manifest`, populated only after Limen
`Trainer(experiment_dir).train(...)` runs inside `StartupSequencer`.

Post-cache-rewire (Praxis #108) the function only collects + returns
the kline_sizes (no `poller.add_kline_size` call); the cache is
symbol-scoped so per-kline_size registration is gone.
'''

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from praxis.launcher import _register_wired_kline_sizes


def _wired_sensor(
    *,
    kline_size: int | None = 7200,
    interval_seconds: int = 60,
    omit_data_source_config: bool = False,
    omit_params: bool = False,
    omit_limen_manifest: bool = False,
) -> SimpleNamespace:
    if omit_limen_manifest:
        limen_manifest = None
    elif omit_data_source_config:
        limen_manifest = SimpleNamespace(data_source_config=None)
    elif omit_params:
        limen_manifest = SimpleNamespace(
            data_source_config=SimpleNamespace(params=None),
        )
    else:
        params: dict[str, int] = {}

        if kline_size is not None:
            params['kline_size'] = kline_size

        limen_manifest = SimpleNamespace(
            data_source_config=SimpleNamespace(params=params),
        )

    return SimpleNamespace(
        sensor_id='strat_a:sensor_0',
        sensor=MagicMock(),
        limen_manifest=limen_manifest,
        round_params={},
        strategy_id='strat_a',
        interval_seconds=interval_seconds,
    )


def test_returns_empty_when_no_wired_sensors() -> None:
    sizes = _register_wired_kline_sizes([])

    assert sizes == ()


def test_collects_single_kline_size() -> None:
    sizes = _register_wired_kline_sizes(
        [_wired_sensor(kline_size=7200, interval_seconds=60)],
    )

    assert sizes == (7200,)


def test_collects_distinct_kline_sizes_sorted_ascending() -> None:
    sizes = _register_wired_kline_sizes([
        _wired_sensor(kline_size=14400, interval_seconds=120),
        _wired_sensor(kline_size=7200, interval_seconds=60),
        _wired_sensor(kline_size=3600, interval_seconds=30),
    ])

    assert sizes == (3600, 7200, 14400)


def test_duplicate_kline_size_collapsed_in_returned_tuple() -> None:
    '''Two sensors with the same kline_size produce one entry in the
    returned tuple (cache is symbol-scoped, no per-kline_size
    registration to refcount).
    '''

    sizes = _register_wired_kline_sizes([
        _wired_sensor(kline_size=7200, interval_seconds=60),
        _wired_sensor(kline_size=7200, interval_seconds=60),
    ])

    assert sizes == (7200,)


def test_skips_sensor_with_missing_limen_manifest() -> None:
    sizes = _register_wired_kline_sizes([
        _wired_sensor(omit_limen_manifest=True),
        _wired_sensor(kline_size=7200, interval_seconds=60),
    ])

    assert sizes == (7200,)


def test_skips_sensor_with_missing_data_source_config() -> None:
    sizes = _register_wired_kline_sizes(
        [_wired_sensor(omit_data_source_config=True)],
    )

    assert sizes == ()


def test_skips_sensor_with_missing_params() -> None:
    sizes = _register_wired_kline_sizes(
        [_wired_sensor(omit_params=True)],
    )

    assert sizes == ()


def test_skips_sensor_with_missing_kline_size_key() -> None:
    sizes = _register_wired_kline_sizes(
        [_wired_sensor(kline_size=None)],
    )

    assert sizes == ()


def test_skips_zero_kline_size() -> None:
    '''`kline_size == 0` is invalid (cannot fetch a 0-second bar) and
    is skipped by the `<= 0` half of the guard.
    '''

    sizes = _register_wired_kline_sizes(
        [_wired_sensor(kline_size=0)],
    )

    assert sizes == ()


def test_skips_negative_kline_size() -> None:
    '''Negative `kline_size` is rejected by the `<= 0` half of the guard.
    '''

    sizes = _register_wired_kline_sizes(
        [_wired_sensor(kline_size=-60)],
    )

    assert sizes == ()


def test_skips_kline_size_not_multiple_of_60() -> None:
    '''Positive `kline_size` that is not a multiple of 60 is rejected
    by the `% 60 != 0` half of the guard (the cache only stores 1-min
    base bars and only aggregates up to multiples of 60).
    '''

    sizes = _register_wired_kline_sizes(
        [_wired_sensor(kline_size=59)],
    )

    assert sizes == ()


def test_warning_messages_distinguish_non_positive_from_non_multiple(
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''The two halves of the guard log distinct messages so operators
    can tell whether the offending `kline_size` was non-positive or
    just not a multiple of 60.
    '''

    with caplog.at_level('WARNING', logger='praxis.launcher'):
        _register_wired_kline_sizes([
            _wired_sensor(kline_size=-60),
            _wired_sensor(kline_size=59),
        ])

    messages = [record.message for record in caplog.records]
    assert any('non-positive kline_size' in m for m in messages)
    assert any('non-multiple-of-60 kline_size' in m for m in messages)


def test_invalid_kline_size_does_not_drop_other_valid_sensors() -> None:
    '''A bad `kline_size` is skipped without aborting the function;
    valid sizes from other sensors are still returned.
    '''

    sizes = _register_wired_kline_sizes([
        _wired_sensor(kline_size=59, interval_seconds=30),
        _wired_sensor(kline_size=7200, interval_seconds=60),
        _wired_sensor(kline_size=-60, interval_seconds=30),
        _wired_sensor(kline_size=3600, interval_seconds=30),
    ])

    assert sizes == (3600, 7200)


def test_one_bad_sensor_does_not_abort_remaining() -> None:
    '''Per-sensor parse exception logs a warning and skips that sensor only.'''

    bad = SimpleNamespace(
        sensor_id='strat_x:sensor_0',
        limen_manifest=SimpleNamespace(
            data_source_config=SimpleNamespace(
                params=SimpleNamespace(get=lambda _k: 'not-an-int'),
            ),
        ),
        interval_seconds=60,
    )

    sizes = _register_wired_kline_sizes(
        [bad, _wired_sensor(kline_size=7200, interval_seconds=60)],
    )

    assert sizes == (7200,)
