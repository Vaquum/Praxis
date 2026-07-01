import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.domain.events import MarkSampled
from praxis.paper.mark_sampler import MarkSampler

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def _sampler(
    price: Decimal | None,
    appended: list[MarkSampled],
    clock: Callable[[], datetime] = lambda: _TS,
) -> MarkSampler:
    async def append(event: MarkSampled) -> None:
        appended.append(event)

    return MarkSampler('acc', 'BTCUSDT', lambda: price, append, clock, 60.0)


@pytest.mark.asyncio
async def test_tick_appends_mark_sampled_when_price_available():
    appended: list[MarkSampled] = []
    sampler = _sampler(Decimal('62000.5'), appended)

    result = await sampler.tick_once()

    assert result is True
    assert len(appended) == 1
    assert appended[0].symbol == 'BTCUSDT'
    assert appended[0].mark_price == Decimal('62000.5')
    assert appended[0].account_id == 'acc'
    assert appended[0].timestamp == _TS


@pytest.mark.asyncio
async def test_tick_skips_when_price_unavailable():
    appended: list[MarkSampled] = []
    sampler = _sampler(None, appended)

    result = await sampler.tick_once()

    assert result is False
    assert appended == []


@pytest.mark.asyncio
async def test_tick_uses_injected_clock():
    appended: list[MarkSampled] = []
    times = iter([datetime(2026, 1, 1, 0, 0, tzinfo=UTC), datetime(2026, 1, 1, 0, 1, tzinfo=UTC)])
    sampler = _sampler(Decimal('100'), appended, clock=lambda: next(times))

    await sampler.tick_once()
    await sampler.tick_once()

    assert appended[0].timestamp != appended[1].timestamp


def test_rejects_bad_construction():
    async def append(_event: MarkSampled) -> None:
        return None

    with pytest.raises(ValueError, match='account_id'):
        MarkSampler('', 'BTCUSDT', lambda: None, append, lambda: _TS, 60.0)

    with pytest.raises(ValueError, match='interval_seconds must be positive'):
        MarkSampler('acc', 'BTCUSDT', lambda: None, append, lambda: _TS, 0.0)


@pytest.mark.asyncio
async def test_tick_failure_does_not_propagate_from_loop():
    calls = []

    async def failing_append(_event: MarkSampled) -> None:
        calls.append(1)
        raise RuntimeError('spine append failed')

    sampler = MarkSampler('acc', 'BTCUSDT', lambda: Decimal('100'), failing_append, lambda: _TS, 0.05)
    sampler.start()
    await asyncio.sleep(0.16)
    running = sampler.running
    await sampler.stop()

    assert running is True
    assert len(calls) >= 2
