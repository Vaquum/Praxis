'''Tests for `_build_health_loop` (PT.5.2) + lifecycle (PT.5.3).

Covers PT.5.4.1–PT.5.4.4 from issue #75. PT.5.4.5 (`submit_abort_fn`
wired) is already exercised by `test_launcher_outbound_wiring`.
'''

from __future__ import annotations

import time
from decimal import Decimal
from unittest.mock import MagicMock

from nexus.core.domain.enums import OperationalMode
from nexus.core.domain.instance_state import InstanceState
from nexus.core.health_loop import HealthLoop

from praxis.core.domain.health_snapshot import HealthSnapshot
from praxis.launcher import _build_health_loop


def _state() -> InstanceState:
    return InstanceState.fresh(Decimal('10000'))


def _healthy_snapshot() -> HealthSnapshot:
    return HealthSnapshot(
        latency_p99_ms=10.0,
        consecutive_failures=0,
        failure_rate=0.0,
        rate_limit_headroom=0.1,
        clock_drift_ms=5.0,
    )


def _halt_snapshot() -> HealthSnapshot:
    return HealthSnapshot(
        latency_p99_ms=2000.0,
        consecutive_failures=0,
        failure_rate=0.0,
        rate_limit_headroom=0.0,
        clock_drift_ms=0.0,
    )


def _trading_returning(snapshot: HealthSnapshot) -> MagicMock:
    trading = MagicMock()
    trading.get_health_snapshot_sync.return_value = snapshot
    return trading


def test_build_health_loop_returns_health_loop_instance() -> None:
    '''The helper returns a HealthLoop wired to the supplied state.'''

    state = _state()
    trading = _trading_returning(_healthy_snapshot())

    loop = _build_health_loop(trading, state, account_id='acct-pt54')

    assert isinstance(loop, HealthLoop)
    assert loop.running is False


def test_health_loop_transition_updates_instance_state_mode() -> None:
    '''Snapshot exceeding `latency_halt_ms` flips state.mode to HALTED.'''

    state = _state()
    assert state.mode.mode == OperationalMode.ACTIVE

    trading = _trading_returning(_halt_snapshot())

    loop = _build_health_loop(trading, state, account_id='acct-pt54')
    loop.tick_once()

    assert state.mode.mode == OperationalMode.HALTED
    assert state.mode.trigger == 'health'
    trading.get_health_snapshot_sync.assert_called_once_with('acct-pt54')


def test_health_loop_no_transition_when_snapshot_within_limits() -> None:
    '''Healthy snapshot leaves state.mode untouched.'''

    state = _state()
    original_mode = state.mode

    trading = _trading_returning(_healthy_snapshot())

    loop = _build_health_loop(trading, state, account_id='acct-pt54')
    loop.tick_once()

    assert state.mode is original_mode
    assert state.mode.mode == OperationalMode.ACTIVE


def test_health_loop_stop_after_start() -> None:
    '''start() then stop() leaves the loop not running; both are idempotent.'''

    state = _state()
    trading = _trading_returning(_healthy_snapshot())

    loop = _build_health_loop(
        trading,
        state,
        account_id='acct-pt54',
        interval_seconds=0.05,
    )

    loop.start()
    loop.start()
    assert loop.running is True

    deadline = time.monotonic() + 1.0
    while (
        trading.get_health_snapshot_sync.call_count == 0
        and time.monotonic() < deadline
    ):
        time.sleep(0.02)

    assert trading.get_health_snapshot_sync.call_count > 0, (
        'health loop worker did not call get_health_snapshot_sync before stop()'
    )

    loop.stop()
    loop.stop()
    assert loop.running is False
