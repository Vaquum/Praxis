'''Tests for `_register_wired_kline_sizes` (PT-FIX-1).

Replaces the broken `_extract_kline_sizes` (which read `_limen_manifest`
on raw `SensorSpec` objects from the manifest YAML — always `None`,
poller started empty, signals never had data). The new helper reads
from `WiredSensor.limen_manifest`, populated only after Limen
`Trainer(experiment_dir).train(...)` runs inside `StartupSequencer`.
'''

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from praxis.launcher import _register_wired_kline_sizes
from praxis.market_data_poller import MarketDataPoller


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
    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(poller, [])

    assert sizes == ()
    poller.add_kline_size.assert_not_called()


def test_registers_single_sensor_with_poller() -> None:
    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(
        poller,
        [_wired_sensor(kline_size=7200, interval_seconds=60)],
    )

    assert sizes == (7200,)
    poller.add_kline_size.assert_called_once_with(7200, 60)


def test_registers_multiple_distinct_kline_sizes_sorted_ascending() -> None:
    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(
        poller,
        [
            _wired_sensor(kline_size=14400, interval_seconds=120),
            _wired_sensor(kline_size=7200, interval_seconds=60),
            _wired_sensor(kline_size=3600, interval_seconds=30),
        ],
    )

    assert sizes == (3600, 7200, 14400)
    assert poller.add_kline_size.call_count == 3
    assert {c.args for c in poller.add_kline_size.call_args_list} == {
        (3600, 30),
        (7200, 60),
        (14400, 120),
    }


def test_duplicate_kline_size_registered_per_sensor_for_refcount() -> None:
    '''Each sensor with the same kline_size yields its own add_kline_size call.

    `MarketDataPoller.add_kline_size` is ref-counted internally, so
    repeated calls are correct. Returned tuple is deduplicated.
    '''

    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(
        poller,
        [
            _wired_sensor(kline_size=7200, interval_seconds=60),
            _wired_sensor(kline_size=7200, interval_seconds=60),
        ],
    )

    assert sizes == (7200,)
    assert poller.add_kline_size.call_count == 2


def test_skips_sensor_with_missing_limen_manifest() -> None:
    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(
        poller,
        [
            _wired_sensor(omit_limen_manifest=True),
            _wired_sensor(kline_size=7200, interval_seconds=60),
        ],
    )

    assert sizes == (7200,)
    poller.add_kline_size.assert_called_once_with(7200, 60)


def test_skips_sensor_with_missing_data_source_config() -> None:
    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(
        poller,
        [_wired_sensor(omit_data_source_config=True)],
    )

    assert sizes == ()
    poller.add_kline_size.assert_not_called()


def test_skips_sensor_with_missing_params() -> None:
    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(
        poller,
        [_wired_sensor(omit_params=True)],
    )

    assert sizes == ()
    poller.add_kline_size.assert_not_called()


def test_skips_sensor_with_missing_kline_size_key() -> None:
    poller = MagicMock(spec=MarketDataPoller)

    sizes = _register_wired_kline_sizes(
        poller,
        [_wired_sensor(kline_size=None)],
    )

    assert sizes == ()
    poller.add_kline_size.assert_not_called()


def test_one_bad_sensor_does_not_abort_remaining() -> None:
    '''Per-sensor parse exception logs a warning and skips that sensor only.'''

    poller = MagicMock(spec=MarketDataPoller)
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
        poller,
        [bad, _wired_sensor(kline_size=7200, interval_seconds=60)],
    )

    assert sizes == (7200,)
    poller.add_kline_size.assert_called_once_with(7200, 60)
