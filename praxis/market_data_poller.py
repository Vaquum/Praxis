'''Shared market data poller for Nexus signal generation.

Periodically fetches klines from TDW per unique kline_size
and provides thread-safe read access for Nexus instances.
Each kline_size has its own poll interval.
'''

from __future__ import annotations

import logging
import threading

import polars as pl

from tdw_control_plane.query.get_binance_spot_klines import get_binance_spot_klines

__all__ = ['MarketDataPoller']

_log = logging.getLogger(__name__)


class MarketDataPoller:
    '''Thread-based poller fetching klines from TDW.

    Each kline_size is polled at its own interval. The poll interval
    for a kline_size should match the minimum sensor interval_seconds
    that uses that kline_size.

    Args:
        kline_intervals: Mapping of kline_size (seconds) to poll interval (seconds).
        n_rows: Max rows per kline query.
    '''

    def __init__(
        self,
        kline_intervals: dict[int, int],
        n_rows: int = 5000,
    ) -> None:
        self._kline_intervals = dict(kline_intervals)
        self._n_rows = n_rows
        self._data: dict[int, pl.DataFrame] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._threads: dict[int, threading.Thread] = {}

    @property
    def running(self) -> bool:
        '''Whether any poller thread is currently running.'''

        return any(t.is_alive() for t in self._threads.values())

    def start(self) -> None:
        '''Start a poller thread per kline_size.'''

        if self._threads:
            return

        self._stop_event.clear()

        for kline_size, interval in self._kline_intervals.items():
            thread = threading.Thread(
                target=self._poll_loop,
                args=(kline_size, interval),
                daemon=True,
                name=f'poller-{kline_size}s',
            )
            self._threads[kline_size] = thread
            thread.start()

        _log.info(
            'market data poller started',
            extra={'kline_intervals': self._kline_intervals},
        )

    def stop(self) -> None:
        '''Stop all poller threads.'''

        self._stop_event.set()

        for thread in self._threads.values():
            thread.join(timeout=10)

        self._threads.clear()
        _log.info('market data poller stopped')

    def get_market_data(self, kline_size: int) -> pl.DataFrame:
        '''Return latest kline DataFrame for a given kline_size.

        Args:
            kline_size: Kline bucket width in seconds.

        Returns:
            Rolling DataFrame of klines. Empty DataFrame if no data yet.
        '''

        with self._lock:
            return self._data.get(kline_size, pl.DataFrame())

    def _poll_loop(self, kline_size: int, interval: int) -> None:
        self._fetch(kline_size)

        while not self._stop_event.wait(timeout=interval):
            self._fetch(kline_size)

    def _fetch(self, kline_size: int) -> None:
        try:
            df = get_binance_spot_klines(
                kline_size=kline_size,
                n_rows=self._n_rows,
            )

            with self._lock:
                self._data[kline_size] = df

            _log.debug(
                'fetched klines',
                extra={'kline_size': kline_size, 'rows': df.height},
            )
        except Exception:  # noqa: BLE001
            _log.exception('failed to fetch klines', extra={'kline_size': kline_size})
