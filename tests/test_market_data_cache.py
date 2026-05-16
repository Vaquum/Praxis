'''Tests for MainCache in praxis.market_data_cache.'''

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest

from praxis.market_data_cache import CacheScheduler, MainCache
from tests.conftest import make_canonical_klines as _make_klines


_BASE_TS = datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC)


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
    fixed_now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC)
    snapshot = _make_klines_pandas(
        fixed_now - timedelta(minutes=4), count=4,
    )

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


def test_last_covered_ts_returns_none_on_corrupt_state_file(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''Corrupt state file is treated as absent so refresh paths
    self-heal instead of permanently breaking. Pin: truncated JSON
    on disk yields `None` from `last_covered_ts` and a warning is
    logged with the path that failed to parse.
    '''

    parquet_path, state_path = cache_paths
    state_path.write_text('{"last_covered_ts": "2026-05-')
    cache = MainCache(MagicMock(), parquet_path, state_path)

    with caplog.at_level('WARNING', logger='praxis.market_data_cache'):
        result = cache.last_covered_ts

    assert result is None
    assert any(
        'state file unreadable or corrupt' in record.message
        and str(state_path) in str(record.__dict__.get('main_cache_state_path', ''))
        for record in caplog.records
    )


def test_last_covered_ts_normalizes_naive_iso_to_utc(
    cache_paths: tuple[Path, Path],
) -> None:
    '''A naive ISO string on disk is assumed to be UTC and returned
    as an aware UTC datetime so the downstream `last_covered_ts >= now`
    check in `refresh_from_binancial` (where `now` is aware UTC)
    never raises naive-vs-aware `TypeError`.
    '''

    parquet_path, state_path = cache_paths
    state_path.write_text(json.dumps({
        'last_covered_ts': '2026-05-15T12:00:00',
    }))
    cache = MainCache(MagicMock(), parquet_path, state_path)

    result = cache.last_covered_ts

    assert result == datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC)
    assert result is not None
    assert result.tzinfo is UTC


def test_last_covered_ts_converts_non_utc_aware_to_utc(
    cache_paths: tuple[Path, Path],
) -> None:
    '''An aware ISO string in a non-UTC offset is converted to UTC.
    '''

    parquet_path, state_path = cache_paths
    state_path.write_text(json.dumps({
        'last_covered_ts': '2026-05-15T14:00:00+02:00',
    }))
    cache = MainCache(MagicMock(), parquet_path, state_path)

    result = cache.last_covered_ts

    assert result == datetime(2026, 5, 15, 12, 0, 0, tzinfo=UTC)
    assert result is not None
    assert result.utcoffset() == timedelta(0)


def test_apply_new_bars_does_not_re_read_parquet(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: `_apply_new_bars` no longer calls `pl.read_parquet` on
    every refresh. Pre-fix the merge re-loaded the entire on-disk
    parquet under `_write_lock` on every tick, scaling per-refresh
    I/O as O(size_of_cache); post-fix the in-memory `_frame` is the
    source of truth during merge so per-minute refreshes are O(new
    bars), not O(whole cache).
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot_pd = _make_klines_pandas(_BASE_TS, count=3)

    with (
        patch(
            'praxis.market_data_cache.get_spot_klines',
            return_value=snapshot_pd,
        ),
        patch(
            'praxis.market_data_cache.pl.read_parquet',
        ) as mock_read,
    ):
        cache.refresh_from_binancial()
        cache.refresh_from_binancial()
        cache.refresh_from_binancial()

    assert mock_read.call_count == 0


def test_snapshot_returns_aggregated_frame_and_latest_ts_atomically(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: `MainCache.snapshot` derives both pieces from a single
    `_frame` reference captured at call entry. Verified by
    asserting the returned `latest` matches the source frame's max
    `datetime` and the aggregated frame matches what
    `get_market_data` returns for the same kline_size.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    bars = _make_klines(_BASE_TS, count=10)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = bars
        cache.refresh_from_limen()

    aggregated, latest = cache.snapshot(60)

    assert latest == bars['datetime'].max()
    assert latest is not None
    assert latest.utcoffset() == timedelta(0)
    assert aggregated.height == cache.get_market_data(60).height


def test_snapshot_returns_empty_and_none_when_cache_unpopulated(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Empty in-memory frame yields `(empty_frame, None)`.'''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    aggregated, latest = cache.snapshot(60)

    assert aggregated.is_empty()
    assert latest is None


def test_snapshot_validates_kline_size(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Same `kline_size` validation as `get_market_data`.'''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    with pytest.raises(ValueError, match='positive multiple'):
        cache.snapshot(0)

    with pytest.raises(ValueError, match='positive multiple'):
        cache.snapshot(59)


def test_load_quarantines_corrupt_parquet_and_resets_frame(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''A corrupt on-disk parquet does not loop the scheduler forever.
    `load()` catches the read error, renames the corrupt parquet (and
    state) to `*.corrupt-<UTC-iso>` so the bad bytes are kept for
    forensics, resets the in-memory frame to empty, and logs a
    warning. The next refresh through `_apply_new_bars` then writes
    a fresh parquet from the freshly-fetched bars, self-healing
    without manual intervention.
    '''

    parquet_path, state_path = cache_paths
    parquet_path.write_bytes(b'not a parquet')
    state_path.write_text(json.dumps({
        'last_covered_ts': _BASE_TS.isoformat(),
    }))
    cache = MainCache(MagicMock(), parquet_path, state_path)

    with caplog.at_level('WARNING', logger='praxis.market_data_cache'):
        cache.load()

    assert cache.frame.is_empty()
    assert not parquet_path.exists()
    assert not state_path.exists()
    quarantined_parquet = list(parquet_path.parent.glob(
        f'{parquet_path.name}.corrupt-*',
    ))
    quarantined_state = list(state_path.parent.glob(
        f'{state_path.name}.corrupt-*',
    ))
    assert len(quarantined_parquet) == 1
    assert len(quarantined_state) == 1
    assert any(
        'parquet unreadable' in record.message
        for record in caplog.records
    )


def test_refresh_after_corrupt_parquet_self_heals(
    cache_paths: tuple[Path, Path],
) -> None:
    '''End-to-end self-heal: corrupt parquet on disk, then a
    `refresh_from_binancial()` call replaces it with a fresh one and
    the in-memory frame contains the new bars (no manual intervention).
    '''

    parquet_path, state_path = cache_paths
    parquet_path.write_bytes(b'not a parquet')
    cache = MainCache(MagicMock(), parquet_path, state_path)
    snapshot = _make_klines_pandas(_BASE_TS, count=3)

    with patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=snapshot,
    ):
        cache.refresh_from_binancial()

    assert cache.frame.height == 3
    assert parquet_path.exists()
    assert state_path.exists()


def test_last_covered_ts_returns_none_when_state_is_not_an_object(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''State file with valid JSON of the wrong shape (e.g. a list at
    the top level) is treated as corrupt so the cache self-heals
    instead of raising `AttributeError` on the missing `.get`.
    '''

    parquet_path, state_path = cache_paths
    state_path.write_text(json.dumps([]))
    cache = MainCache(MagicMock(), parquet_path, state_path)

    with caplog.at_level('WARNING', logger='praxis.market_data_cache'):
        result = cache.last_covered_ts

    assert result is None
    assert any(
        'state file unreadable or corrupt' in record.message
        for record in caplog.records
    )


def test_last_covered_ts_returns_none_when_value_is_not_a_string(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''State file where `last_covered_ts` is a non-string value
    (e.g. a number) is treated as corrupt so the cache self-heals
    instead of raising `TypeError` on `datetime.fromisoformat`.
    '''

    parquet_path, state_path = cache_paths
    state_path.write_text(json.dumps({'last_covered_ts': 1234567890}))
    cache = MainCache(MagicMock(), parquet_path, state_path)

    with caplog.at_level('WARNING', logger='praxis.market_data_cache'):
        result = cache.last_covered_ts

    assert result is None


def test_last_covered_ts_returns_none_on_invalid_iso_timestamp(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''Valid JSON but unparseable `last_covered_ts` value is also
    treated as absent so the cache self-heals.
    '''

    parquet_path, state_path = cache_paths
    state_path.write_text(json.dumps({'last_covered_ts': 'not-a-timestamp'}))
    cache = MainCache(MagicMock(), parquet_path, state_path)

    with caplog.at_level('WARNING', logger='praxis.market_data_cache'):
        result = cache.last_covered_ts

    assert result is None


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


def test_limen_cannot_overwrite_binancial_bars_on_overlap(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin the contract: binancial wins on overlap with Limen
    regardless of refresh order. The reverse-order scenario
    (binancial first, then Limen) breaks pre-fix because the
    blanket `keep='last'` dedup would let a re-fetched Limen
    snapshot overwrite freshly-written binancial bars at the
    boundary (the realistic trigger is a corrupt state file →
    full Limen re-fetch on the next 05:00 UTC tick while
    binancial has already populated the trailing minutes).
    Post-fix the source-aware dedup uses `keep='first'` for
    Limen so existing binancial rows in `_frame` win.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    binancial_pd = _make_klines_pandas(_BASE_TS, count=3)
    binancial_pd['close'] = pd.Series([99999.0, 99999.0, 99999.0])

    with patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=binancial_pd,
    ):
        cache.refresh_from_binancial()

    assert cache.frame['close'].to_list() == [99999.0, 99999.0, 99999.0]

    overlapping_limen = _make_klines(_BASE_TS, count=3)

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls:
        mock_hd_cls.return_value.get_spot_klines.return_value = overlapping_limen
        cache.refresh_from_limen()

    assert cache.frame.height == 3
    assert cache.frame['close'].to_list() == [99999.0, 99999.0, 99999.0]


def test_refresh_from_binancial_uses_frame_max_when_state_missing(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: when the parquet was loaded into `_frame` but the state
    file is missing (operator deleted it, partial atomic write,
    etc.), `refresh_from_binancial` must use the in-memory frame's
    max `datetime` as the window start — NOT `now - 1h`. The naive
    fallback would create a multi-hour gap between the newest
    on-disk bar and the new fetch window.
    '''

    parquet_path, state_path = cache_paths
    older_bars = _make_klines(
        _BASE_TS - timedelta(hours=8),
        count=5,
    )
    older_bars.write_parquet(parquet_path)
    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache.load()
    assert not state_path.exists()
    assert not cache.frame.is_empty()

    snapshot_pd = _make_klines_pandas(_BASE_TS, count=3)

    with patch(
        'praxis.market_data_cache.get_spot_klines',
        return_value=snapshot_pd,
    ) as mock_fetch:
        cache.refresh_from_binancial()

    call_kwargs = mock_fetch.call_args.kwargs
    expected_start_ts = older_bars['datetime'].max()
    expected_start = expected_start_ts.strftime('%Y-%m-%d %H:%M:%S')
    assert call_kwargs['start_date'] == expected_start
    assert state_path.exists()


def test_refresh_from_binancial_self_heals_on_future_state_ts(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''Pin: a future `last_covered_ts` on disk (clock skew, manual
    edit) is treated as corrupt and the refresh proceeds with the
    in-memory frame max as fallback. Pre-fix the method just logged
    and returned, so every subsequent refresh kept skipping and the
    cache stayed stale until manual intervention.
    '''

    parquet_path, state_path = cache_paths
    older_bars = _make_klines(
        datetime.now(tz=UTC) - timedelta(hours=4),
        count=5,
    )
    older_bars.write_parquet(parquet_path)
    future_ts = datetime.now(tz=UTC) + timedelta(days=1)
    state_path.write_text(json.dumps({
        'last_covered_ts': future_ts.isoformat(),
    }))

    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache.load()
    snapshot_pd = _make_klines_pandas(
        datetime.now(tz=UTC) - timedelta(minutes=2),
        count=2,
    )

    with (
        patch(
            'praxis.market_data_cache.get_spot_klines',
            return_value=snapshot_pd,
        ) as mock_fetch,
        caplog.at_level('WARNING', logger='praxis.market_data_cache'),
    ):
        cache.refresh_from_binancial()

    mock_fetch.assert_called_once()
    call_kwargs = mock_fetch.call_args.kwargs
    expected_start_ts = older_bars['datetime'].max()
    expected_start = expected_start_ts.strftime('%Y-%m-%d %H:%M:%S')
    assert call_kwargs['start_date'] == expected_start
    assert any(
        'in the future' in record.message
        for record in caplog.records
    )
    healed_state = json.loads(state_path.read_text())
    healed_ts = datetime.fromisoformat(healed_state['last_covered_ts'])
    assert healed_ts < datetime.now(tz=UTC)


def test_refresh_from_binancial_clamps_when_frame_ts_also_in_future(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''Pin: even when both the state ts AND the frame max are in
    the future, the refresh proceeds with `now - 1h` clamp rather
    than fetching a future window or skipping.
    '''

    parquet_path, state_path = cache_paths
    future_bars = _make_klines(
        datetime.now(tz=UTC) + timedelta(hours=2),
        count=3,
    )
    future_bars.write_parquet(parquet_path)
    future_state = datetime.now(tz=UTC) + timedelta(days=1)
    state_path.write_text(json.dumps({
        'last_covered_ts': future_state.isoformat(),
    }))

    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache.load()
    snapshot_pd = _make_klines_pandas(
        datetime.now(tz=UTC) - timedelta(minutes=2),
        count=2,
    )

    with (
        patch(
            'praxis.market_data_cache.get_spot_klines',
            return_value=snapshot_pd,
        ) as mock_fetch,
        caplog.at_level('WARNING', logger='praxis.market_data_cache'),
    ):
        cache.refresh_from_binancial()

    mock_fetch.assert_called_once()
    call_kwargs = mock_fetch.call_args.kwargs
    start_dt = datetime.strptime(
        call_kwargs['start_date'], '%Y-%m-%d %H:%M:%S',
    ).replace(tzinfo=UTC)
    assert start_dt < datetime.now(tz=UTC)
    assert any(
        'clamping to bootstrap window' in record.message
        for record in caplog.records
    )


def test_latest_frame_ts_converts_non_utc_aware_to_utc(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: `_latest_frame_ts` normalizes an aware non-UTC datetime
    in the frame's max position to UTC. Without normalization the
    downstream `strftime` would silently drop the offset and
    produce a `start_date` for the wrong wall-clock window.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    tokyo = timezone(timedelta(hours=9))
    cache._frame = pl.DataFrame({
        'datetime': pl.Series(
            'datetime',
            [datetime(2026, 5, 16, 9, 0, 0, tzinfo=tokyo)],
            dtype=pl.Datetime('us', 'Asia/Tokyo'),
        ),
    })

    result = cache._latest_frame_ts()

    assert result is not None
    assert result.utcoffset() == timedelta(0)
    assert result == datetime(2026, 5, 16, 0, 0, 0, tzinfo=UTC)


def test_snapshot_converts_non_utc_aware_to_utc(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Same normalization contract on the `snapshot` path so the
    poller's staleness comparison is always against a UTC value.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    tokyo = timezone(timedelta(hours=9))
    cache._frame = pl.DataFrame({
        'datetime': pl.Series(
            'datetime',
            [datetime(2026, 5, 16, 9, 0, 0, tzinfo=tokyo)],
            dtype=pl.Datetime('us', 'Asia/Tokyo'),
        ),
    })

    _, latest = cache.snapshot(60)

    assert latest is not None
    assert latest.utcoffset() == timedelta(0)
    assert latest == datetime(2026, 5, 16, 0, 0, 0, tzinfo=UTC)


def test_apply_new_bars_fast_path_skips_full_sort_when_no_overlap(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: when `new_bars.min() > _frame.max()` (the per-minute
    happy path), `_apply_new_bars` does NOT call `merged.unique` /
    `merged.sort`. Patched so the test fails loudly if the slow path
    is taken — the fix is meant to keep per-refresh cost from
    scaling with cache size.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache._frame = _make_klines(_BASE_TS, count=5)
    new_bars = _make_klines(_BASE_TS + timedelta(minutes=5), count=3)

    original_unique = pl.DataFrame.unique
    original_sort = pl.DataFrame.sort
    calls: dict[str, int] = {'unique': 0, 'sort': 0}

    def _spy_unique(self: pl.DataFrame, *args: object, **kwargs: object) -> pl.DataFrame:
        calls['unique'] += 1
        return original_unique(self, *args, **kwargs)

    def _spy_sort(self: pl.DataFrame, *args: object, **kwargs: object) -> pl.DataFrame:
        calls['sort'] += 1
        return original_sort(self, *args, **kwargs)

    with (
        patch.object(pl.DataFrame, 'unique', _spy_unique),
        patch.object(pl.DataFrame, 'sort', _spy_sort),
    ):
        cache._apply_new_bars(new_bars, source='binancial')

    assert calls['unique'] == 0
    assert calls['sort'] == 0
    assert cache.frame.height == 8
    datetimes = cache.frame['datetime'].to_list()
    assert datetimes == sorted(datetimes)


def test_apply_new_bars_slow_path_runs_on_overlap(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: when `new_bars.min() <= _frame.max()` (Limen boundary,
    corrupt-state full re-fetch), the slow path runs `unique` +
    `sort` so dedupe is correct.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    cache._frame = _make_klines(_BASE_TS, count=5)
    overlapping = _make_klines(_BASE_TS + timedelta(minutes=3), count=4)

    original_sort = pl.DataFrame.sort
    sort_calls: dict[str, int] = {'n': 0}

    def _spy_sort(self: pl.DataFrame, *args: object, **kwargs: object) -> pl.DataFrame:
        sort_calls['n'] += 1
        return original_sort(self, *args, **kwargs)

    with patch.object(pl.DataFrame, 'sort', _spy_sort):
        cache._apply_new_bars(overlapping, source='binancial')

    assert sort_calls['n'] >= 1
    assert cache.frame.height == 7
    datetimes = cache.frame['datetime'].to_list()
    assert datetimes == sorted(datetimes)
    assert len(datetimes) == len(set(datetimes))


def test_apply_new_bars_drops_future_dated_rows_before_persist(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''Pin: when the merged frame contains future-dated rows (from
    pre-existing _frame rows, or somehow from new_bars), they are
    filtered out before computing `new_high_water` and persisting.
    Otherwise the state file would keep getting a future
    `last_covered_ts`, defeating the round-11 future-state self-heal
    and making the poller's staleness check report fresh on
    negative age.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    now = datetime.now(tz=UTC)
    future_bars = _make_klines(now + timedelta(hours=2), count=3)
    future_bars.write_parquet(parquet_path)
    cache.load()
    assert cache.frame.height == 3

    past_snapshot = _make_klines_pandas(now - timedelta(minutes=5), count=2)

    with (
        patch(
            'praxis.market_data_cache.get_spot_klines',
            return_value=past_snapshot,
        ),
        caplog.at_level('WARNING', logger='praxis.market_data_cache'),
    ):
        cache.refresh_from_binancial()

    assert cache.frame.height == 2
    max_ts = cache.frame['datetime'].max()
    assert max_ts < datetime.now(tz=UTC)

    healed_state = json.loads(state_path.read_text())
    healed_ts = datetime.fromisoformat(healed_state['last_covered_ts'])
    assert healed_ts < datetime.now(tz=UTC)

    assert any(
        'dropped future-dated rows' in record.message
        for record in caplog.records
    )


def test_apply_new_bars_skips_persist_when_every_row_future(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''When fetch returns only future-dated rows (extreme corruption
    case), the filter empties the frame; persist is skipped so the
    on-disk state is not overwritten with an empty frame.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    now = datetime.now(tz=UTC)
    future_only = _make_klines_pandas(now + timedelta(hours=2), count=3)

    with (
        patch(
            'praxis.market_data_cache.get_spot_klines',
            return_value=future_only,
        ),
        caplog.at_level('WARNING', logger='praxis.market_data_cache'),
    ):
        cache.refresh_from_binancial()

    assert not parquet_path.exists()
    assert not state_path.exists()
    assert any(
        'every fetched bar was future-dated' in record.message
        for record in caplog.records
    )


def test_apply_new_bars_normalizes_schema_across_sources(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: production-observed failure mode. Limen HF parquet and
    binancial pandas->polars frames differ on multiple columns:

      - `datetime`: Limen `Datetime('ms', 'UTC')` vs binancial
        `Datetime('us', 'UTC')`
      - `no_of_trades`: Limen `UInt64` vs binancial `Int64`
        (pandas has no UInt type so pd->pl always gives Int64)
      - any future schema drift on any column

    Pre-fix `pl.concat([_frame, new_bars])` raised `SchemaError` on
    the first mismatched column, freezing the cache at Limen's
    high-water mark. Post-fix `_apply_new_bars` casts every column
    in new_bars whose dtype differs from `self._frame`'s dtype
    BEFORE the concat, so all current and future column-dtype
    mismatches resolve uniformly at the merge chokepoint.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    base = _make_klines(_BASE_TS, count=5)
    limen_like = base.with_columns(
        pl.col('datetime').cast(pl.Datetime('ms', 'UTC')),
        pl.col('no_of_trades').cast(pl.UInt64),
    )
    cache._frame = limen_like
    assert cache.frame.schema['datetime'] == pl.Datetime('ms', 'UTC')
    assert cache.frame.schema['no_of_trades'] == pl.UInt64

    binancial_like = _make_klines(_BASE_TS + timedelta(minutes=5), count=3)
    binancial_like = binancial_like.with_columns(
        pl.col('no_of_trades').cast(pl.Int64),
    )
    assert binancial_like.schema['datetime'] == pl.Datetime('us', 'UTC')
    assert binancial_like.schema['no_of_trades'] == pl.Int64

    cache._apply_new_bars(binancial_like, source='binancial')

    assert cache.frame.height == 8
    assert cache.frame.schema['datetime'] == pl.Datetime('ms', 'UTC')
    assert cache.frame.schema['no_of_trades'] == pl.UInt64
    datetimes = cache.frame['datetime'].to_list()
    assert datetimes == sorted(datetimes)


def test_apply_new_bars_rejects_unknown_source(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Typos in the source string are loud, not silent.'''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)
    bars = _make_klines(_BASE_TS, count=2)

    with pytest.raises(ValueError, match="must be 'limen' or 'binancial'"):
        cache._apply_new_bars(bars, source='binance')


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
    leave the disk parquet inconsistent with the state file.

    Both mocked fetchers `time.sleep(0.1)` before returning so the
    two refresh threads actually overlap inside `_apply_new_bars`
    (without the sleep, mocked fetches return in microseconds and
    the threads serialize trivially — the lock is never exercised).
    Afterward the on-disk parquet's bar count must match the
    state's `last_covered_ts` (no in-flight reorder lost a write).
    '''

    import threading as _threading
    import time as _time

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    limen_bars = _make_klines(_BASE_TS, count=10)
    binancial_bars = _make_klines_pandas(
        _BASE_TS + timedelta(minutes=10), count=5,
    )

    def _slow_limen(**_kwargs: object) -> pl.DataFrame:
        _time.sleep(0.1)
        return limen_bars

    def _slow_binancial(*_args: object, **_kwargs: object) -> pd.DataFrame:
        _time.sleep(0.1)
        return binancial_bars

    with patch(
        'praxis.market_data_cache.HistoricalData',
    ) as mock_hd_cls, patch(
        'praxis.market_data_cache.get_spot_klines',
        side_effect=_slow_binancial,
    ):
        mock_hd_cls.return_value.get_spot_klines.side_effect = _slow_limen

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


def test_scheduler_init_rejects_nan_interval() -> None:
    '''NaN binancial_interval_seconds would crash the daemon via
    Event.wait(timeout=NaN), so reject at construction time.
    '''

    with pytest.raises(ValueError, match='must be finite'):
        CacheScheduler(
            MagicMock(spec=MainCache),
            binancial_interval_seconds=float('nan'),
        )


def test_scheduler_init_rejects_inf_interval() -> None:
    '''inf binancial_interval_seconds would stall refresh forever.'''

    with pytest.raises(ValueError, match='must be finite'):
        CacheScheduler(
            MagicMock(spec=MainCache),
            binancial_interval_seconds=float('inf'),
        )


def test_scheduler_limen_loop_falls_back_on_non_finite_schedule(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''Defensive: if a user-supplied limen_schedule_fn returns
    NaN/inf, the loop logs a warning and uses a 1-hour fallback
    rather than passing the bad value into Event.wait.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    schedule_called = threading.Event()

    def _bad_schedule() -> float:
        schedule_called.set()
        return float('nan')

    scheduler = CacheScheduler(
        cache,
        binancial_interval_seconds=10.0,
        limen_schedule_fn=_bad_schedule,
    )

    with caplog.at_level('WARNING', logger='praxis.market_data_cache'):
        scheduler.start()
        assert schedule_called.wait(timeout=2.0), (
            'limen loop never invoked schedule_fn within timeout'
        )
        scheduler.stop(timeout_seconds=2.0)

    assert any(
        'non-finite seconds' in record.message
        for record in caplog.records
    )


def test_scheduler_limen_loop_survives_raising_schedule_fn(
    cache_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''A schedule_fn that raises (or returns a non-numeric value
    that float() rejects) must not kill the limen daemon. The loop
    logs and falls back to the safe 1-hour wait.
    '''

    parquet_path, state_path = cache_paths
    cache = MainCache(MagicMock(), parquet_path, state_path)

    schedule_called = threading.Event()

    def _raising_schedule() -> float:
        schedule_called.set()
        msg = 'synthetic schedule_fn failure'
        raise RuntimeError(msg)

    scheduler = CacheScheduler(
        cache,
        binancial_interval_seconds=10.0,
        limen_schedule_fn=_raising_schedule,
    )

    with caplog.at_level('ERROR', logger='praxis.market_data_cache'):
        scheduler.start()
        assert schedule_called.wait(timeout=2.0)
        assert scheduler._limen_thread is not None
        assert scheduler._limen_thread.is_alive()
        scheduler.stop(timeout_seconds=2.0)

    assert any(
        'limen_schedule_fn raised' in record.message
        for record in caplog.records
    )


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


def test_scheduler_start_recovers_from_dead_thread_refs(
    cache_paths: tuple[Path, Path],
) -> None:
    '''Pin: `start()` is recovery-safe — if the existing thread refs
    are non-None but no longer alive (e.g. a prior `stop()` timed
    out and left the refs in place, or a thread exited unexpectedly),
    the next `start()` recreates and starts fresh threads instead of
    no-oping. Pre-fix the non-None check made every subsequent
    `start()` a permanent no-op after a timed-out stop.
    '''

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
    scheduler.stop(timeout_seconds=2.0)
    assert scheduler._limen_thread is None
    assert scheduler._binancial_thread is None

    dead_limen = threading.Thread(target=lambda: None, daemon=True)
    dead_limen.start()
    dead_limen.join()
    dead_binancial = threading.Thread(target=lambda: None, daemon=True)
    dead_binancial.start()
    dead_binancial.join()
    scheduler._limen_thread = dead_limen
    scheduler._binancial_thread = dead_binancial
    assert not dead_limen.is_alive()
    assert not dead_binancial.is_alive()

    scheduler.start()

    assert scheduler._limen_thread is not dead_limen
    assert scheduler._binancial_thread is not dead_binancial
    assert scheduler._limen_thread is not None
    assert scheduler._binancial_thread is not None
    assert scheduler._limen_thread.is_alive()
    assert scheduler._binancial_thread.is_alive()

    scheduler.stop(timeout_seconds=2.0)


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
