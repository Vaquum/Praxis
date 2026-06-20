from __future__ import annotations

from datetime import datetime, timedelta, UTC

import pytest

from praxis.replay.replay_clock import ReplayClock

_START = datetime(2026, 1, 1, tzinfo=UTC)


def test_now_returns_start() -> None:
    clock = ReplayClock(_START)

    assert clock.now() == _START


def test_advance_to_moves_forward() -> None:
    clock = ReplayClock(_START)
    later = _START + timedelta(seconds=900)
    clock.advance_to(later)

    assert clock.now() == later


def test_advance_to_same_instant_allowed() -> None:
    clock = ReplayClock(_START)
    clock.advance_to(_START)

    assert clock.now() == _START


def test_advance_to_backward_raises() -> None:
    clock = ReplayClock(_START)
    earlier = _START - timedelta(seconds=1)

    with pytest.raises(ValueError, match='cannot move backward'):
        clock.advance_to(earlier)


def test_naive_start_raises() -> None:
    with pytest.raises(ValueError, match='timezone-aware'):
        ReplayClock(datetime(2026, 1, 1))


def test_naive_advance_raises() -> None:
    clock = ReplayClock(_START)

    with pytest.raises(ValueError, match='timezone-aware'):
        clock.advance_to(datetime(2026, 1, 2))
