'''Tests for the event-spine projection-replay parity harness.'''

from __future__ import annotations

import pytest

from praxis.core.trading_state import TradingState

from tests.support.replay_parity import (
    assert_reconstructs_clean,
    assert_replays_equal,
    state_snapshot,
)
from tests.test_execution_manager_bracket_amend import (
    _ACCT,
    _EPOCH,
    _fresh_spine,
    _make_adapter,
    _mgr_on,
    _protected_bracket,
)

_EXPECTED_SNAPSHOT_FIELDS = frozenset({
    'positions',
    'orders',
    'closed_orders',
    'trade_strategy_ids',
    'schemes',
    'oco_leg_parent',
    'oco_parent_legs',
})


def test_state_snapshot_covers_projection_fields() -> None:
    snapshot = state_snapshot(TradingState(_ACCT))

    assert frozenset(snapshot) == _EXPECTED_SNAPSHOT_FIELDS


def test_assert_replays_equal_accepts_identical_projections() -> None:
    assert_replays_equal(TradingState(_ACCT), TradingState(_ACCT))


def test_assert_replays_equal_detects_divergence() -> None:
    diverged = TradingState(_ACCT)
    diverged.trade_strategy_ids['trade-1'] = 'strat_a'

    with pytest.raises(AssertionError, match='diverged'):
        assert_replays_equal(TradingState(_ACCT), diverged)


@pytest.mark.asyncio
async def test_bracket_spine_reconstructs_clean() -> None:
    spine, conn = await _fresh_spine()
    live = _mgr_on(spine, _make_adapter())
    try:
        await _protected_bracket(live)
        await live.unregister_account(_ACCT)

        await assert_reconstructs_clean(
            lambda: _mgr_on(spine, _make_adapter()),
            spine,
            _EPOCH,
            (_ACCT,),
        )

        replayed = _mgr_on(spine, _make_adapter())
        replayed.register_account(_ACCT, booting=True)
        replayed.replay_events(_ACCT, await spine.read(epoch_id=_EPOCH))
        snapshot = state_snapshot(replayed._accounts[_ACCT].trading_state)

        assert snapshot['orders'] or snapshot['positions']
    finally:
        for account_id in list(live._accounts):
            await live.unregister_account(account_id)

        await conn.close()
