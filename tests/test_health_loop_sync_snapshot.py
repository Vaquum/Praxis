'''Tests for PT-FIX-14: HealthLoop snapshot bypasses the async bridge.

Pre-fix: `_build_health_loop` curried `praxis_outbound.get_health_snapshot`
into the loop's `snapshot_provider`. That method scheduled a coroutine
on the asyncio loop via `run_coroutine_threadsafe` and waited up to
30 s on `future.result(timeout=...)`. When the loop was busy with a
slow venue REST call, the per-account `HealthLoop` thread blocked
until the coroutine drained, starving subsequent ticks.

Post-fix: a new `Trading.get_health_snapshot_sync(account_id)` calls
`BinanceAdapter.get_health_snapshot(...)` directly. The adapter's
sync method already serializes its tracker reads under
`threading.Lock`, so the cross-thread call is safe and never crosses
the loop. `_build_health_loop` consumes the sync accessor instead of
the async bridge.
'''

from __future__ import annotations

from unittest.mock import MagicMock

from nexus.core.domain.instance_state import InstanceState
from nexus.core.health_evaluator import HealthSnapshot

from praxis.launcher import _build_health_loop
from decimal import Decimal


def _build_state() -> InstanceState:
    return InstanceState.fresh(capital_pool=Decimal('10000'))


def test_snapshot_provider_uses_trading_sync_accessor() -> None:

    expected = HealthSnapshot(
        latency_p99_ms=42.0,
        consecutive_failures=0,
        failure_rate=0.0,
        rate_limit_headroom=0.1,
        clock_drift_ms=5.0,
    )

    trading = MagicMock()
    trading.get_health_snapshot_sync.return_value = expected

    loop = _build_health_loop(
        trading=trading,
        state=_build_state(),
        account_id='acct-1',
    )

    snapshot = loop._snapshot_provider()

    trading.get_health_snapshot_sync.assert_called_once_with('acct-1')
    assert snapshot is expected


def test_snapshot_provider_does_not_use_async_bridge() -> None:
    '''The provider must not touch any async/coroutine plumbing.'''

    trading = MagicMock()
    trading.get_health_snapshot_sync.return_value = HealthSnapshot(
        latency_p99_ms=0.0,
        consecutive_failures=0,
        failure_rate=0.0,
        rate_limit_headroom=0.0,
        clock_drift_ms=0.0,
    )

    loop = _build_health_loop(
        trading=trading,
        state=_build_state(),
        account_id='acct-2',
    )

    loop._snapshot_provider()

    assert not trading.get_health_snapshot.called, (
        'snapshot_provider should not invoke the async accessor; the sync '
        'accessor avoids the run_coroutine_threadsafe loop hop entirely'
    )
