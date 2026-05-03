'''Tests for MAJOR-007 — local filter rejections must reach Nexus as REJECTED.

Pre-fix `BinanceAdapter._validate_order` raised plain `ValueError` for
filter violations; `_process_command` only catches `VenueError` around
`submit_order`, so the ValueError escaped to the worker's broad
catch-all. Result: `CommandAccepted` and `OrderSubmitIntent` were
persisted but no `OrderSubmitFailed` / terminal `TradeOutcomeProduced`
ever followed, capital stayed parked, and `reconcile_orphan_commands`
did not flag it (the intent counted as a "follow-up").

Post-fix: `_validate_order` raises `LocalOrderRejectedError` (a
`VenueError` / `OrderRejectedError` subclass), which the existing
`except VenueError` flow translates into `OrderSubmitFailed` and a
REJECTED `TradeOutcome`. As defense-in-depth,
`reconcile_orphan_commands` now also synthesizes REJECTED for
`OrderSubmitIntent`-without-followup.
'''

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.events import (
    CommandAccepted,
    OrderSubmitIntent,
    OrderSubmitted,
    TradeOutcomeProduced,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    LocalOrderRejectedError,
    SubmitResult,
    VenueAdapter,
)

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1

_CMD_KWARGS: dict[str, Any] = {
    'trade_id': _TRADE,
    'account_id': _ACCT,
    'symbol': 'BTCUSDT',
    'side': OrderSide.BUY,
    'qty': Decimal('1'),
    'order_type': OrderType.LIMIT,
    'execution_mode': ExecutionMode.SINGLE_SHOT,
    'execution_params': SingleShotParams(price=Decimal('50000')),
    'timeout': 300,
    'reference_price': None,
    'maker_preference': MakerPreference.NO_PREFERENCE,
    'stp_mode': STPMode.NONE,
    'created_at': _TS,
}


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='v-1', status=OrderStatus.OPEN, immediate_fills=(),
    )
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine, adapter: AsyncMock,
) -> AsyncGenerator[ExecutionManager, None]:
    em = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    yield em
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


class TestLocalFilterRejectionEndsAsRejected:
    '''M07.3-M07.5: filter violations now produce REJECTED outcomes
    rather than orphaning the command.'''

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'reason',
        [
            'qty 0.0001 is below lot minimum 0.001',
            'qty 0.000012 is not a multiple of lot step 0.0001',
            'price 50000.005 is not a multiple of tick size 0.01',
            'notional 0.1 is below minimum 10',
        ],
    )
    async def test_filter_violation_records_submit_failed_and_rejected(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
        reason: str,
    ) -> None:
        adapter.submit_order.side_effect = LocalOrderRejectedError(
            reason, venue_code=-1013, reason=reason,
        )

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert types == [
            'CommandAccepted',
            'OrderSubmitIntent',
            'OrderSubmitFailed',
            'TradeOutcomeProduced',
        ]
        terminal = next(
            e for _, e in events if isinstance(e, TradeOutcomeProduced)
        )
        assert terminal.status == TradeStatus.REJECTED


class TestReconcileOrphanIntentWithoutFollowup:
    '''M07.2: defense-in-depth — intent-without-followup must be rescued
    at boot just like CommandAccepted-without-intent already is.'''

    @pytest.mark.asyncio
    async def test_intent_without_submitted_or_terminal_synthesizes_rejected(
        self, mgr: ExecutionManager, spine: EventSpine,
    ) -> None:
        '''Replay events where an intent has no follow-up; reconcile
        should emit REJECTED for that command_id.'''

        accepted = CommandAccepted(
            account_id=_ACCT,
            timestamp=_TS,
            command_id='cmd-orphan-intent',
            trade_id=_TRADE,
            strategy_id=None,
        )
        intent = OrderSubmitIntent(
            account_id=_ACCT,
            timestamp=_TS,
            command_id='cmd-orphan-intent',
            trade_id=_TRADE,
            client_order_id='cid-orphan-intent',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal('1'),
            price=Decimal('50000'),
            stop_price=None,
            stop_limit_price=None,
        )
        await spine.append(accepted, _EPOCH)
        await spine.append(intent, _EPOCH)

        replay_events = await spine.read(_EPOCH, after_seq=0)

        mgr.register_account(_ACCT)
        await mgr.reconcile_orphan_commands(_ACCT, replay_events)

        all_events = await spine.read(_EPOCH, after_seq=0)
        terminals = [
            e for _, e in all_events
            if isinstance(e, TradeOutcomeProduced)
            and e.command_id == 'cmd-orphan-intent'
        ]
        assert len(terminals) == 1
        assert terminals[0].status == TradeStatus.REJECTED
        assert terminals[0].reason == 'boot_orphan_command'

    @pytest.mark.asyncio
    async def test_intent_followed_by_submitted_is_not_an_orphan(
        self, mgr: ExecutionManager, spine: EventSpine,
    ) -> None:
        '''When an intent already has an OrderSubmitted follow-up, the
        reconcile must not emit a duplicate REJECTED.'''

        accepted = CommandAccepted(
            account_id=_ACCT,
            timestamp=_TS,
            command_id='cmd-not-orphan',
            trade_id=_TRADE,
            strategy_id=None,
        )
        intent = OrderSubmitIntent(
            account_id=_ACCT,
            timestamp=_TS,
            command_id='cmd-not-orphan',
            trade_id=_TRADE,
            client_order_id='cid-not-orphan',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal('1'),
            price=Decimal('50000'),
            stop_price=None,
            stop_limit_price=None,
        )
        submitted = OrderSubmitted(
            account_id=_ACCT,
            timestamp=_TS,
            client_order_id='cid-not-orphan',
            venue_order_id='v-not-orphan',
        )
        await spine.append(accepted, _EPOCH)
        await spine.append(intent, _EPOCH)
        await spine.append(submitted, _EPOCH)

        replay_events = await spine.read(_EPOCH, after_seq=0)

        mgr.register_account(_ACCT)
        await mgr.reconcile_orphan_commands(_ACCT, replay_events)

        all_events = await spine.read(_EPOCH, after_seq=0)
        terminals = [
            e for _, e in all_events
            if isinstance(e, TradeOutcomeProduced)
            and e.command_id == 'cmd-not-orphan'
        ]
        assert terminals == []
