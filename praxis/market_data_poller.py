'''Shared market data poller for Nexus signal generation.

Periodically fetches klines from TDW per unique kline_size
and provides thread-safe read access for Nexus instances.
Each kline_size has its own poll interval and thread.
Supports runtime addition and removal of kline_sizes.
'''

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import polars as pl

from tdw_control_plane.query.get_binance_spot_klines import get_binance_spot_klines

__all__ = ['MarketDataPoller']

_log = logging.getLogger(__name__)


@dataclass
class _PollerThread:
    thread: threading.Thread
    stop_event: threading.Event
    kline_size: int
    interval: int


class MarketDataPoller:
    '''Thread-based poller fetching klines from TDW.

    Each kline_size is polled at its own interval. Supports runtime
    addition and removal of kline_sizes without restarting.

    Args:
        kline_intervals: Initial mapping of kline_size (seconds) to poll interval (seconds).
        n_rows: Max rows per kline query.
    '''

    def __init__(
        self,
        kline_intervals: dict[int, int] | None = None,
        n_rows: int = 5000,
    ) -> None:
        self._n_rows = n_rows
        self._data: dict[int, pl.DataFrame] = {}
        self._lock = threading.Lock()
        self._pollers: dict[int, _PollerThread] = {}
        self._refcounts: dict[int, int] = {}
        self._started = False
        self._initial_intervals = dict(kline_intervals or {})

    @property
    def running(self) -> bool:
        '''Whether the poller has been started.'''

        return self._started

    def start(self) -> None:
        '''Start poller threads for initial kline_sizes.'''

        if self._started:
            return

        self._started = True

        with self._lock:
            for kline_size, interval in self._initial_intervals.items():
                self._refcounts[kline_size] = self._refcounts.get(kline_size, 0) + 1
                self._start_thread_locked(kline_size, interval)

        _log.info(
            'market data poller started',
            extra={'kline_sizes': sorted(self._pollers.keys())},
        )

    def stop(self) -> None:
        '''Stop all poller threads.'''

        with self._lock:
            pollers = list(self._pollers.values())

        for pt in pollers:
            pt.stop_event.set()

        for pt in pollers:
            pt.thread.join(timeout=10)

        with self._lock:
            self._pollers.clear()
            self._refcounts.clear()

        self._started = False
        _log.info('market data poller stopped')

    def add_kline_size(self, kline_size: int, interval: int) -> None:
        '''Add a reference to a kline_size. Starts polling if first reference.

        Multiple strategies can reference the same kline_size. The poller
        thread only stops when all references are removed.

        Args:
            kline_size: Kline bucket width in seconds.
            interval: Poll interval in seconds. If already polling, the
                existing interval is kept (first caller wins).
        '''

        with self._lock:
            count = self._refcounts.get(kline_size, 0)
            self._refcounts[kline_size] = count + 1

            if kline_size in self._pollers:
                return

            self._start_thread_locked(kline_size, interval)

        _log.info(
            'added kline_size',
            extra={'kline_size': kline_size, 'interval': interval, 'refcount': count + 1},
        )

    def remove_kline_size(self, kline_size: int) -> None:
        '''Remove a reference to a kline_size. Stops polling when last reference removed.

        Args:
            kline_size: Kline bucket width in seconds.
        '''

        with self._lock:
            count = self._refcounts.get(kline_size, 0)

            if count <= 1:
                self._refcounts.pop(kline_size, None)
                pt = self._pollers.pop(kline_size, None)
                self._data.pop(kline_size, None)
            else:
                self._refcounts[kline_size] = count - 1
                return

        if pt is not None:
            pt.stop_event.set()
            pt.thread.join(timeout=10)
            _log.info('removed kline_size', extra={'kline_size': kline_size})

    def get_market_data(self, kline_size: int) -> pl.DataFrame:
        '''Return latest kline DataFrame for a given kline_size.

        Args:
            kline_size: Kline bucket width in seconds.

        Returns:
            Rolling DataFrame of klines. Empty DataFrame if no data yet.
        '''

        with self._lock:
            return self._data.get(kline_size, pl.DataFrame())

    def _start_thread_locked(self, kline_size: int, interval: int) -> None:
        '''Create and start a poller thread. Must be called with lock held.'''

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._poll_loop,
            args=(kline_size, interval, stop_event),
            daemon=True,
            name=f'poller-{kline_size}s',
        )

        pt = _PollerThread(
            thread=thread,
            stop_event=stop_event,
            kline_size=kline_size,
            interval=interval,
        )

        self._pollers[kline_size] = pt
        thread.start()

    def _poll_loop(self, kline_size: int, interval: int, stop_event: threading.Event) -> None:
        self._fetch(kline_size)

        while not stop_event.wait(timeout=interval):
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
