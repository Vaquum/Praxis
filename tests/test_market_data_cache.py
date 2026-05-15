'''Tests for MainCache in praxis.market_data_cache.'''

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest

from praxis.market_data_cache import CacheScheduler, MainCache


_BASE_TS = datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC)


def _make_klines(start_ts: datetime, count: int) -> pl.DataFrame:

    '''Build a 17-column 1-min kline frame matching Limen's canonical shape.'''

    return pl.DataFrame({
        'datetime': [start_ts + timedelta(minutes=i) for i in range(count)],
        'open': [50000.0 + i for i in range(count)],
        'high': [50100.0 + i for i in range(count)],
        'low': [49900.0 + i for i in range(count)],
        'close': [50050.0 + i for i in range(count)],
        'mean': [50025.0 + i for i in range(count)],
        'std': [10.0] * count,
        'volume': [1.0] * count,
        'maker_ratio': [0.5] * count,
        'no_of_trades': [100] * count,
        'open_liquidity': [50.0] * count,
        'high_liquidity': [55.0] * count,
        'low_liquidity': [49.0] * count,
        'close_liquidity': [51.0] * count,
        'liquidity_sum': [205.0] * count,
        'maker_volume': [0.5] * count,
        'maker_liquidity': [102.5] * count,
    })


@pytest.fixture
def cache_paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / 'btcusdt_1m.parquet', tmp_path / 'main_cache_state.json'


def test_load_from_existing_disk_parquet(cache_paths: tuple[Path, Path]) -> None:
    '''`load()` reads an existing parquet into the in-memory frame.

    Pin: when a prior `refresh()` left a parquet on disk, a fresh
    `MainCache` instance + `load()` reproduces the same in-memory
    frame without any network call (no Limen import is touched).
    '''

    parquet_path, state_path = cache_paths
    expected = _make_klines(_BASE_TS, count=5)
    expected.write_parquet(parquet_path)

    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache.load()

    assert cache.frame.height == 5
    assert cache.frame['datetime'].to_list() == expected['datetime'].to_list()


def test_refresh_from_limen_first_boot_writes_full_snapshot(
    cache_paths: tuple[Path, Path],
) -> None:
    '''First-ever `refresh()` (sidecar absent) calls Limen with no
    `start_date_limit` and persists the returned frame to disk.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines(_BASE_TS, count=10)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = snapshot
        cache.refresh_from_limen()

    call_kwargs = mock_hd_cls.return_value.get_spot_klines.call_args.kwargs
    assert call_kwargs.get('start_date_limit') is None
    assert call_kwargs.get('kline_size') == 60

    assert parquet_path.exists()
    assert state_path.exists()
    on_disk = pl.read_parquet(parquet_path)
    assert on_disk.height == 10
    assert cache.frame.height == 10
    assert cache.last_covered_ts == snapshot['datetime'].max()


def test_refresh_from_limen_incremental_appends_only_new_bars(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Subsequent `refresh()` reads `last_covered_ts` from the state
    file and passes it as Limen's `start_date_limit`. Returned bars
    are appended to the existing on-disk frame and the state's
    high-water timestamp advances.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    initial = _make_klines(_BASE_TS, count=5)
    later = _make_klines(_BASE_TS.replace(minute=10), count=3)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.side_effect = [initial, later]
        cache.refresh_from_limen()
        cache.refresh_from_limen()

    second_call_kwargs = (
        mock_hd_cls.return_value.get_spot_klines.call_args_list[1].kwargs
    )
    assert second_call_kwargs.get('start_date_limit') is not None
    assert second_call_kwargs.get('start_date_limit') == (
        initial['datetime'].max().strftime('%Y-%m-%d %H:%M:%S')
    )
    assert cache.frame.height == 8
    assert cache.last_covered_ts == later['datetime'].max()


def test_refresh_from_limen_no_op_when_returns_empty(
    cache_paths: tuple[Path, Path],
) -> None:
    '''If Limen returns an empty frame (HF cron behind our daily
    fire), `refresh()` neither writes the parquet nor advances the
    state — leaves the prior on-disk artefacts untouched.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    initial = _make_klines(_BASE_TS, count=3)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.side_effect = [
            initial, pl.DataFrame(),
        ]
        cache.refresh_from_limen()
        first_state = json.loads(state_path.read_text())
        first_parquet_mtime = parquet_path.stat().st_mtime_ns
        cache.refresh_from_limen()

    second_state = json.loads(state_path.read_text())
    second_parquet_mtime = parquet_path.stat().st_mtime_ns

    assert first_state == second_state
    assert first_parquet_mtime == second_parquet_mtime


