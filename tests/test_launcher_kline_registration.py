'''Tests for `_register_wired_kline_sizes` (PT-FIX-1).

Replaces the broken `_extract_kline_sizes` (which read `_limen_manifest`
on raw `SensorSpec` objects from the manifest YAML — always `None`,
poller started empty, signals never had data). The new helper reads
from `WiredSensor.limen_manifest`, populated only after Limen
`Trainer(experiment_dir).train(...)` runs inside `StartupSequencer`.

Post-cache-rewire (Praxis #108) the function no longer calls
`poller.add_kline_size` (cache is symbol-scoped, not per-kline_size).
The `poller` argument is accepted for backward-compat with existing
call sites and is otherwise unused; only the kline_size-collection
behavior is asserted here.
'''

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

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


def test_returns_empty_when_poller_is_none() -> None:
    sizes = _register_wired_kline_sizes(None, [_wired_sensor()])

    assert sizes == ()


def test_returns_empty_when_no_wired_sensors() -> None:
    sizes = _register_wired_kline_sizes(MagicMock(), [])

    assert sizes == ()


def test_collects_single_kline_size() -> None:
    sizes = _register_wired_kline_sizes(
        MagicMock(),
        [_wired_sensor(kline_size=7200, interval_seconds=60)],
    )

    assert sizes == (7200,)


def test_collects_distinct_kline_sizes_sorted_ascending() -> None:
    sizes = _register_wired_kline_sizes(
        MagicMock(),
        [
            _wired_sensor(kline_size=14400, interval_seconds=120),
            _wired_sensor(kline_size=7200, interval_seconds=60),
            _wired_sensor(kline_size=3600, interval_seconds=30),
        ],
    )

    assert sizes == (3600, 7200, 14400)


def test_duplicate_kline_size_collapsed_in_returned_tuple() -> None:
    '''Two sensors with the same kline_size produce one entry in the
    returned tuple (cache is symbol-scoped, no per-kline_size
    registration to refcount).
    '''

    sizes = _register_wired_kline_sizes(
        MagicMock(),
        [
            _wired_sensor(kline_size=7200, interval_seconds=60),
            _wired_sensor(kline_size=7200, interval_seconds=60),
        ],
    )

    assert sizes == (7200,)


def test_skips_sensor_with_missing_limen_manifest() -> None:
    sizes = _register_wired_kline_sizes(
        MagicMock(),
        [
            _wired_sensor(omit_limen_manifest=True),
            _wired_sensor(kline_size=7200, interval_seconds=60),
        ],
    )

    assert sizes == (7200,)


def test_skips_sensor_with_missing_data_source_config() -> None:
    sizes = _register_wired_kline_sizes(
        MagicMock(),
        [_wired_sensor(omit_data_source_config=True)],
    )

    assert sizes == ()


def test_skips_sensor_with_missing_params() -> None:
    sizes = _register_wired_kline_sizes(
        MagicMock(),
        [_wired_sensor(omit_params=True)],
    )

    assert sizes == ()


def test_skips_sensor_with_missing_kline_size_key() -> None:
    sizes = _register_wired_kline_sizes(
        MagicMock(),
        [_wired_sensor(kline_size=None)],
    )

    assert sizes == ()


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
        MagicMock(),
        [bad, _wired_sensor(kline_size=7200, interval_seconds=60)],
    )

    assert sizes == (7200,)
