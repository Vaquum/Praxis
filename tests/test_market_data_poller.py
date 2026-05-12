'''Tests for MarketDataPoller.'''

from __future__ import annotations

import time
from collections.abc import Callable
from unittest.mock import patch

import pandas as pd

from praxis.market_data_poller import MarketDataPoller


def _mock_klines(*_args: object, **_kwargs: object) -> pd.DataFrame:
    return pd.DataFrame({
        'open_time': [1000, 2000],
        'open': [70000.0, 70100.0],
        'high': [71000.0, 71100.0],
        'low': [69000.0, 69100.0],
        'close': [70500.0, 70600.0],
        'volume': [100.0, 110.0],
        'close_time': [1059, 2059],
        'qav': [0.0, 0.0],
        'num_trades': [10, 11],
        'taker_base_vol': [50.0, 55.0],
        'taker_quote_vol': [50.0, 55.0],
        'ignore': [0.0, 0.0],
    })


def _wait_until(predicate: Callable[[], bool], deadline: float = 5.0, step: float = 0.05) -> bool:
    '''Block until predicate() returns True, up to deadline seconds.'''

    while deadline > 0:
        if predicate():
            return True
        time.sleep(step)
        deadline -= step
    return predicate()


class TestMarketDataPoller:

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_start_and_stop(self, _mock: object) -> None:
        '''Poller starts and stops without error.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})

        poller.start()
        assert poller.running is True

        poller.stop()
        assert poller.running is False

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_fetches_data_on_start(self, _mock: object) -> None:
        '''Poller fetches data immediately on start.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})

        poller.start()
        assert _wait_until(lambda: not poller.get_market_data(3600).is_empty())

        df = poller.get_market_data(3600)
        assert not df.is_empty()
        assert df.height == 2

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_unknown_kline_size_returns_empty(self, _mock: object) -> None:
        '''get_market_data returns empty DataFrame for unknown kline_size.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})

        poller.start()
        _wait_until(lambda: not poller.get_market_data(3600).is_empty())

        df = poller.get_market_data(900)
        assert df.is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_multiple_kline_sizes(self, _mock: object) -> None:
        '''Poller fetches data for each unique kline_size.'''

        poller = MarketDataPoller(kline_intervals={3600: 60, 900: 15})

        poller.start()
        assert _wait_until(
            lambda: not poller.get_market_data(3600).is_empty()
            and not poller.get_market_data(900).is_empty(),
        )

        assert not poller.get_market_data(3600).is_empty()
        assert not poller.get_market_data(900).is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=RuntimeError('connection failed'),
    )
    def test_fetch_error_does_not_crash(self, _mock: object) -> None:
        '''Fetch error is caught, poller continues.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})

        poller.start()
        # Give the poller thread a moment to execute the failing fetch.
        _wait_until(lambda: False, deadline=0.3)

        assert poller.running is True
        df = poller.get_market_data(3600)
        assert df.is_empty()

        poller.stop()

    def test_slow_fetch_does_not_accumulate_drift_in_fetch_schedule(self) -> None:
        '''Anchored scheduling — a slow fetch does not push every subsequent
        start by `slow_overrun`.

        Cumulative timeline math (with `interval=0.1`, `slow_delay=0.15`,
        i.e. fetch #2 overruns by `0.5 * interval` — its own slot only,
        not enough to skip the next slot):

        | fetch | anchored start (this PR)               | pre-fix start (sleep-after) |
        | ----- | -------------------------------------- | --------------------------- |
        | 1     | anchor                                 | anchor                      |
        | 2     | anchor + 1*interval = 0.10, slow→0.25  | anchor + 1*interval = 0.10  |
        | 3     | n=max(3, int(0.25/0.1)+1)=3 → wait→0.30 | wait(0.1) after slow → 0.35 |
        | 4     | n=4 → 0.40                             | wait(0.1) → 0.45            |

        So fetch #4's offset from fetch #1 is `4 * interval = 0.40` for
        the anchored loop (skip-missed-slots makes fetch #3 skip the
        already-past slot 2 and land at slot 3) versus `3 * interval +
        slow_delay = 0.45` for the pre-fix loop. The slow fetch's
        overrun is absorbed once (into fetch #3's wait window) instead
        of paid forward cumulatively. The assertion below pins the
        anchored offset's upper bound at `4 * interval + interval / 4
        = 0.425`, which is between the two values and distinguishes
        the implementations deterministically; a pre-fix implementation
        that sleeps `interval` after each fetch returns would fail
        this assertion.
        '''

        interval = 0.1
        slow_delay = 0.15  # > interval — fetch #2 overruns its own wait window
        fetch_starts: list[float] = []
        call_count = {'n': 0}

        def slow_then_fast_fetch(*_args: object, **_kwargs: object) -> pd.DataFrame:
            call_count['n'] += 1
            fetch_starts.append(time.monotonic())
            if call_count['n'] == 2:
                time.sleep(slow_delay)
            return _mock_klines()

        with patch(
            'praxis.market_data_poller.get_spot_klines',
            side_effect=slow_then_fast_fetch,
        ):
            poller = MarketDataPoller(kline_intervals={3600: interval})
            poller.start()
            assert _wait_until(lambda: call_count['n'] >= 4, deadline=2.0)
            poller.stop()

        timeline_4 = fetch_starts[3] - fetch_starts[0]
        anchored_cap = 4 * interval + interval / 4
        assert timeline_4 < anchored_cap, (
            f'fetch #4 started at +{timeline_4:.3f}s from fetch #1; '
            f'anchored upper bound is {anchored_cap:.3f}s. Pre-fix '
            f'sleep-after-fetch behaviour would push fetch #4 to '
            f'~{3 * interval + slow_delay:.3f}s.'
        )

    def test_multi_interval_slow_fetch_collapses_missed_slots(self) -> None:
        '''Skip-missed-slots — a fetch overrunning `k * interval` (k >= 2)
        triggers exactly ONE catch-up fetch at the next future scheduled
        slot, not `k - 1` back-to-back fetches that fire with `wait(0)`.

        Cumulative timeline math (with `interval=0.1`, `slow_delay=0.25`,
        i.e. fetch #2 spans 2.5 intervals):

        | fetch | with skip-missed-slots                 | without (n += 1)            |
        | ----- | -------------------------------------- | --------------------------- |
        | 1     | anchor                                 | anchor                      |
        | 2     | anchor + 1*interval = 0.10, slow→0.35  | anchor + 1*interval = 0.10  |
        | 3     | n=max(3, int(0.35/0.1)+1)=4 → 0.40     | n=3 → wait(0) → fires 0.35  |
        | 4     | n=5 → 0.50                             | n=4 → 0.40                  |

        Without skip, fetches #3 and #2's-return cluster at t=0.35 with
        gap=0 — a back-to-back burst that hits the venue rate limiter.
        With skip, fetch #3 waits to the next future slot (anchor +
        4*interval = 0.40), so the gap from fetch #2's start to
        fetch #3's start is `slow_delay + (next_slot_offset)` =
        `0.25 + 0.05 = 0.30`, strictly greater than `slow_delay`.

        Assertion: `gap_2_to_3 > slow_delay + interval / 4`. With skip:
        `0.30 > 0.275` ✓. Without skip: `0.25 > 0.275` ✗.
        '''

        interval = 0.1
        slow_delay = 0.25  # 2.5 * interval — fetch #2 spans multiple slots
        fetch_starts: list[float] = []
        call_count = {'n': 0}

        def slow_then_fast_fetch(*_args: object, **_kwargs: object) -> pd.DataFrame:
            call_count['n'] += 1
            fetch_starts.append(time.monotonic())
            if call_count['n'] == 2:
                time.sleep(slow_delay)
            return _mock_klines()

        with patch(
            'praxis.market_data_poller.get_spot_klines',
            side_effect=slow_then_fast_fetch,
        ):
            poller = MarketDataPoller(kline_intervals={3600: interval})
            poller.start()
            assert _wait_until(lambda: call_count['n'] >= 3, deadline=2.0)
            poller.stop()

        gap_2_to_3 = fetch_starts[2] - fetch_starts[1]
        skip_threshold = slow_delay + interval / 4
        assert gap_2_to_3 > skip_threshold, (
            f'gap from fetch #2 to fetch #3 was {gap_2_to_3:.3f}s; '
            f'skip-missed-slots threshold is {skip_threshold:.3f}s. '
            f'Without-skip behaviour would fire fetch #3 immediately '
            f'after fetch #2 returns (gap ~= slow_delay = {slow_delay:.3f}s).'
        )

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_per_kline_size_threads(self, _mock: object) -> None:
        '''Each kline_size gets its own poller thread.'''

        poller = MarketDataPoller(kline_intervals={3600: 60, 900: 15})

        poller.start()

        assert len(poller._pollers) == 2
        assert 3600 in poller._pollers
        assert 900 in poller._pollers

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_add_kline_size_at_runtime(self, _mock: object) -> None:
        '''add_kline_size starts a new poller thread.'''

        poller = MarketDataPoller()
        poller.start()

        assert poller.get_market_data(3600).is_empty()

        poller.add_kline_size(3600, 60)
        assert _wait_until(lambda: not poller.get_market_data(3600).is_empty())

        df = poller.get_market_data(3600)
        assert not df.is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_remove_kline_size_at_runtime(self, _mock: object) -> None:
        '''remove_kline_size stops the thread and clears data.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})
        poller.start()
        assert _wait_until(lambda: not poller.get_market_data(3600).is_empty())

        assert not poller.get_market_data(3600).is_empty()

        poller.remove_kline_size(3600)

        assert poller.get_market_data(3600).is_empty()
        assert 3600 not in poller._pollers

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_add_duplicate_increments_refcount(self, _mock: object) -> None:
        '''Adding same kline_size twice increments refcount, one thread.'''

        poller = MarketDataPoller()
        poller.start()

        poller.add_kline_size(3600, 60)
        poller.add_kline_size(3600, 60)

        assert len(poller._pollers) == 1
        assert poller._refcounts[3600] == 2

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_remove_with_remaining_refs_keeps_thread(self, _mock: object) -> None:
        '''Removing one ref when two exist keeps the thread running.'''

        poller = MarketDataPoller()
        poller.start()

        poller.add_kline_size(3600, 60)
        poller.add_kline_size(3600, 60)
        assert _wait_until(lambda: not poller.get_market_data(3600).is_empty())

        poller.remove_kline_size(3600)

        assert 3600 in poller._pollers
        assert poller._refcounts[3600] == 1
        assert not poller.get_market_data(3600).is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_remove_last_ref_stops_thread(self, _mock: object) -> None:
        '''Removing last ref stops the thread and clears data.'''

        poller = MarketDataPoller()
        poller.start()

        poller.add_kline_size(3600, 60)
        poller.add_kline_size(3600, 60)
        assert _wait_until(lambda: not poller.get_market_data(3600).is_empty())

        poller.remove_kline_size(3600)
        poller.remove_kline_size(3600)

        assert 3600 not in poller._pollers
        assert poller.get_market_data(3600).is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_spot_klines',
        side_effect=_mock_klines,
    )
    def test_start_empty_then_add(self, _mock: object) -> None:
        '''Poller starts with no kline_sizes, then adds at runtime.'''

        poller = MarketDataPoller()
        poller.start()

        assert poller.running is True
        assert len(poller._pollers) == 0

        poller.add_kline_size(900, 15)
        assert _wait_until(lambda: not poller.get_market_data(900).is_empty())

        assert not poller.get_market_data(900).is_empty()

        poller.stop()

    def test_add_kline_size_rejects_non_positive_interval(self) -> None:
        '''add_kline_size raises ValueError for interval <= 0.'''

        poller = MarketDataPoller()
        poller.start()

        try:
            import pytest

            with pytest.raises(ValueError, match='interval must be positive'):
                poller.add_kline_size(3600, 0)

            with pytest.raises(ValueError, match='interval must be positive'):
                poller.add_kline_size(3600, -1)

            with pytest.raises(ValueError, match='kline_size must be positive'):
                poller.add_kline_size(0, 60)
        finally:
            poller.stop()

    def test_start_rejects_non_positive_initial_intervals(self) -> None:
        '''start() raises ValueError for non-positive initial kline_size or interval.'''

        import pytest

        poller = MarketDataPoller(kline_intervals={0: 60})
        with pytest.raises(ValueError, match='kline_size must be positive'):
            poller.start()

        poller = MarketDataPoller(kline_intervals={3600: 0})
        with pytest.raises(ValueError, match='interval must be positive'):
            poller.start()
