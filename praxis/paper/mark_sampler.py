'''Periodic mark-price sampler that persists the paper metrics equity series.

Each tick reads the current mark price and appends a `MarkSampled` event to
the Event Spine. Replaying those samples plus the run's fills reconstructs
the equity/return series the paper metrics are computed from, so the sample
cadence is also the durable "periodic snapshot" of the run.
'''

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from decimal import Decimal

from praxis.core.domain.events import MarkSampled

__all__ = ['MarkSampler']

_log = logging.getLogger(__name__)


class MarkSampler:

    '''Append a `MarkSampled` event on a fixed cadence.

    Args:
        account_id: Account the samples belong to.
        symbol: Symbol the mark applies to.
        mark_price_provider: Returns the current mark price, or `None`
            when no market data is available yet (the tick is skipped).
        append: Coroutine appending an event to the Event Spine.
        clock: Returns the current UTC time; injected so a replay or a
            test drives it deterministically.
        interval_seconds: Seconds between samples.
    '''

    def __init__(
        self,
        account_id: str,
        symbol: str,
        mark_price_provider: Callable[[], Decimal | None],
        append: Callable[[MarkSampled], Awaitable[object]],
        clock: Callable[[], datetime],
        interval_seconds: float,
    ) -> None:

        if not account_id:
            raise ValueError('account_id must be a non-empty string')

        if not symbol:
            raise ValueError('symbol must be a non-empty string')

        if interval_seconds <= 0:
            raise ValueError(f'interval_seconds must be positive, got {interval_seconds}')

        self._account_id = account_id
        self._symbol = symbol
        self._mark_price_provider = mark_price_provider
        self._append = append
        self._clock = clock
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def running(self) -> bool:

        return self._task is not None and not self._task.done()

    def start(self) -> None:

        '''Start the background sampling loop.'''

        if self.running:
            raise RuntimeError('MarkSampler already running')

        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name='mark-sampler')

    async def stop(self) -> None:

        '''Signal the loop to exit and await it.'''

        self._stop_event.set()

        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

            self._task = None

    async def tick_once(self) -> bool:

        '''Sample the mark once, appending an event if a price is available.

        Returns:
            True if a `MarkSampled` event was appended, False if the mark
            price was unavailable and the tick was skipped.
        '''

        price = self._mark_price_provider()

        if price is None:
            return False

        await self._append(
            MarkSampled(
                account_id=self._account_id,
                timestamp=self._clock(),
                symbol=self._symbol,
                mark_price=price,
            )
        )

        return True

    async def _loop(self) -> None:

        while not self._stop_event.is_set():

            try:
                await self.tick_once()
            except Exception:  # noqa: BLE001 - a sampling failure must not stop the loop
                _log.exception('mark sample tick failed; continuing')

            try:
                await asyncio.wait_for(self._stop_event.wait(), self._interval_seconds)
            except TimeoutError:
                continue
