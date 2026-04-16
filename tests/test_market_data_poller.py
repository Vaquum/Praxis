'''Tests for MarketDataPoller.'''

from __future__ import annotations

import time
from unittest.mock import patch

import polars as pl

from praxis.market_data_poller import MarketDataPoller


def _mock_klines(**_kwargs: object) -> pl.DataFrame:
    return pl.DataFrame({
        'datetime': [1000, 2000],
        'open': [70000.0, 70100.0],
        'high': [71000.0, 71100.0],
        'low': [69000.0, 69100.0],
        'close': [70500.0, 70600.0],
        'volume': [100.0, 110.0],
    })


class TestMarketDataPoller:

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
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
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_fetches_data_on_start(self, _mock: object) -> None:
        '''Poller fetches data immediately on start.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})

        poller.start()
        time.sleep(0.5)

        df = poller.get_market_data(3600)
        assert not df.is_empty()
        assert df.height == 2

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_unknown_kline_size_returns_empty(self, _mock: object) -> None:
        '''get_market_data returns empty DataFrame for unknown kline_size.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})

        poller.start()
        time.sleep(0.5)

        df = poller.get_market_data(900)
        assert df.is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_multiple_kline_sizes(self, _mock: object) -> None:
        '''Poller fetches data for each unique kline_size.'''

        poller = MarketDataPoller(kline_intervals={3600: 60, 900: 15})

        poller.start()
        time.sleep(0.5)

        df_3600 = poller.get_market_data(3600)
        df_900 = poller.get_market_data(900)

        assert not df_3600.is_empty()
        assert not df_900.is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=RuntimeError('connection failed'),
    )
    def test_fetch_error_does_not_crash(self, _mock: object) -> None:
        '''Fetch error is caught, poller continues.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})

        poller.start()
        time.sleep(0.5)

        assert poller.running is True
        df = poller.get_market_data(3600)
        assert df.is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
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
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_add_kline_size_at_runtime(self, _mock: object) -> None:
        '''add_kline_size starts a new poller thread.'''

        poller = MarketDataPoller()
        poller.start()

        assert poller.get_market_data(3600).is_empty()

        poller.add_kline_size(3600, 60)
        time.sleep(0.5)

        df = poller.get_market_data(3600)
        assert not df.is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_remove_kline_size_at_runtime(self, _mock: object) -> None:
        '''remove_kline_size stops the thread and clears data.'''

        poller = MarketDataPoller(kline_intervals={3600: 60})
        poller.start()
        time.sleep(0.5)

        assert not poller.get_market_data(3600).is_empty()

        poller.remove_kline_size(3600)

        assert poller.get_market_data(3600).is_empty()
        assert 3600 not in poller._pollers

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
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
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_remove_with_remaining_refs_keeps_thread(self, _mock: object) -> None:
        '''Removing one ref when two exist keeps the thread running.'''

        poller = MarketDataPoller()
        poller.start()

        poller.add_kline_size(3600, 60)
        poller.add_kline_size(3600, 60)
        time.sleep(0.5)

        poller.remove_kline_size(3600)

        assert 3600 in poller._pollers
        assert poller._refcounts[3600] == 1
        assert not poller.get_market_data(3600).is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_remove_last_ref_stops_thread(self, _mock: object) -> None:
        '''Removing last ref stops the thread and clears data.'''

        poller = MarketDataPoller()
        poller.start()

        poller.add_kline_size(3600, 60)
        poller.add_kline_size(3600, 60)
        time.sleep(0.5)

        poller.remove_kline_size(3600)
        poller.remove_kline_size(3600)

        assert 3600 not in poller._pollers
        assert poller.get_market_data(3600).is_empty()

        poller.stop()

    @patch(
        'praxis.market_data_poller.get_binance_spot_klines',
        side_effect=_mock_klines,
    )
    def test_start_empty_then_add(self, _mock: object) -> None:
        '''Poller starts with no kline_sizes, then adds at runtime.'''

        poller = MarketDataPoller()
        poller.start()

        assert poller.running is True
        assert len(poller._pollers) == 0

        poller.add_kline_size(900, 15)
        time.sleep(0.5)

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