def test_bootstrap_if_empty_skips_when_disk_present(
    cache_paths: tuple[Path, Path],
) -> None:
    '''`bootstrap_if_empty()` is a no-op when the parquet already
    exists; only a missing parquet triggers the one-shot refresh.
    '''

    parquet_path, state_path = cache_paths
    _make_klines(_BASE_TS, count=2).write_parquet(parquet_path)

    cache = MainCache(MagicMock(), parquet_path, state_path)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        cache.bootstrap_if_empty()

    mock_hd_cls.assert_not_called()


def test_bootstrap_if_empty_refreshes_when_disk_missing(
    cache_paths: tuple[Path, Path],
) -> None:
    '''`bootstrap_if_empty()` triggers a `refresh()` when no parquet
    exists yet (covers the first-ever Praxis boot path so the cache
    is usable immediately, without waiting for the 05:00 UTC cron).
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines(_BASE_TS, count=4)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = snapshot
        cache.bootstrap_if_empty()

    mock_hd_cls.return_value.get_spot_klines.assert_called_once()
    assert parquet_path.exists()
    assert cache.frame.height == 4


def _make_klines_pandas(start_ts: datetime, count: int) -> pd.DataFrame:

    '''Build a 19-column 1-min kline frame in pandas, mimicking binancial.

    binancial.get_spot_klines returns the same canonical columns
    Limen does plus `median` and `iqr`. The MainCache binancial
    path drops those two so the merged shape stays 17 columns.
    '''

    return pd.DataFrame({
        'datetime': [start_ts + timedelta(minutes=i) for i in range(count)],
        'open': [50000.0 + i for i in range(count)],
        'high': [50100.0 + i for i in range(count)],
        'low': [49900.0 + i for i in range(count)],
        'close': [50050.0 + i for i in range(count)],
        'mean': [50025.0 + i for i in range(count)],
        'std': [10.0] * count,
        'median': [50025.0 + i for i in range(count)],
        'iqr': [5.0] * count,
        'volume': [1.0] * count,
        'maker_ratio': [0.5] * count,
        'no_of_trades': [100] * count,
        'open_liquidity': [50.0] * count,
        'high_liquidity': [55.0] * count,
        'low_liquidity': [49.0] * count,
        'close_liquidity': [51.0] * count,
        'liquidity_sum': [205.0] * count,
        'maker_volume': [0.5] * count,
        'maker_liquidity': [102.5] * count,
    })


def test_refresh_from_binancial_first_boot_uses_default_window(
    cache_paths: tuple[Path, Path],
) -> None:
    '''First-ever `refresh_from_binancial()` (state file absent)
    asks binancial for `now - 1h` to `now`, then writes the result.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines_pandas(_BASE_TS, count=4)

    fixed_now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC)

    with patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=snapshot,
    ) as mock_fetch, patch(
        'praxis.market_data_cache.datetime',
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now
        mock_dt.fromisoformat = datetime.fromisoformat
        cache.refresh_from_binancial()

    call_kwargs = mock_fetch.call_args.kwargs
    assert call_kwargs['start_date'] == (
        (fixed_now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    )
    assert call_kwargs['end_date'] == fixed_now.strftime('%Y-%m-%d %H:%M:%S')
    assert call_kwargs['kline_size'] == 60
    assert cache.frame.height == 4


def test_refresh_from_binancial_incremental_uses_last_covered_ts(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Subsequent `refresh_from_binancial()` reads the state's
    `last_covered_ts` and uses it as `start_date`.
    '''

    parquet_path, state_path = cache_paths
    state_path.write_text(json.dumps({
        'last_covered_ts': _BASE_TS.isoformat(),
    }))
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines_pandas(
        _BASE_TS + timedelta(minutes=1), count=2,
    )

    with patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=snapshot,
    ) as mock_fetch:
        cache.refresh_from_binancial()

    call_kwargs = mock_fetch.call_args.kwargs
    assert call_kwargs['start_date'] == _BASE_TS.strftime('%Y-%m-%d %H:%M:%S')


def test_refresh_from_binancial_drops_median_and_iqr_columns(
    cache_paths: tuple[Path, Path],
) -> None:
    '''binancial returns 19 columns including `median` and `iqr`;
    those two are dropped before append so the disk parquet retains
    Limen's 17-column shape.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines_pandas(_BASE_TS, count=3)
    assert 'median' in snapshot.columns
    assert 'iqr' in snapshot.columns

    with patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=snapshot,
    ):
        cache.refresh_from_binancial()

    assert 'median' not in cache.frame.columns
    assert 'iqr' not in cache.frame.columns
    assert cache.frame.width == 17


def test_refresh_from_binancial_wins_on_overlap_with_limen_bars(
    cache_paths: tuple[Path, Path],
) -> None:
    '''When binancial returns a bar at a `datetime` already present
    from a prior Limen refresh, the binancial bar wins (last-write
    on `unique(keep='last')`). Verifies that the per-minute trailing
    refresh supersedes the daily Limen bars on the overlap window.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    limen_bars = _make_klines(_BASE_TS, count=3)
    overlapping_pd = _make_klines_pandas(_BASE_TS, count=3)
    overlapping_pd['close'] = pd.Series([99999.0, 99999.0, 99999.0])

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = limen_bars
        cache.refresh_from_limen()

    assert cache.frame['close'].to_list() == [50050.0, 50051.0, 50052.0]

    with patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=overlapping_pd,
    ):
        cache.refresh_from_binancial()

    assert cache.frame.height == 3
    assert cache.frame['close'].to_list() == [99999.0, 99999.0, 99999.0]


def test_get_market_data_aggregates_5m_from_1m(
    cache_paths: tuple[Path, Path],
) -> None:
    '''`get_market_data(300)` aggregates 1-min bars into 5-min
    buckets. Pin: shape (height/12 buckets), datetime spacing
    (300s), open/high/low/close behave as first/max/min/last.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines(_BASE_TS, count=15)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = snapshot
        cache.refresh_from_limen()

    aggregated = cache.get_market_data(300)

    assert aggregated.height == 3
    assert aggregated['datetime'].to_list() == [
        _BASE_TS,
        _BASE_TS + timedelta(minutes=5),
        _BASE_TS + timedelta(minutes=10),
    ]
    assert aggregated['open'].to_list() == [50000.0, 50005.0, 50010.0]
    assert aggregated['close'].to_list() == [50054.0, 50059.0, 50064.0]


def test_concurrent_refreshes_do_not_corrupt_disk(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: `_write_lock` serializes the two refresh paths so a
    Limen refresh + binancial refresh firing simultaneously cannot
    leave the disk parquet inconsistent with the state file. Both
    paths run via real threads; afterward the on-disk parquet's
    bar count must match the state's `last_covered_ts` (i.e. no
    in-flight reorder lost a write).
    '''

    import threading as _threading

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    limen_bars = _make_klines(_BASE_TS, count=10)
    binancial_bars = _make_klines_pandas(
        _BASE_TS + timedelta(minutes=10), count=5,
    )

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls, patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=binancial_bars,
    ):
        mock_hd_cls.return_value.get_spot_klines.return_value = limen_bars

        t_limen = _threading.Thread(target=cache.refresh_from_limen)
        t_binancial = _threading.Thread(target=cache.refresh_from_binancial)
        t_limen.start()
        t_binancial.start()
        t_limen.join(timeout=10)
        t_binancial.join(timeout=10)

    assert not t_limen.is_alive()
    assert not t_binancial.is_alive()

    on_disk = pl.read_parquet(parquet_path)
    state = json.loads(state_path.read_text())
    expected_last = on_disk['datetime'].max()
    assert state['last_covered_ts'] == expected_last.isoformat()
    assert on_disk.height == 15


def test_scheduler_starts_both_threads(
    cache_paths: tuple[Path, Path],
) -> None:
    '''start() spawns two named daemon threads (limen + binancial).'''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache.refresh_from_binancial = MagicMock(return_value=None)
    cache.refresh_from_limen = MagicMock(return_value=None)

    scheduler = CacheScheduler(
        cache,
        binancial_interval_seconds=10.0,
        limen_schedule_fn=lambda: 10.0,
    )
    scheduler.start()
    try:
        assert scheduler._limen_thread is not None
        assert scheduler._binancial_thread is not None
        assert scheduler._limen_thread.is_alive()
        assert scheduler._binancial_thread.is_alive()
        assert scheduler._limen_thread.daemon is True
        assert scheduler._binancial_thread.daemon is True
        assert scheduler._limen_thread.name == 'cache-scheduler-limen'
        assert scheduler._binancial_thread.name == 'cache-scheduler-binancial'
    finally:
        scheduler.stop(timeout_seconds=2.0)


def test_scheduler_stops_cleanly_on_stop_event(
    cache_paths: tuple[Path, Path],
) -> None:
    '''stop() sets the stop event and both threads exit promptly.'''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache.refresh_from_binancial = MagicMock(return_value=None)
    cache.refresh_from_limen = MagicMock(return_value=None)

    scheduler = CacheScheduler(
        cache,
        binancial_interval_seconds=10.0,
        limen_schedule_fn=lambda: 10.0,
    )
    scheduler.start()
    limen_thread = scheduler._limen_thread
    binancial_thread = scheduler._binancial_thread

    scheduler.stop(timeout_seconds=2.0)

    assert limen_thread is not None
    assert binancial_thread is not None
    assert not limen_thread.is_alive()
    assert not binancial_thread.is_alive()
    assert scheduler._limen_thread is None
    assert scheduler._binancial_thread is None


def test_limen_refresh_exception_does_not_kill_thread(
    cache_paths: tuple[Path, Path],
) -> None:
    '''A raising refresh_from_limen logs at exception level and the
    thread keeps looping; the next tick fires normally.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    fire_count = threading.Event()
    calls = {'n': 0}

    def _flaky() -> None:
        calls['n'] += 1
        if calls['n'] == 1:
            raise RuntimeError('synthetic limen failure')
        fire_count.set()

    cache.refresh_from_limen = _flaky
    cache.refresh_from_binancial = MagicMock(return_value=None)

    scheduler = CacheScheduler(
        cache,
        binancial_interval_seconds=60.0,
        limen_schedule_fn=lambda: 0.01,
    )
    scheduler.start()
    try:
        assert fire_count.wait(timeout=2.0), 'limen thread did not survive the exception'
        assert calls['n'] >= 2
    finally:
        scheduler.stop(timeout_seconds=2.0)


def test_binancial_refresh_exception_does_not_kill_thread(
    cache_paths: tuple[Path, Path],
) -> None:
    '''A raising refresh_from_binancial logs at exception level and
    the thread keeps looping; the next tick fires normally.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    fire_count = threading.Event()
    calls = {'n': 0}

    def _flaky() -> None:
        calls['n'] += 1
        if calls['n'] == 1:
            raise RuntimeError('synthetic binancial failure')
        fire_count.set()

    cache.refresh_from_binancial = _flaky
    cache.refresh_from_limen = MagicMock(return_value=None)

    scheduler = CacheScheduler(
        cache,
        binancial_interval_seconds=0.01,
        limen_schedule_fn=lambda: 60.0,
    )
    scheduler.start()
    try:
        assert fire_count.wait(timeout=2.0), 'binancial thread did not survive the exception'
        assert calls['n'] >= 2
    finally:
        scheduler.stop(timeout_seconds=2.0)
