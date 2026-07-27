'''
Async token-bucket rate limiter for venue operation budgeting.

Bounds the rate of venue REST operations (submit, cancel, query,
reconcile) to a shared per-second budget, complementing the Venue
Adapter's reactive 429 retry with proactive throttling.
'''

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

__all__ = ['TokenBucket']


class TokenBucket:

    '''
    A refilling token bucket that gates the rate of an async operation.

    Tokens refill continuously at `rate` per second up to `capacity`.
    `acquire` consumes one token, waiting for the next refill when the
    bucket is empty, so callers are throttled to at most `rate`
    operations per second with bursts up to `capacity`.

    Args:
        rate (float): Tokens replenished per second, positive.
        capacity (float): Maximum tokens held, positive.
        clock (Callable[[], float]): Monotonic time source in seconds.
        sleep (Callable[[float], Awaitable[None]]): Async sleep.
    '''

    def __init__(
        self,
        rate: float,
        capacity: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        '''Initialise a full bucket.'''

        if rate <= 0:
            msg = 'rate must be positive'
            raise ValueError(msg)

        if capacity <= 0:
            msg = 'capacity must be positive'
            raise ValueError(msg)

        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        '''Consume one token, waiting for refill when the bucket is empty.

        Under the lock, refill and reserve one token (letting the balance
        go negative), computing how long the reservation must wait for the
        deficit to refill. The lock is released before sleeping so a waiting
        caller never blocks other callers from reserving — each concurrent
        acquire reserves its own slot and waits proportionally, which is
        the intended throttle rather than head-of-line serialization.
        Reserving up front (rather than looping and re-checking) also avoids
        an unbounded refill loop under floating-point rounding.
        '''

        async with self._lock:
            now = self._clock()
            self._tokens = min(
                self._capacity,
                self._tokens + (now - self._updated) * self._rate,
            )
            self._updated = now

            wait = (1 - self._tokens) / self._rate if self._tokens < 1 else 0.0
            self._tokens -= 1

        if wait > 0:
            try:
                await self._sleep(wait)
            except asyncio.CancelledError:
                # Refund the reserved token so a cancellation mid-wait (common
                # on shutdown) does not leave permanent debt that throttles
                # every later operation. A single read-modify-write is atomic
                # on the event loop thread, so the lock is not needed and is
                # avoided to keep the cancellation path await-free.
                self._tokens = min(self._capacity, self._tokens + 1)
                raise
