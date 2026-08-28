'''Reusable event-spine projection-replay parity harness.

Generalizes the per-scenario replay-equality checks into reusable
assertions over the boot-time projection path
(`ExecutionManager.replay_events` folding events through
`TradingState.apply`):

- `assert_replays_equal` pins projection parity when a live projection is
  held in memory, the live-versus-replayed case the execution-manager
  tests drive directly.
- `assert_reconstructs_clean` pins clean, deterministic,
  invariant-preserving reconstruction of an arbitrary recorded spine, the
  case a captured paper session exercises before a live cutover.

Decision parity between the paper and live code paths is out of scope:
the paper venue is MARKET-only, so it cannot exercise the live-only
resting order types, and the two paths share one adapter. The harness
asserts projection parity only.
'''

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from praxis.core.domain.events import Event
from praxis.core.execution_manager import ExecutionManager
from praxis.core.trading_state import TradingState
from praxis.infrastructure.event_spine import EventSpine

__all__ = [
    'assert_reconstructs_clean',
    'assert_replays_equal',
    'state_snapshot',
]


def state_snapshot(trading_state: TradingState) -> dict[str, Any]:
    '''Return a comparable snapshot of the projection's public state.'''

    return {
        'positions': dict(trading_state.positions),
        'orders': dict(trading_state.orders),
        'closed_orders': dict(trading_state.closed_orders),
        'trade_strategy_ids': dict(trading_state.trade_strategy_ids),
        'schemes': dict(trading_state.schemes),
        'oco_leg_parent': dict(trading_state.oco_leg_parent),
        'oco_parent_legs': dict(trading_state.oco_parent_legs),
    }


def assert_replays_equal(live: TradingState, replayed: TradingState) -> None:
    '''Assert a replayed projection is field-identical to the live one.'''

    live_snapshot = state_snapshot(live)
    replayed_snapshot = state_snapshot(replayed)
    diverged = [
        field
        for field in live_snapshot
        if live_snapshot[field] != replayed_snapshot[field]
    ]

    assert not diverged, f'projection replay diverged on fields: {diverged}'


def _assert_projection_invariants(trading_state: TradingState) -> None:
    '''Assert projection-level invariants a reconstructed state must hold.'''

    for leg, parent in trading_state.oco_leg_parent.items():
        legs = trading_state.oco_parent_legs.get(parent, ())

        assert leg in legs, (
            f'oco_leg_parent[{leg!r}]={parent!r} has no matching parent leg'
        )

    for parent, legs in trading_state.oco_parent_legs.items():
        for leg in legs:
            assert trading_state.oco_leg_parent.get(leg) == parent, (
                f'oco_parent_legs[{parent!r}] lists {leg!r} without a back-reference'
            )

    overlap = set(trading_state.orders) & set(trading_state.closed_orders)

    assert not overlap, f'orders present as both open and closed: {sorted(overlap)}'


def _partition_by_account(
    events: list[tuple[int, Event]],
) -> dict[str, list[tuple[int, Event]]]:
    '''Group `(seq, event)` rows by owning account, preserving order.'''

    by_account: defaultdict[str, list[tuple[int, Event]]] = defaultdict(list)
    for seq, event in events:
        by_account[event.account_id].append((seq, event))

    return dict(by_account)


def _replay_account(
    manager: ExecutionManager,
    account_id: str,
    events: list[tuple[int, Event]],
) -> TradingState:
    '''Replay one account's history into a fresh manager and return its state.'''

    manager.register_account(account_id, booting=True)
    manager.replay_events(account_id, events)

    return manager._accounts[account_id].trading_state


async def assert_reconstructs_clean(
    manager_factory: Callable[[], ExecutionManager],
    spine: EventSpine,
    epoch_id: int,
    account_ids: tuple[str, ...],
) -> None:
    '''Assert a recorded spine reconstructs cleanly and deterministically.

    Verifies the spine hash chain, replays each account's full history into
    a fresh manager from `manager_factory`, checks projection-level
    invariants, and confirms a second independent replay reconstructs an
    identical projection.

    Args:
        manager_factory: Builds a fresh, empty `ExecutionManager` per call.
        spine: Recorded event spine to replay.
        epoch_id: Epoch whose events are replayed.
        account_ids: Accounts expected in the recording.
    '''

    await spine.verify_chain()

    rows = await spine.read(epoch_id=epoch_id)
    by_account = _partition_by_account(rows)

    recorded_accounts = set(by_account)
    requested_accounts = set(account_ids)

    assert recorded_accounts == requested_accounts, (
        f'recorded accounts {sorted(recorded_accounts)} do not match '
        f'requested {sorted(requested_accounts)}'
    )

    for account_id in account_ids:
        events = by_account[account_id]

        first_state = _replay_account(manager_factory(), account_id, events)
        _assert_projection_invariants(first_state)

        second_state = _replay_account(manager_factory(), account_id, events)

        assert_replays_equal(first_state, second_state)
