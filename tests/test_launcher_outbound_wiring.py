'''Tests for `_build_praxis_outbound` (PT.5.1).

Confirms that the launcher wires every outbound callable `Nexus`
needs against the Praxis `Trading` singleton, including the two
fields that the PR-#73 launcher omitted: `submit_abort_fn` (needed
by `ShutdownSequencer` abort escalation and `submit_actions` ABORT
handling) and `get_health_snapshot_fn` (needed by the runtime
`HealthLoop` from PT.5.2).
'''

from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from nexus.infrastructure.praxis_connector.praxis_outbound import PraxisOutbound

from praxis.core.domain.health_snapshot import HealthSnapshot
from praxis.core.domain.trade_abort import TradeAbort
from praxis.launcher import _build_praxis_outbound
from praxis.trading import Trading


def _abort() -> TradeAbort:
    return TradeAbort(
        command_id='cmd-pt51',
        account_id='acct-pt51',
        reason='shutdown',
        created_at=datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC),
    )


def _snapshot() -> HealthSnapshot:
    return HealthSnapshot(
        latency_p99_ms=0.0,
        consecutive_failures=0,
        failure_rate=0.0,
        rate_limit_headroom=0.0,
        clock_drift_ms=0.0,
    )


def _run_loop_in_thread() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop, thread


def _stop_loop(loop: asyncio.AbstractEventLoop, thread: threading.Thread) -> None:
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)

    if thread.is_alive():
        pytest.fail(
            'event loop thread did not stop within 2s; '
            'refusing to close a running event loop',
        )

    if not loop.is_closed():
        loop.close()


def test_build_praxis_outbound_returns_praxis_outbound() -> None:
    '''Sanity: the helper returns a `PraxisOutbound`.

    Full wiring is exercised behaviorally by the `send_abort` and
    `get_health_snapshot` round-trip tests below, which drive the
    public surface and assert the underlying `Trading` mock was
    invoked. Those are the stable contract; `PraxisOutbound`'s
    private attributes are an implementation detail of an external
    dependency.
    '''

    trading = MagicMock(spec=Trading)
    loop = MagicMock(spec=asyncio.AbstractEventLoop)

    outbound = _build_praxis_outbound(trading, loop)

    assert isinstance(outbound, PraxisOutbound)


def test_submit_abort_adapter_calls_trading_submit_abort_through_loop() -> None:
    '''The async adapter forwards to `Trading.submit_abort` on the Praxis loop thread.

    `Trading.submit_abort` is sync; the adapter must be schedulable
    via `run_coroutine_threadsafe` from the Nexus thread without
    losing the call.
    '''

    trading = MagicMock(spec=Trading)
    trading.submit_abort = MagicMock()

    loop, thread = _run_loop_in_thread()

    try:
        outbound = _build_praxis_outbound(trading, loop)

        abort = _abort()
        outbound.send_abort(
            command_id=abort.command_id,
            account_id=abort.account_id,
            reason=abort.reason,
            created_at=abort.created_at,
        )

        assert trading.submit_abort.call_count == 1
        forwarded = trading.submit_abort.call_args.args[0]
        assert isinstance(forwarded, TradeAbort)
        assert forwarded.command_id == abort.command_id
        assert forwarded.account_id == abort.account_id
        assert forwarded.reason == abort.reason
    finally:
        _stop_loop(loop, thread)


def test_get_health_snapshot_passes_through_to_trading() -> None:
    '''`PraxisOutbound.get_health_snapshot(account_id)` reaches `Trading.get_health_snapshot`.'''

    trading = MagicMock(spec=Trading)

    async def fake_get(account_id: str) -> HealthSnapshot:
        assert account_id == 'acct-pt51'
        return _snapshot()

    trading.get_health_snapshot = fake_get

    loop, thread = _run_loop_in_thread()

    try:
        outbound = _build_praxis_outbound(trading, loop)
        snapshot = outbound.get_health_snapshot('acct-pt51')
        assert isinstance(snapshot, HealthSnapshot)
    finally:
        _stop_loop(loop, thread)


def test_send_abort_without_wiring_raises() -> None:
    '''Sanity: a PraxisOutbound built without `submit_abort_fn` rejects send_abort.

    Documents the regression `_build_praxis_outbound` fixes — without
    the wiring, abort submission silently fails at runtime.
    '''

    loop = MagicMock(spec=asyncio.AbstractEventLoop)

    bare = PraxisOutbound(
        submit_fn=MagicMock(),
        loop=loop,
    )

    with pytest.raises(RuntimeError, match='submit_abort_fn'):
        bare.send_abort(
            command_id='cmd-x',
            account_id='acct-x',
            reason='shutdown',
            created_at=datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC),
        )
