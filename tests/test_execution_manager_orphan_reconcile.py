'''Tests for PT-FIX-30 — boot-time reconciliation of orphan
`CommandAccepted` events.

Pre-fix `submit_command` appended `CommandAccepted` to the spine
(durable) BEFORE writing to the in-memory `runtime.command_queue`,
`_accepted_commands`, `_commands`, and `_command_trade_ids` dicts. A
SIGKILL / OOM in this window left a durable `CommandAccepted` with no
follow-up `OrderSubmitIntent` — Praxis would never submit to the
venue because the in-memory queue was wiped on restart, but the Nexus
launcher's `submitter` had already called
`CapitalController.send_order(reservation_id, command_id)` so the
in-flight order notional stayed locked across restarts.

Post-fix `ExecutionManager.reconcile_orphan_commands` is called by
`Trading._startup_account` after `replay_events`. It scans the per-
account event sequence, finds every `CommandAccepted` that did not
produce an `OrderSubmitIntent` and is not already terminal, and emits
a synthetic `TradeOutcome(REJECTED, reason='boot_orphan_command')`
that flows through `on_trade_outcome` so the launcher's
`OutcomeProcessor` releases the reservation.
'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import aiosqlite
import pytest
import pytest_asyncio

from praxis.core.domain.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
    TradeStatus,
)
from praxis.core.domain.events import (
    CommandAccepted,
    OrderSubmitIntent,
    TradeOutcomeProduced,
)
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import SubmitResult, VenueAdapter

_EPOCH = 1
_ACCT = 'acc-1'
_TS = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def spine() -> EventSpine:
    conn = await aiosqlite.connect(':memory:')
    es = EventSpine(conn)
    await es.ensure_schema()
    return es


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.OPEN,
        immediate_fills=(),
    )
    return mock


def _command_accepted(
    command_id: str,
    trade_id: str,
    *,
    strategy_id: str | None = 'strat-1',
) -> CommandAccepted:
    return CommandAccepted(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=command_id,
        trade_id=trade_id,
        strategy_id=strategy_id,
    )


def _order_submit_intent(command_id: str, trade_id: str) -> OrderSubmitIntent:
    return OrderSubmitIntent(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=command_id,
        trade_id=trade_id,
        client_order_id=f'client-{command_id}',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
    )


def _terminal_outcome(command_id: str, trade_id: str) -> TradeOutcomeProduced:
    return TradeOutcomeProduced(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=command_id,
        trade_id=trade_id,
        status=TradeStatus.FILLED,
        reason='filled',
    )


class TestReconcileOrphanCommands:

    @pytest.mark.asyncio
    async def test_orphan_emits_synthetic_rejected_outcome(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''CommandAccepted with no follow-up OrderSubmitIntent is an
        orphan. `reconcile_orphan_commands` must emit a synthetic
        REJECTED outcome via `on_trade_outcome`.'''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
            on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)

        events = [
            (1, _command_accepted('cmd-orphan', 'trade-orphan')),
        ]
        mgr.replay_events(_ACCT, events)

        await mgr.reconcile_orphan_commands(_ACCT, events)

        callback.assert_awaited_once()
        outcome: TradeOutcome = callback.call_args[0][0]
        assert outcome.command_id == 'cmd-orphan'
        assert outcome.trade_id == 'trade-orphan'
        assert outcome.status == TradeStatus.REJECTED
        assert outcome.reason == 'boot_orphan_command'
        assert outcome.filled_qty == Decimal(0)
        assert 'cmd-orphan' in mgr._terminal_commands

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_command_with_intent_is_not_orphan(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''CommandAccepted followed by OrderSubmitIntent is in-flight,
        not an orphan — no synthetic outcome should fire.'''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
            on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)

        events = [
            (1, _command_accepted('cmd-inflight', 'trade-inflight')),
            (2, _order_submit_intent('cmd-inflight', 'trade-inflight')),
        ]
        mgr.replay_events(_ACCT, events)

        await mgr.reconcile_orphan_commands(_ACCT, events)

        callback.assert_not_awaited()
        assert 'cmd-inflight' not in mgr._terminal_commands

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_already_terminal_command_is_not_orphan(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''CommandAccepted with a terminal TradeOutcomeProduced already
        on the spine is fully resolved — no synthetic outcome.'''

        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
            on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)

        events = [
            (1, _command_accepted('cmd-done', 'trade-done')),
            (2, _terminal_outcome('cmd-done', 'trade-done')),
        ]
        mgr.replay_events(_ACCT, events)

        await mgr.reconcile_orphan_commands(_ACCT, events)

        callback.assert_not_awaited()

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_orphan_writes_terminal_event_to_spine(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''The synthetic REJECTED must also land on the spine so a
        subsequent reboot does not reconcile the same orphan twice.'''

        mgr = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)

        events = [
            (1, _command_accepted('cmd-orphan', 'trade-orphan')),
        ]
        mgr.replay_events(_ACCT, events)

        await mgr.reconcile_orphan_commands(_ACCT, events)

        spine_events = await spine.read(_EPOCH, after_seq=0)
        produced_rejects = [
            e for _seq, e in spine_events
            if isinstance(e, TradeOutcomeProduced)
            and e.command_id == 'cmd-orphan'
            and e.status == TradeStatus.REJECTED
        ]
        assert len(produced_rejects) == 1
        assert produced_rejects[0].reason == 'boot_orphan_command'

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_multiple_orphans_each_reconciled(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        callback = AsyncMock()
        mgr = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
            on_trade_outcome=callback,
        )
        mgr.register_account(_ACCT)

        events = [
            (1, _command_accepted('cmd-a', 'trade-a')),
            (2, _command_accepted('cmd-b', 'trade-b')),
            (3, _command_accepted('cmd-c', 'trade-c')),
            (4, _order_submit_intent('cmd-b', 'trade-b')),
        ]
        mgr.replay_events(_ACCT, events)

        await mgr.reconcile_orphan_commands(_ACCT, events)

        assert callback.await_count == 2
        reconciled_ids = {
            call.args[0].command_id for call in callback.await_args_list
        }
        assert reconciled_ids == {'cmd-a', 'cmd-c'}

        await mgr.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_no_callback_means_silent_no_op(
        self,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''Without on_trade_outcome wired, reconciliation still writes
        to spine + marks terminal but does not raise.'''

        mgr = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
        )
        mgr.register_account(_ACCT)

        events = [
            (1, _command_accepted('cmd-orphan', 'trade-orphan')),
        ]
        mgr.replay_events(_ACCT, events)

        await mgr.reconcile_orphan_commands(_ACCT, events)

        assert 'cmd-orphan' in mgr._terminal_commands

        await mgr.unregister_account(_ACCT)
