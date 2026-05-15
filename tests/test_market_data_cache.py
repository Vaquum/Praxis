'''Tests for MainCache in praxis.market_data_cache.'''

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from praxis.market_data_cache import MainCache


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

    cache = MainCache(parquet_path, state_path)
    cache.load()

    assert cache.frame.height == 5
    assert cache.frame['datetime'].to_list() == expected['datetime'].to_list()


def test_refresh_first_boot_writes_full_snapshot(
    cache_paths: tuple[Path, Path],
) -> None:
    '''First-ever `refresh()` (sidecar absent) calls Limen with no
    `start_date_limit` and persists the returned frame to disk.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(parquet_path, state_path)
    snapshot = _make_klines(_BASE_TS, count=10)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = snapshot
        cache.refresh()

    call_kwargs = mock_hd_cls.return_value.get_spot_klines.call_args.kwargs
    assert call_kwargs.get('start_date_limit') is None
    assert call_kwargs.get('kline_size') == 60

    assert parquet_path.exists()
    assert state_path.exists()
    on_disk = pl.read_parquet(parquet_path)
    assert on_disk.height == 10
    assert cache.frame.height == 10
    assert cache.last_covered_ts == snapshot['datetime'].max()


def test_refresh_incremental_appends_only_new_bars(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Subsequent `refresh()` reads `last_covered_ts` from the state
    file and passes it as Limen's `start_date_limit`. Returned bars
    are appended to the existing on-disk frame and the state's
    high-water timestamp advances.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(parquet_path, state_path)
    initial = _make_klines(_BASE_TS, count=5)
    later = _make_klines(_BASE_TS.replace(minute=10), count=3)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.side_effect = [initial, later]
        cache.refresh()
        cache.refresh()

    second_call_kwargs = (
        mock_hd_cls.return_value.get_spot_klines.call_args_list[1].kwargs
    )
    assert second_call_kwargs.get('start_date_limit') is not None
    assert second_call_kwargs.get('start_date_limit') == (
        initial['datetime'].max().strftime('%Y-%m-%d %H:%M:%S')
    )
    assert cache.frame.height == 8
    assert cache.last_covered_ts == later['datetime'].max()


def test_refresh_no_op_when_limen_returns_empty(
    cache_paths: tuple[Path, Path],
) -> None:
    '''If Limen returns an empty frame (HF cron behind our daily
    fire), `refresh()` neither writes the parquet nor advances the
    state — leaves the prior on-disk artefacts untouched.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(parquet_path, state_path)
    initial = _make_klines(_BASE_TS, count=3)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.side_effect = [
            initial, pl.DataFrame(),
        ]
        cache.refresh()
        first_state = json.loads(state_path.read_text())
        first_parquet_mtime = parquet_path.stat().st_mtime_ns
        cache.refresh()

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

    cache = MainCache(parquet_path, state_path)

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
    cache = MainCache(parquet_path, state_path)
    snapshot = _make_klines(_BASE_TS, count=4)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = snapshot
        cache.bootstrap_if_empty()

    mock_hd_cls.return_value.get_spot_klines.assert_called_once()
    assert parquet_path.exists()
    assert cache.frame.height == 4
