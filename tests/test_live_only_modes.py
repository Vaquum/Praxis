'''
Tests for the live-only execution-mode classification.
'''

from __future__ import annotations

from praxis.core.domain.enums import ExecutionMode
from praxis.core.live_only_modes import LIVE_ONLY_MODES, is_live_only


def test_non_market_modes_are_live_only() -> None:
    assert frozenset({
        ExecutionMode.BRACKET,
        ExecutionMode.ICEBERG,
        ExecutionMode.LADDER_DCA,
    }) == LIVE_ONLY_MODES


def test_market_modes_are_paper_safe() -> None:
    for mode in (
        ExecutionMode.SINGLE_SHOT,
        ExecutionMode.TWAP,
        ExecutionMode.TIME_DCA,
        ExecutionMode.SCHEDULED_VWAP,
    ):
        assert not is_live_only(mode)


def test_is_live_only_matches_the_set() -> None:
    assert is_live_only(ExecutionMode.BRACKET)
    assert not is_live_only(ExecutionMode.SINGLE_SHOT)


def test_every_mode_is_classified() -> None:
    paper_safe = {mode for mode in ExecutionMode if not is_live_only(mode)}

    assert paper_safe | LIVE_ONLY_MODES == set(ExecutionMode)
    assert paper_safe & LIVE_ONLY_MODES == set()
