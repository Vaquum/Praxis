'''
Tests for the TokenBucket venue-operation rate limiter.
'''

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from praxis.infrastructure.token_bucket import TokenBucket


def _controlled() -> tuple[list[float], list[float], Callable[[], float], Callable[[float], Awaitable[None]]]:
    clock = [0.0]
    slept: list[float] = []

    async def _sleep(delay: float) -> None:
        slept.append(delay)
        clock[0] += delay

    return clock, slept, lambda: clock[0], _sleep


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError, match='rate'):
        TokenBucket(0, 10)


def test_rejects_non_positive_capacity() -> None:
    with pytest.raises(ValueError, match='capacity'):
        TokenBucket(10, 0)


@pytest.mark.asyncio
async def test_burst_up_to_capacity_does_not_wait() -> None:
    _clock, slept, clock, sleep = _controlled()
    bucket = TokenBucket(rate=10, capacity=3, clock=clock, sleep=sleep)

    for _ in range(3):
        await bucket.acquire()

    assert slept == []


@pytest.mark.asyncio
async def test_waits_for_refill_when_empty() -> None:
    _clock, slept, clock, sleep = _controlled()
    bucket = TokenBucket(rate=10, capacity=1, clock=clock, sleep=sleep)

    await bucket.acquire()
    await bucket.acquire()

    assert slept == [pytest.approx(0.1)]


@pytest.mark.asyncio
async def test_lock_released_while_waiting() -> None:
    clock = [0.0]
    locked_during_sleep: list[bool] = []

    async def _sleep(delay: float) -> None:
        locked_during_sleep.append(bucket._lock.locked())
        clock[0] += delay

    bucket = TokenBucket(rate=10, capacity=1, clock=lambda: clock[0], sleep=_sleep)

    await bucket.acquire()
    await bucket.acquire()

    assert locked_during_sleep == [False]


@pytest.mark.asyncio
async def test_cancel_during_wait_refunds_token() -> None:
    clock = [0.0]

    async def _sleep(_delay: float) -> None:
        raise asyncio.CancelledError

    bucket = TokenBucket(rate=10, capacity=1, clock=lambda: clock[0], sleep=_sleep)

    await bucket.acquire()

    with pytest.raises(asyncio.CancelledError):
        await bucket.acquire()

    assert bucket._tokens == 0


@pytest.mark.asyncio
async def test_throttles_sustained_rate() -> None:
    _clock, slept, clock, sleep = _controlled()
    bucket = TokenBucket(rate=5, capacity=1, clock=clock, sleep=sleep)

    for _ in range(5):
        await bucket.acquire()

    assert len(slept) == 4
    assert all(delay == pytest.approx(0.2) for delay in slept)
