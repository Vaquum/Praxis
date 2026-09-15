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
    SubmitFailureClass,
    TradeStatus,
)
from praxis.core.domain.events import (
    CommandAccepted,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    TradeOutcomeProduced,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.classify_submit_failure import classify_submit_failure
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    OrderBookLevel,
    DuplicateClientOrderIdError,
    LocalOrderRejectedError,
    OrderBookSnapshot,
    OrderRejectedError,
    OrderSubmitTimeoutError,
    TransientError,
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
    mock.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('2')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('2')),),
        last_update_id=1,
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


    @pytest.mark.asyncio
    async def test_an_adapter_rejection_is_recorded_as_one(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''A refusal the venue never saw must say so.

        The exception types already carry this — `LocalOrderRejectedError`
        exists to say the order never reached the venue — and the event
        flattened it into prose alongside the venue's own rejections. A
        consumer could only tell them apart by matching on text, and the two
        want different responses: a filter refusal is a local condition, a
        duplicate client order id is an idempotency condition.
        '''

        adapter.submit_order.side_effect = LocalOrderRejectedError(
            'qty 0.0001 is below lot minimum 0.001',
            venue_code=-1013,
            reason='qty 0.0001 is below lot minimum 0.001',
        )

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        failed = next(
            e for _, e in events if isinstance(e, OrderSubmitFailed)
        )

        assert failed.failure_class is SubmitFailureClass.ADAPTER
        assert failed.venue_code is None, (
            'an order the venue never saw carries no venue code'
        )

    @pytest.mark.asyncio
    async def test_a_venue_rejection_carries_its_code(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
        adapter: AsyncMock,
    ) -> None:
        '''A venue refusal records the code it answered with.

        Recovering the condition from the reason text is what this replaces:
        the code is what a consumer can branch on.
        '''

        adapter.submit_order.side_effect = OrderRejectedError(
            'Account has insufficient balance for requested action.',
            venue_code=-2010,
            reason='insufficient balance',
        )

        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        failed = next(
            e for _, e in events if isinstance(e, OrderSubmitFailed)
        )

        assert failed.failure_class is SubmitFailureClass.VENUE
        assert failed.venue_code == -2010


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


class TestSubmitFailureClassification:

    '''Cover which side a submit failure is attributed to.

    The exception types already say whether the venue ever saw the order.
    A type that does not say must not be guessed into a bucket that an
    alerting rule would then trust.
    '''

    def test_a_local_rejection_is_adapter_side(self) -> None:

        '''The order never reached the venue.'''

        error = LocalOrderRejectedError('filter', -1013, 'LOT_SIZE')

        assert classify_submit_failure(error) == (
            SubmitFailureClass.ADAPTER,
            None,
        )

    def test_a_venue_rejection_keeps_its_code(self) -> None:

        '''The venue answered with a code worth branching on.'''

        error = OrderRejectedError('rejected', -2010, 'INSUFFICIENT_BALANCE')

        assert classify_submit_failure(error) == (
            SubmitFailureClass.VENUE,
            -2010,
        )

    @pytest.mark.parametrize(
        'error',
        [
            OrderSubmitTimeoutError('transport', client_order_id='c-1'),
            TransientError('venue 5xx'),
        ],
    )
    def test_a_transport_failure_is_unknown_not_a_venue_refusal(
        self,
        error: Exception,
    ) -> None:

        '''Transport failed; the venue may or may not hold the order.'''

        assert classify_submit_failure(error) == (
            SubmitFailureClass.UNKNOWN,
            None,
        )

    def test_a_duplicate_id_recovers_the_code_it_was_raised_from(
        self,
    ) -> None:

        '''The adapter raises in place of the venue's own rejection.'''

        cause = OrderRejectedError('dup', -2022, 'Duplicate order sent')
        error = DuplicateClientOrderIdError('duplicate', client_order_id='c-1')
        error.__cause__ = cause

        assert classify_submit_failure(error) == (
            SubmitFailureClass.VENUE,
            -2022,
        )

    def test_a_duplicate_id_without_a_cause_still_classifies(self) -> None:

        '''A refusal with no recoverable code is still the venue's.'''

        error = DuplicateClientOrderIdError('duplicate', client_order_id='c-1')

        assert classify_submit_failure(error) == (
            SubmitFailureClass.VENUE,
            None,
        )

    def test_an_adapter_value_error_is_adapter_side(self) -> None:

        '''Rejected parameters never left the process.'''

        assert classify_submit_failure(
            ValueError('bad quantity'),
        ) == (SubmitFailureClass.ADAPTER, None)

    def test_an_unrecognised_failure_is_not_guessed(self) -> None:

        '''A type that does not say which side refused says unknown.'''

        assert classify_submit_failure(
            RuntimeError('event loop closed'),
        ) == (SubmitFailureClass.UNKNOWN, None)

    def test_no_exception_is_not_guessed(self) -> None:

        '''A caller describing its own failure states no side.'''

        assert classify_submit_failure(None) == (
            SubmitFailureClass.UNKNOWN,
            None,
        )

    def test_a_bool_venue_code_is_refused(self) -> None:

        '''`True` is an int by inheritance but never a venue's code.'''

        with pytest.raises(ValueError, match='venue_code must be an int'):
            OrderSubmitFailed(
                account_id='acc-1',
                timestamp=datetime(2026, 9, 15, tzinfo=UTC),
                client_order_id='c-1',
                reason='rejected',
                failure_class=SubmitFailureClass.VENUE,
                venue_code=True,
            )
