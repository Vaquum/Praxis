'''Background poller that keeps the `BookCache` current from the venue.'''

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

from praxis.infrastructure.book_cache import BookCache
from praxis.infrastructure.venue_adapter import OrderBookSnapshot

__all__ = ['BookPoller']

_log = logging.getLogger(__name__)


class BookPoller:
    '''Polls the venue order book for one symbol and updates the cache.'''

    def __init__(
        self,
        symbol: str,
        fetch: Callable[[], Awaitable[OrderBookSnapshot]],
        cache: BookCache,
        clock: Callable[[], datetime],
        interval_seconds: float,
    ) -> None:

        if not symbol:
            raise ValueError('symbol must be a non-empty string')

        if interval_seconds <= 0:
            raise ValueError(f'interval_seconds must be positive, got {interval_seconds}')

        self._symbol = symbol
        self._fetch = fetch
        self._cache = cache
        self._clock = clock
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        '''Start the background polling loop.'''

        if self.running:
            raise RuntimeError('BookPoller already running')

        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._loop(), name=f'book-poller-{self._symbol}',
        )

    async def stop(self) -> None:
        '''Signal the loop to exit, then cancel and await it.'''

        self._stop_event.set()

        if self._task is not None:
            self._task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await self._task

            self._task = None

    async def tick_once(self) -> None:
        '''Fetch the order book once and update the cache.'''

        snapshot = await self._fetch()
        self._cache.update(self._symbol, snapshot, self._clock())

    async def _loop(self) -> None:

        while not self._stop_event.is_set():

            try:
                await self.tick_once()
            except Exception:  # noqa: BLE001 - a poll failure must not stop the loop
                _log.exception('book poll tick failed; continuing')

            try:
                await asyncio.wait_for(self._stop_event.wait(), self._interval_seconds)
            except TimeoutError:
                continue
