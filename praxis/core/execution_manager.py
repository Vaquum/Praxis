'''
TradeCommand intake with per-account queues.

Route commands to per-account coroutines via unbounded asyncio queues.
Each registered account owns an independent command queue, priority
queue, and asyncio task.
'''

from __future__ import annotations

import asyncio
import copy
import contextlib
import logging
import threading
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from praxis.core.account_ledger import AccountLedger
from praxis.core.domain.chart_of_accounts import Account
from praxis.core.domain.enums import (
    BracketProtectionStatus,
    CostBasisMethod,
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    SchemeState,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.events import (
    BracketInitialized,
    LadderAmendAborted,
    LadderAmendCompleted,
    LadderAmendInitiated,
    LadderAmendPlanned,
    LadderAmendStateUnknown,
    OrderAmendInitiated,
    ProtectionActive,
    ProtectionAmendRequested,
    ProtectionCancelConfirmed,
    ProtectionFailed,
    ProtectionRemediationDelivered,
    ProtectionReplaceSubmitted,
    ProtectionStateUnknown,
    SchemeFrozen,
    SchemeInitialized,
    SchemeStateChanged,
    CommandAccepted,
    Event,
    FillReceived,
    FlattenInitiated,
    FundTransaction,
    ReconciliationMismatch,
    OrderCanceled,
    OrderExpired,
    OrderQuoteNativeFilled,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    RegisterAccount,
    SliceFailed,
    TradeClosed,
    TradeOutcomeProduced,
)
from nexus.core.domain.bracket_protection_failure_response import (
    BracketProtectionFailureResponse,
)
from nexus.infrastructure.praxis_connector.protection_remediation import (
    ProtectionRemediation,
)

from praxis.core.domain.order import Order
from praxis.core.domain.position import Position
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.trade_pnl import TradePnL
from praxis.core.bracket_exit_command_id import bracket_exit_command_id
from praxis.core.domain.bracket_modify import BracketModify
from praxis.core.domain.bracket_params import BracketParams
from praxis.core.domain.execution_params import ExecutionParams
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.ladder_dca_modify import LadderDcaModify
from praxis.core.domain.ladder_dca_params import LadderDcaParams
from praxis.core.domain.scheduled_vwap_params import ScheduledVwapParams
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.time_dca_params import TimeDcaParams
from praxis.core.domain.twap_params import TwapParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_modify import TradeModify
from praxis.core.domain.iceberg_modify import IcebergModify
from praxis.core.domain.single_shot_modify import SingleShotModify
from praxis.core.domain.twap_modify import TwapModify
from praxis.core.domain.time_dca_modify import TimeDcaModify
from praxis.core.domain.scheduled_vwap_modify import ScheduledVwapModify
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.estimate_slippage import (
    SlippageEstimate,
    estimate_slippage,
    estimate_slippage_for_quote,
)
from praxis.core.generate_client_order_id import (
    command_id_fragment,
    generate_client_order_id,
    validate_command_id_for_client_order_id,
)
from praxis.core.plan_even_slices import plan_even_slices
from praxis.core.plan_weighted_slices import plan_weighted_slices
from praxis.core.trading_state import TradingState
from praxis.core.validate_trade_abort import validate_trade_abort
from praxis.core.validate_trade_modify import validate_trade_modify
from praxis.core.validate_trade_command import validate_trade_command
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    DuplicateClientOrderIdError,
    ImmediateFill,
    NotFoundError,
    OrderSubmitTimeoutError,
    SubmitResult,
    VenueAdapter,
    VenueError,
    VenueOrder,
    VenueOrderList,
)

__all__ = [
    'AccountNotRegisteredError',
    'CommandQueueFullError',
    'ExecutionManager',
    'ExecutionModeNotEnabledError',
]

_log = logging.getLogger(__name__)

_QUEUE_POLL_INTERVAL = 0.1
_ZERO = Decimal(0)
_BPS_MULTIPLIER = Decimal('10000')
_SLIPPAGE_BOOK_LIMIT = 20
_OUTCOME_CALLBACK_MAX_ATTEMPTS = 3
_OUTCOME_CALLBACK_BASE_DELAY = 0.5
_TERMINAL_STATUSES = frozenset({
    TradeStatus.FILLED,
    TradeStatus.CANCELED,
    TradeStatus.REJECTED,
    TradeStatus.EXPIRED,
})
_TERMINAL_ORDER_STATUSES = frozenset({
    OrderStatus.FILLED,
    OrderStatus.CANCELED,
    OrderStatus.EXPIRED,
    OrderStatus.REJECTED,
})
_TERMINAL_ORDER_TO_TRADE_STATUS = {
    OrderStatus.FILLED: TradeStatus.FILLED,
    OrderStatus.CANCELED: TradeStatus.CANCELED,
    OrderStatus.EXPIRED: TradeStatus.EXPIRED,
    OrderStatus.REJECTED: TradeStatus.REJECTED,
}
_BOOT_ORPHAN_REASON = 'boot_orphan_command'
_BOOT_INCOMPLETE_SCHEME_REASON = 'boot_incomplete_scheme'
_SCHEME_MODES = frozenset(
    {ExecutionMode.TWAP, ExecutionMode.TIME_DCA, ExecutionMode.SCHEDULED_VWAP},
)
_MIN_SCHEME_SLICES = 2
_COMMAND_QUEUE_MAXSIZE = 1000
_OCO_LIST_STATUS_REJECT = 'REJECT'
_OCO_LIST_STATUS_ALL_DONE = 'ALL_DONE'
_ORPHAN_SENTINEL_QTY = Decimal(1)
_REPLAY_COMMAND_TIMEOUT_SECONDS = 60
_ONE = Decimal(1)
_BRACKET_ENTRY_SEQUENCE = 0
_BRACKET_PROTECTION_SEQUENCE = 1
_BRACKET_FLATTEN_SEQUENCE = 999
_BRACKET_FIRST_PROTECTION_VERSION = 1
_FLATTEN_BUY_PRICE_BUFFER = Decimal('1.01')


def _aggregate_oco_terminal_status(
    leg_statuses: tuple[OrderStatus, ...],
) -> OrderStatus:
    '''Reduce an ALL_DONE OCO list's leg statuses to one order status.

    Mirrors the precedence `_parse_oco_response` applies to a fresh OCO
    submission: a fill on either leg makes the list FILLED (or
    PARTIALLY_FILLED), otherwise the terminal state is EXPIRED, REJECTED,
    or CANCELED in that order.

    Args:
        leg_statuses (tuple[OrderStatus, ...]): Status of each queried leg.

    Returns:
        OrderStatus: The resolved list-level terminal status.
    '''

    if OrderStatus.FILLED in leg_statuses:
        return OrderStatus.FILLED

    if OrderStatus.PARTIALLY_FILLED in leg_statuses:
        return OrderStatus.PARTIALLY_FILLED

    if OrderStatus.EXPIRED in leg_statuses:
        return OrderStatus.EXPIRED

    if OrderStatus.REJECTED in leg_statuses:
        return OrderStatus.REJECTED

    return OrderStatus.CANCELED


def _utc_now() -> datetime:
    '''Return the current UTC time.'''

    return datetime.now(UTC)


class AccountNotRegisteredError(Exception):
    '''Raised when a command targets an unregistered account_id.'''


class CommandQueueFullError(ValueError):
    '''Raised when a command is rejected because the account queue is full.

    Subclasses `ValueError` so existing inbound-validation handling still
    catches it, while letting a caller distinguish a fail-closed capacity
    rejection from a bad-parameter rejection.
    '''


class ExecutionModeNotEnabledError(ValueError):
    '''Raised when a command uses an execution mode not enabled for the host.

    The per-mode capability gate is default-off: only the modes explicitly
    enabled for this deployment may be driven, so a new mode cannot execute
    live until it is turned on. Subclasses `ValueError` so existing inbound
    handling rejects it, while letting a caller distinguish a disabled-mode
    rejection from a bad-parameter one.
    '''


@dataclass
class _LiveScheme:
    '''In-memory scheduler state for a running multi-slice scheme.

    Holds the resolved per-slice plan and the running aggregates that the
    account coroutine advances between slices. The durable projection of
    the same progress lives in TradingState.schemes, rebuilt from
    SchemeInitialized and SchemeStateChanged on replay.
    '''

    command: TradeCommand
    slice_qtys: list[Decimal]
    slices_total: int
    interval_seconds: int
    cursor: int = 0
    active_children: set[str] = field(default_factory=set)
    pending_terminal: tuple[TradeStatus, SchemeState, str | None] | None = None
    next_run_at: datetime | None = None
    deadline: datetime | None = None
    frozen: bool = False
    protection_frozen: bool = False
    state: SchemeState = SchemeState.RUNNING
    amend_generation: int = 0
    amend_phase: str | None = None
    amend_context: _LadderAmendContext | None = None


@dataclass
class _LadderAmendContext:
    '''In-flight ladder-amend state a halt or a restart resumes from.

    Carries the generation being retired and placed, the old grid's rung count
    (how many rungs to retire), the target grid (to plan the remainder), and
    the fixed replacement plan once known. Set when an amend begins and
    rebuilt on boot from the durable amend events, so the shared driver can
    finish a CANCELLING or PLACING amend identically whether it stalled live
    or crashed mid-flight.
    '''

    old_generation: int
    new_generation: int
    old_slices_total: int
    price_levels: tuple[Decimal, ...]
    level_weights: tuple[Decimal, ...]
    planned: list[tuple[int, Decimal, Decimal]] | None = None
    cancel_committed: bool = False


@dataclass
class _LiveBracket:
    '''In-memory state for a bracket awaiting or holding its protection.

    A bracket submits a MARKET entry, then a protective OCO once the entry
    fills. When the entry fills asynchronously (no immediate fill) the
    account coroutine places the protection from the WebSocket fill via
    `_on_bracket_event`; `protection_placed` guards against a double
    placement across the immediate and asynchronous paths.

    Once the protective OCO is live the bracket is retained as the durable
    anchor for a protective-OCO amend: `protection_client_order_id` names the
    resting OCO, `protection_version` counts amend attempts (0 for the
    original placement), `protection_status` tracks the amend state machine,
    and the resolved legs (`current_tp_price`, `current_sl_stop_price`,
    `current_sl_limit_price`) are the snapshot a partial amend merges against.
    `avg_entry_price` is the entry average fill an offset amend resolves from.
    '''

    command: TradeCommand
    entry_client_order_id: str
    protection_placed: bool = False
    protection_client_order_id: str | None = None
    protection_version: int = 0
    protection_status: BracketProtectionStatus = BracketProtectionStatus.ACTIVE
    avg_entry_price: Decimal | None = None
    current_tp_price: Decimal | None = None
    current_sl_stop_price: Decimal | None = None
    current_sl_limit_price: Decimal | None = None
    unknown_since: datetime | None = None
    pending_replacement_client_order_id: str | None = None
    amend_backfill_since: datetime | None = None
    amend_new_list_client_order_id: str | None = None
    amend_tp_price: Decimal | None = None
    amend_sl_stop_price: Decimal | None = None
    amend_sl_limit_price: Decimal | None = None


@dataclass
class _PendingSingleAmend:
    '''A single-order amend held after cancel until its venue fill reconciles.

    When the post-cancel backfill of a fill that raced the cancel cannot be
    reconciled to venue truth, the amend is parked rather than terminalizing the
    old order and placing a replacement against an understated ledger. The
    periodic scan re-drives it — re-query, backfill, then terminalize and place
    the replacement once the projection reaches venue truth.
    '''

    old_client_order_id: str
    new_client_order_id: str
    new_price: Decimal
    new_display: Decimal | None


def _scheme_schedule(params: ExecutionParams) -> tuple[int, int]:
    '''Return (slice count, interval seconds) for a scheme mode.

    TWAP and Time DCA submit a fixed number of equal MARKET children at a
    fixed interval; Scheduled VWAP submits one child per volume weight at a
    fixed interval. Any other params type is a routing bug — the loop
    dispatch admits only `_SCHEME_MODES`.
    '''

    if isinstance(params, TwapParams):
        return params.num_slices, params.interval_seconds

    if isinstance(params, TimeDcaParams):
        return params.num_iterations, params.interval_seconds

    if isinstance(params, ScheduledVwapParams):
        return len(params.volume_weights), params.interval_seconds

    msg = f'not a scheme params type: {type(params).__name__}'
    raise TypeError(msg)


def _plan_scheme_slices(
    params: ExecutionParams,
    total_qty: Decimal,
    slices_total: int,
    lot_step: Decimal | None,
) -> list[Decimal]:
    '''Compute the child quantities for a scheme mode.

    Equal-slice modes divide the total evenly; Scheduled VWAP splits it
    across its volume-weight curve. Both floor each child to the lot step.
    '''

    if isinstance(params, ScheduledVwapParams):
        return plan_weighted_slices(total_qty, params.volume_weights, lot_step)

    return plan_even_slices(total_qty, slices_total, lot_step)


def _ladder_levels(
    params: LadderDcaParams,
    total_qty: Decimal,
    lot_step: Decimal | None,
) -> list[tuple[Decimal, Decimal]]:
    '''Resolve the (quantity, price) pair for each ladder rung.

    The command quantity is split across the rungs — by `level_weights` when
    given, otherwise equally — with each rung's quantity floored to the lot
    step; each rung rests at its explicit `price_levels` entry.

    Args:
        params (LadderDcaParams): The ladder parameters.
        total_qty (Decimal): Total base quantity to work across the rungs.
        lot_step (Decimal | None): Venue LOT_SIZE step, or None when the
            symbol filters are not cached.

    Returns:
        list[tuple[Decimal, Decimal]]: One (quantity, price) pair per rung.
    '''

    if params.level_weights is not None:
        qtys = plan_weighted_slices(total_qty, params.level_weights, lot_step)
    else:
        qtys = plan_even_slices(total_qty, len(params.price_levels), lot_step)

    return list(zip(qtys, params.price_levels, strict=True))


def _rebuild_scheme_params(
    mode: ExecutionMode,
    slices_total: int,
    interval_seconds: int,
    volume_weights: tuple[Decimal, ...],
) -> ExecutionParams:
    '''Reconstruct a scheme mode's params for boot resume.

    An equal-slice scheme's params are fully determined by its slice count
    and interval; a Scheduled VWAP scheme also needs its persisted volume
    weights, since the weighted grid cannot be recomputed from the slice
    count alone. All are persisted on `SchemeInitialized`, so the transient
    command's params need not be stored to resume the schedule.
    '''

    if mode is ExecutionMode.TWAP:
        return TwapParams(num_slices=slices_total, interval_seconds=interval_seconds)

    if mode is ExecutionMode.TIME_DCA:
        return TimeDcaParams(num_iterations=slices_total, interval_seconds=interval_seconds)

    if mode is ExecutionMode.SCHEDULED_VWAP:
        return ScheduledVwapParams(
            interval_seconds=interval_seconds, volume_weights=volume_weights,
        )

    msg = f'not a resumable scheme mode: {mode.value}'
    raise TypeError(msg)


class _AccountRuntime:
    '''
    Per-account runtime state owned by ExecutionManager.

    Args:
        account_id (str): Account identifier.
        command_queue (asyncio.Queue[TradeCommand]): Bounded queue for commands; a full queue rejects fail-closed at submit.
        priority_queue (asyncio.Queue[TradeAbort | TradeModify]): Unbounded queue for aborts and amends.
        ws_event_queue (asyncio.Queue[Event]): Unbounded queue for WS events.
        trading_state (TradingState): Per-account state projection.
        account_ledger (AccountLedger): Per-account double-entry projection.
    '''

    def __init__(
        self,
        account_id: str,
        command_queue: asyncio.Queue[TradeCommand],
        priority_queue: asyncio.Queue[TradeAbort | TradeModify],
        ws_event_queue: asyncio.Queue[Event],
        trading_state: TradingState,
        account_ledger: AccountLedger,
    ) -> None:
        '''Store per-account queues and projections.'''

        self.account_id = account_id
        self.command_queue = command_queue
        self.priority_queue = priority_queue
        self.ws_event_queue = ws_event_queue
        self.trading_state = trading_state
        self.account_ledger = account_ledger
        self.task: asyncio.Task[None] | None = None
        self.command_to_order: dict[str, str] = {}
        self.schemes: dict[str, _LiveScheme] = {}
        self.brackets: dict[str, _LiveBracket] = {}
        self.amend_counts: dict[str, int] = {}
        self.pending_amends: dict[str, _PendingSingleAmend] = {}
        self.queue_reservations = 0
        self.reconciling = False
        self.poisoned = False
        self.protection_scan_requested = False


class ExecutionManager:
    '''
    Orchestrate TradeCommand intake and per-account queue routing.

    Args:
        event_spine (EventSpine): Append-only event log for persistence.
        epoch_id (int): Current epoch identifier.
        venue_adapter (VenueAdapter): Venue interface for order submission.
        on_trade_outcome (Callable[[TradeOutcome], Awaitable[None]] | None):
            Async callback awaited once per produced TradeOutcome after
            TradeOutcomeProduced is appended to the event spine. None to skip.
            Callback exceptions are logged and suppressed.
        clock (Callable[[], datetime]): Source of the current UTC time
            for event timestamps and staleness gating. Defaults to wall
            clock; a replay run injects a cursor advanced per bar settle.
    '''

    def __init__(
        self,
        event_spine: EventSpine,
        epoch_id: int,
        venue_adapter: VenueAdapter,
        on_trade_outcome: Callable[[TradeOutcome], Awaitable[None]] | None = None,
        clock: Callable[[], datetime] = _utc_now,
        max_slippage_bps: Decimal | None = None,
        enabled_modes: frozenset[ExecutionMode] | None = None,
        protection_failure_response: (
            Callable[[str], BracketProtectionFailureResponse] | None
        ) = None,
        on_protection_remediation: (
            Callable[[ProtectionRemediation], Awaitable[None]] | None
        ) = None,
        restore_deadline_seconds: float = 300.0,
    ) -> None:
        '''Store dependencies and initialize empty account registry.

        Args:
            enabled_modes: Execution modes the host may drive, enforced as a
                per-mode capability gate at submit. None disables the gate
                (all modes allowed) — the mechanism default; the default-off
                policy lives at the production wiring (`TradingConfig`
                defaults to `{SINGLE_SHOT}`), so a mode cannot be driven live
                until it is explicitly enabled there. When a set is given,
                SINGLE_SHOT is always included as the baseline.
        '''

        self._event_spine = event_spine
        self._epoch_id = epoch_id
        self._venue_adapter = venue_adapter
        self._max_slippage_bps = max_slippage_bps
        self._enabled_modes = (
            None
            if enabled_modes is None
            else enabled_modes | {ExecutionMode.SINGLE_SHOT}
        )
        self._on_trade_outcome = on_trade_outcome
        self._clock = clock
        self._protection_failure_response = protection_failure_response
        self._on_protection_remediation = on_protection_remediation
        self._restore_deadline_seconds = restore_deadline_seconds
        self._pending_remediations: dict[str, ProtectionRemediation] = {}
        self._accounts: dict[str, _AccountRuntime] = {}
        self._accepted_commands: dict[str, str] = {}
        self._terminal_commands: set[str] = set()
        self._modifiable_snapshot: dict[str, frozenset[str]] = {}
        self._commands: dict[str, TradeCommand] = {}
        self._aborted_commands: dict[str, str] = {}
        self._command_trade_ids: dict[str, str] = {}
        self._loop_thread_id: int | None = None

    def set_on_trade_outcome(
        self,
        cb: Callable[[TradeOutcome], Awaitable[None]] | None,
    ) -> None:
        '''Replace the on_trade_outcome callback.

        Used by `Trading.set_on_trade_outcome` so the launcher can wire
        `Trading.route_outcome` after `Trading()` is constructed (the
        callback can't reference the Trading instance during
        TradingConfig construction).

        The pre-`start()` guard lives on `Trading.set_on_trade_outcome`
        (the only public entry point that calls this method);
        callers that go through the `Trading` wrapper cannot bypass
        the order constraint. Direct calls to `ExecutionManager` are
        reserved for tests and stay unrestricted.

        Args:
            cb: New callback or `None`. Must accept a `TradeOutcome` and
                return an awaitable.
        '''

        self._on_trade_outcome = cb

    def set_on_protection_remediation(
        self,
        cb: Callable[[ProtectionRemediation], Awaitable[None]] | None,
    ) -> None:
        '''Replace the on_protection_remediation callback.

        Used by `Trading.set_on_protection_remediation` so the launcher can
        wire the per-account Nexus delivery closure after `Trading()` is
        constructed. Must accept a `ProtectionRemediation` and return an
        awaitable.
        '''

        self._on_protection_remediation = cb

    async def _dispatch_outcome_with_retry(
        self,
        outcome: TradeOutcome,
        *,
        source: str,
    ) -> None:
        '''Deliver outcome to `_on_trade_outcome` with bounded retries.

        Round-18 MAJOR-004: pre-fix the callback exception was logged
        and swallowed once, leaving `TradeOutcomeProduced` durably on
        the spine but the consumer (Nexus) unaware. Bounded retry with
        exponential backoff gives transient failures a chance to clear
        before giving up. On full exhaustion, the spine record is the
        durable evidence and a future boot-replay-from-spine pass
        (deferred TD) can re-deliver.
        '''

        if self._on_trade_outcome is None:
            return

        for attempt in range(1, _OUTCOME_CALLBACK_MAX_ATTEMPTS + 1):
            try:
                await self._on_trade_outcome(outcome)
                return
            except asyncio.CancelledError:
                # `CancelledError` is a `BaseException` on every
                # supported Python version, so the broad `except
                # Exception` below does not catch it; the explicit
                # branch documents intent and protects against
                # accidental future widening of the broad catch.
                raise
            except Exception as exc:  # noqa: BLE001 - callback is operator code
                if attempt == _OUTCOME_CALLBACK_MAX_ATTEMPTS:
                    _log.exception(
                        'on_trade_outcome callback exhausted retries (%s): '
                        'command_id=%s attempts=%d last_error=%s — outcome '
                        'durably persisted on spine for future replay',
                        source,
                        outcome.command_id,
                        attempt,
                        exc,
                    )
                    return
                delay = _OUTCOME_CALLBACK_BASE_DELAY * (2 ** (attempt - 1))
                _log.warning(
                    'on_trade_outcome callback failed (%s, attempt %d/%d), '
                    'retrying in %.2fs: command_id=%s error=%s',
                    source,
                    attempt,
                    _OUTCOME_CALLBACK_MAX_ATTEMPTS,
                    delay,
                    outcome.command_id,
                    exc,
                )
                await asyncio.sleep(delay)

    def register_account(self, account_id: str) -> None:
        '''
        Create per-account queues and start account coroutine.

        Args:
            account_id (str): Account identifier to register.

        Raises:
            ValueError: If account_id is empty or already registered.
        '''

        if not account_id:
            msg = 'account_id must be a non-empty string'
            raise ValueError(msg)

        if account_id in self._accounts:
            msg = f"account_id '{account_id}' is already registered"
            raise ValueError(msg)

        if self._loop_thread_id is None:
            self._loop_thread_id = threading.get_ident()

        runtime = _AccountRuntime(
            account_id=account_id,
            command_queue=asyncio.Queue(maxsize=_COMMAND_QUEUE_MAXSIZE),
            priority_queue=asyncio.Queue(),
            ws_event_queue=asyncio.Queue(),
            trading_state=TradingState(account_id),
            account_ledger=AccountLedger(account_id),
        )
        runtime.task = asyncio.create_task(
            self._account_loop(runtime),
            name=f"account-{account_id}",
        )
        self._accounts[account_id] = runtime
        _log.info('account registered: %s', account_id)

    def has_account(self, account_id: str) -> bool:
        '''
        Check whether an account runtime is currently registered.

        Args:
            account_id (str): Account identifier to check.

        Returns:
            bool: True when account_id is currently registered.
        '''

        return account_id in self._accounts

    def active_symbols(self, account_id: str) -> set[str]:
        '''
        Return the set of symbols with open orders or positions for an account.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            set[str]: Unique symbols from open orders and positions.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        symbols: set[str] = set()
        for order in runtime.trading_state.orders.values():
            symbols.add(order.symbol)
        for pos in runtime.trading_state.snapshot_positions().values():
            symbols.add(pos.symbol)
        return symbols

    def get_open_orders(self, account_id: str) -> dict[str, Order]:
        '''
        Return a copy of open orders for an account.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            dict[str, Order]: Open orders keyed by client_order_id.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        return {k: copy.copy(v) for k, v in runtime.trading_state.orders.items()}

    def owned_command_fragments(self, account_id: str) -> set[str]:
        '''Return the command fragments this account has ever accepted.

        Each fragment is the client-order-id slice a command produces via
        `command_id_fragment`. A venue open order is Praxis-owned only if
        its embedded fragment (`praxis_command_fragment`) is in this set:
        the account's accepted commands are the authoritative record of
        what Praxis created, so an order shaped like a Praxis id but tied
        to no accepted command is foreign and left untouched. The set
        retains terminalized commands, since a command reconciled at boot
        can still have a live venue order that must be cancelled.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            set[str]: The account's accepted command fragments.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        if account_id not in self._accounts:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        return {
            command_id_fragment(command_id)
            for command_id, owner in self._accepted_commands.items()
            if owner == account_id
        }

    def in_flight_command_ids(self, account_id: str) -> list[str]:
        '''Return the non-terminal command ids still working for an account.

        Covers every in-flight execution mode: running schemes and ladders
        (`runtime.schemes`), brackets awaiting protection (`runtime.brackets`),
        single-order commands with a live venue order (`command_to_order`),
        and commands accepted but still awaiting dequeue (`_accepted_commands`)
        — the last so a graceful shutdown pre-aborts a queued command to a
        terminal CANCELED outcome instead of tearing down the loop while it
        waits. Commands already terminal are excluded. A shutdown aborts each
        of these so every mode reaches a terminal CANCELED outcome carrying
        its cumulative fills, rather than being torn down with only its venue
        orders cancelled.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            list[str]: In-flight command ids, empty when the account is
                unregistered or has none.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return []

        candidates = (
            set(runtime.schemes)
            | set(runtime.brackets)
            | set(runtime.command_to_order)
            | {
                command_id
                for command_id, owner in self._accepted_commands.items()
                if owner == account_id
            }
        )

        return sorted(
            command_id
            for command_id in candidates
            if command_id not in self._terminal_commands
        )

    def modifiable_command_ids(self, account_id: str) -> list[str]:
        '''Return the command ids a strategy MODIFY may target.

        The Nexus INTAKE stage gates a MODIFY against this set (via the
        launcher provider), so it must hold only commands `_process_modify`
        would actually accept — not the wider shutdown-abort set. A command
        merely accepted and still queued has no resting order or running scheme
        yet, and a MODIFY (drained ahead of commands) would reach it first and
        be silently rejected, so queued commands are excluded: the set is built
        from the running schemes/ladders, the single orders with a live venue
        order, and the ACTIVE-protection brackets. Frozen or mid-amend schemes
        (rejected by `_process_scheme_modify` / `_process_ladder_modify`) and
        each bracket's protective-OCO exit command are removed; a bracket whose
        entry has terminalized but whose protective OCO is still ACTIVE stays
        amendable through its entry id. `in_flight_command_ids` remains the
        separate shutdown-abort set.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            list[str]: Amendable command ids, empty when unregistered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return []

        exit_ids = {
            bracket_exit_command_id(entry_id) for entry_id in runtime.brackets
        }
        live_order_commands = set()
        for command_id, client_order_id in runtime.command_to_order.items():
            order = runtime.trading_state.orders.get(client_order_id)
            if order is not None and order.status not in _TERMINAL_ORDER_STATUSES:
                live_order_commands.add(command_id)

        amendable = (
            set(runtime.schemes)
            | live_order_commands
            | set(runtime.brackets)
        ) - exit_ids
        amendable -= self._terminal_commands
        amendable -= set(runtime.pending_amends)
        amendable -= {
            command_id
            for command_id, scheme in runtime.schemes.items()
            if scheme.protection_frozen
            or scheme.amend_phase is not None
            or scheme.pending_terminal is not None
            or (
                scheme.frozen
                and scheme.command.execution_mode is ExecutionMode.LADDER_DCA
            )
        }

        for entry_id, bracket in runtime.brackets.items():
            protection_active = (
                bracket.protection_placed
                and bracket.protection_client_order_id is not None
                and bracket.protection_status is BracketProtectionStatus.ACTIVE
            )
            if protection_active:
                amendable.add(entry_id)
            else:
                amendable.discard(entry_id)

        return sorted(amendable)

    def modifiable_command_ids_snapshot(self, account_id: str) -> frozenset[str]:
        '''Return the last account-writer-published amendable set, thread-safe.

        `modifiable_command_ids` iterates the runtime dictionaries the account
        writer mutates, so calling it from a Nexus validation thread can tear or
        raise `RuntimeError: dictionary changed size during iteration`. The
        account loop republishes an immutable `frozenset` each iteration; this
        reader returns that snapshot with a single atomic dict lookup, safe to
        call from any thread. An account with no published snapshot yet (or
        already unregistered) reads as empty.

        Args:
            account_id (str): Account identifier to read.

        Returns:
            frozenset[str]: The amendable command ids as of the last loop pass.
        '''

        return self._modifiable_snapshot.get(account_id, frozenset())

    def replay_events(
        self,
        account_id: str,
        events: list[tuple[int, Event]],
    ) -> None:
        '''
        Rebuild per-account state and runtime indices from event history.

        Applies events to TradingState and rebuilds command tracking indices.
        Expects account to be registered but in fresh state (no prior events applied).

        Args:
            account_id (str): Account identifier to replay events for.
            events: Sequence of (seq, event) tuples ordered by sequence number.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        self._bridge_legacy_registration(runtime, events)

        scheme_command_ids = {
            event.command_id
            for _seq, event in events
            if isinstance(event, SchemeInitialized)
        }

        for _seq, event in events:
            self._project(runtime, event)

            if isinstance(event, CommandAccepted):
                self._accepted_commands[event.command_id] = account_id

                if event.strategy_id is not None:
                    runtime.trading_state.trade_strategy_ids[event.trade_id] = event.strategy_id

            if isinstance(event, TradeOutcomeProduced) and event.status in _TERMINAL_STATUSES:
                self._terminal_commands.add(event.command_id)
                self._commands.pop(event.command_id, None)

            if isinstance(event, OrderAmendInitiated):
                runtime.amend_counts[event.command_id] = (
                    runtime.amend_counts.get(event.command_id, 0) + 1
                )
                amended = self._commands.get(event.command_id)
                if amended is not None and isinstance(
                    amended.execution_params, (IcebergParams, SingleShotParams),
                ):
                    self._commands[event.command_id] = replace(
                        amended,
                        execution_params=self._amended_order_params(
                            amended, event.price, event.display_qty,
                        ),
                    )

            if isinstance(event, OrderSubmitIntent):
                self._command_trade_ids[event.command_id] = event.trade_id
                runtime.command_to_order[event.command_id] = event.client_order_id

                if (
                    event.command_id not in self._terminal_commands
                    and event.command_id not in scheme_command_ids
                ):
                    self._commands[event.command_id] = TradeCommand(
                        command_id=event.command_id,
                        trade_id=event.trade_id,
                        account_id=event.account_id,
                        symbol=event.symbol,
                        side=event.side,
                        qty=event.qty,
                        quote_qty=event.quote_qty,
                        order_type=event.order_type,
                        execution_mode=ExecutionMode.SINGLE_SHOT,
                        execution_params=SingleShotParams(
                            price=event.price,
                            stop_price=event.stop_price,
                            stop_limit_price=event.stop_limit_price,
                        ),
                        timeout=_REPLAY_COMMAND_TIMEOUT_SECONDS,
                        reference_price=None,
                        maker_preference=MakerPreference.NO_PREFERENCE,
                        stp_mode=STPMode.NONE,
                        created_at=event.timestamp,
                    )

        self._resume_schemes(runtime, events)
        self._resume_ladders(runtime, events)
        self._resume_brackets(runtime, events)
        self._resume_unknown_protection(runtime, events)

    def _resume_ladders(
        self,
        runtime: _AccountRuntime,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Rebuild live ladder state for non-terminal ladders after replay.

        A ladder posts all of its resting LIMIT rungs at start, so resume
        does not replan or resubmit — it rebuilds the `_LiveScheme` with the
        replayed cursor and the rungs still working (`active_client_order_ids`
        whose order is not terminal), leaving `next_run_at` None so the
        account loop only finalizes it once every rung settles. A ladder with
        a terminal outcome, a non-RUNNING state, too few persisted levels, or
        a malformed init is not resumed.
        '''

        inits: dict[str, SchemeInitialized] = {}
        latest_state: dict[str, SchemeStateChanged] = {}
        terminal_outcomes: set[str] = set()
        frozen_ids: set[str] = set()
        protection_frozen_ids: set[str] = set()
        completed: dict[str, tuple[int, LadderDcaParams, int]] = {}
        inflight: dict[
            str, tuple[LadderAmendInitiated, LadderAmendPlanned | None, str]
        ] = {}
        initiated_by_gen: dict[tuple[str, int], LadderAmendInitiated] = {}
        planned_by_gen: dict[tuple[str, int], LadderAmendPlanned] = {}

        for _seq, event in events:
            if (
                isinstance(event, SchemeInitialized)
                and event.execution_mode is ExecutionMode.LADDER_DCA
            ):
                inits.setdefault(event.command_id, event)
            elif isinstance(event, SchemeStateChanged):
                latest_state[event.command_id] = event
            elif isinstance(event, SliceFailed):
                frozen_ids.add(event.command_id)
            elif isinstance(event, SchemeFrozen):
                frozen_ids.add(event.command_id)
                protection_frozen_ids.add(event.command_id)
            elif isinstance(event, TradeOutcomeProduced) and event.status in _TERMINAL_STATUSES:
                terminal_outcomes.add(event.command_id)
            elif isinstance(event, LadderAmendInitiated):
                initiated_by_gen[(event.command_id, event.generation)] = event
                inflight[event.command_id] = (event, None, 'CANCELLING')
            elif isinstance(event, LadderAmendPlanned):
                planned_by_gen[(event.command_id, event.generation)] = event
                pending = inflight.get(event.command_id)
                if pending is not None:
                    inflight[event.command_id] = (pending[0], event, 'PLACING')
            elif isinstance(event, LadderAmendStateUnknown):
                pending = inflight.get(event.command_id)
                if pending is not None:
                    inflight[event.command_id] = (pending[0], pending[1], event.phase)
            elif isinstance(event, LadderAmendCompleted):
                init_e = initiated_by_gen.get((event.command_id, event.generation))
                planned_e = planned_by_gen.get((event.command_id, event.generation))
                grid_size = len(planned_e.sequences) if planned_e is not None else 0
                grid_params = (
                    LadderDcaParams(
                        price_levels=init_e.price_levels,
                        level_weights=init_e.level_weights or None,
                    )
                    if init_e is not None
                    else None
                )
                if grid_params is not None:
                    completed[event.command_id] = (
                        event.generation, grid_params, grid_size,
                    )
                inflight.pop(event.command_id, None)
            elif isinstance(event, LadderAmendAborted):
                inflight.pop(event.command_id, None)

        for command_id, init in inits.items():
            if command_id in terminal_outcomes:
                continue

            state = latest_state.get(command_id)
            scheme_state = state.state if state is not None else SchemeState.RUNNING
            if scheme_state is not SchemeState.RUNNING:
                continue

            if len(init.price_levels) < _MIN_SCHEME_SLICES:
                continue

            try:
                command = self._ladder_command_from_init(init)
            except ValueError:
                _log.exception(
                    'ladder resume skipped: malformed init: command_id=%s', command_id,
                )
                continue

            deadline = (
                init.timestamp + timedelta(seconds=init.timeout_seconds)
                if init.timeout_seconds > 0
                else None
            )

            pending = inflight.get(command_id)
            if pending is not None:
                _gen, baseline_params, _grid = completed.get(
                    command_id, (0, command.execution_params, init.slices_total),
                )
                assert isinstance(baseline_params, LadderDcaParams)
                scheme = self._resume_inflight_ladder_amend(
                    runtime, command_id,
                    replace(command, execution_params=baseline_params),
                    deadline, pending,
                    command_id in frozen_ids, command_id in protection_frozen_ids,
                )
            else:
                generation, params, grid_size = completed.get(
                    command_id, (0, command.execution_params, init.slices_total),
                )
                assert isinstance(params, LadderDcaParams)
                live_children, posted_count = self._ladder_children_from_projections(
                    runtime, command_id, grid_size, generation,
                )
                scheme = _LiveScheme(
                    command=replace(command, execution_params=params),
                    slice_qtys=[],
                    slices_total=grid_size,
                    interval_seconds=0,
                    cursor=posted_count,
                    active_children=live_children,
                    next_run_at=None,
                    deadline=deadline,
                    frozen=command_id in frozen_ids,
                    protection_frozen=command_id in protection_frozen_ids,
                    amend_generation=generation,
                )

            runtime.schemes[command_id] = scheme
            self._commands[command_id] = scheme.command
            self._accepted_commands[command_id] = runtime.account_id
            self._command_trade_ids[command_id] = init.trade_id

            _log.info(
                'resumed ladder from replay: command_id=%s active=%d frozen=%s '
                'generation=%d amend_phase=%s',
                command_id,
                len(scheme.active_children),
                scheme.frozen,
                scheme.amend_generation,
                scheme.amend_phase,
            )

    def _resume_inflight_ladder_amend(
        self,
        runtime: _AccountRuntime,
        command_id: str,
        command: TradeCommand,
        deadline: datetime | None,
        pending: tuple[LadderAmendInitiated, LadderAmendPlanned | None, str],
        frozen: bool,
        protection_frozen: bool,
    ) -> _LiveScheme:
        '''Rebuild a ladder whose amend was in flight at the crash.

        The old-generation rungs still resting and any new-generation rungs
        already placed are gathered as active children, and the amend context
        (target grid, generation, and the fixed plan when reached) is rebuilt
        from the durable events. The scheme resumes with its `amend_phase` set
        so the reconcile watchdog re-drives it — retiring the rest of the old
        grid and placing the new — exactly as the live driver would have.
        '''

        initiated, planned_event, phase = pending
        old_generation = initiated.generation - 1

        planned = (
            [
                (sequence, price, qty)
                for sequence, price, qty in zip(
                    planned_event.sequences,
                    planned_event.prices,
                    planned_event.qtys,
                    strict=True,
                )
            ]
            if planned_event is not None
            else None
        )
        context = _LadderAmendContext(
            old_generation=old_generation,
            new_generation=initiated.generation,
            old_slices_total=initiated.old_slices_total,
            price_levels=initiated.price_levels,
            level_weights=initiated.level_weights,
            planned=planned,
            cancel_committed=True,
        )

        old_live, _old_posted = self._ladder_children_from_projections(
            runtime, command_id, initiated.old_slices_total, old_generation,
        )
        new_live: set[str] = set()
        if planned_event is not None and planned_event.sequences:
            new_grid_size = max(planned_event.sequences) + 1
            new_live, _new_posted = self._ladder_children_from_projections(
                runtime, command_id, new_grid_size, initiated.generation,
            )

        return _LiveScheme(
            command=command,
            slice_qtys=[],
            slices_total=initiated.old_slices_total,
            interval_seconds=0,
            cursor=initiated.old_slices_total,
            active_children=old_live | new_live,
            next_run_at=None,
            deadline=deadline,
            frozen=frozen,
            protection_frozen=protection_frozen,
            amend_generation=old_generation,
            amend_phase=phase,
            amend_context=context,
        )

    def _ladder_children_from_projections(
        self,
        runtime: _AccountRuntime,
        command_id: str,
        slices_total: int,
        generation: int = 0,
    ) -> tuple[set[str], int]:
        '''Reconstruct a ladder's live rungs and posted count from replay.

        The rungs carry deterministic client order ids, so the durable order
        projections — not a possibly-missing `SchemeStateChanged` — are the
        source of truth on resume: a rung with an order projection was
        submitted (counts toward the cursor), and one still non-terminal is
        active. Deriving from projections means a crash mid-posting (before
        any progress event) never restores an empty, cursor-complete ladder
        that would falsely finalize while its posted rungs rest live.

        Args:
            runtime (_AccountRuntime): Per-account state to read projections.
            command_id (str): The ladder parent command id.
            slices_total (int): The persisted rung count.
            generation (int): Amend generation whose rung ids (retry=generation)
                to scan; 0 is the original grid.

        Returns:
            tuple[set[str], int]: The still-working rung client order ids and
                the number of rungs actually posted.
        '''

        live_children: set[str] = set()
        posted_count = 0
        for index in range(slices_total):
            child_id = generate_client_order_id(
                ExecutionMode.LADDER_DCA, command_id, sequence=index, retry=generation,
            )
            order = self._scheme_child_order(runtime, child_id)
            if order is None:
                continue

            posted_count += 1
            if order.status not in _TERMINAL_ORDER_STATUSES:
                live_children.add(child_id)

        return live_children, posted_count

    def _ladder_command_from_init(self, init: SchemeInitialized) -> TradeCommand:
        '''Rebuild a ladder command from its durable init event for resume.

        Args:
            init (SchemeInitialized): The persisted ladder init event.

        Returns:
            TradeCommand: The reconstructed ladder command.
        '''

        return TradeCommand(
            command_id=init.command_id,
            trade_id=init.trade_id,
            account_id=init.account_id,
            symbol=init.symbol,
            side=init.side,
            qty=init.total_qty,
            order_type=OrderType.LIMIT,
            execution_mode=ExecutionMode.LADDER_DCA,
            execution_params=LadderDcaParams(
                price_levels=init.price_levels,
                level_weights=tuple(init.volume_weights) or None,
            ),
            timeout=_REPLAY_COMMAND_TIMEOUT_SECONDS,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE,
            created_at=init.timestamp,
        )

    def _resume_brackets(
        self,
        runtime: _AccountRuntime,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Rebuild live bracket state for incomplete brackets after replay.

        For each `BracketInitialized` whose protective OCO was not confirmed
        placed, a `_LiveBracket` is registered so the account loop can place
        protection: immediately for an already-filled entry
        (`_place_pending_bracket_protection`), or from `_on_bracket_event`
        when a still-open entry fills. A protective OCO is treated as
        confirmed when its order projection exists and is past SUBMITTING
        (OPEN, filled, canceled, or a REJECTED submit failure); a SUBMITTING
        projection means the submit was persisted but never venue-confirmed
        (a crash between the intent and the response), so it is re-placed —
        the deterministic list client order id makes the retry idempotent via
        the OCO rescue. A bracket that carries a durable `ProtectionFailed` was
        already remediated inline (freeze, flatten, hold) and is not re-placed —
        even if the process crashed before the exit's `OrderSubmitFailed` left
        the OCO projection SUBMITTING — because `recover_incomplete_flattens`
        finishes the flatten from that same marker. A malformed init that cannot
        rebuild valid params is skipped.
        '''

        inits: dict[str, BracketInitialized] = {}
        remediated: set[str] = set()
        for _seq, event in events:
            if isinstance(event, BracketInitialized):
                inits[event.command_id] = event

            elif isinstance(event, ProtectionFailed):
                remediated.add(event.command_id)

        for command_id, init in inits.items():
            if command_id in remediated:
                continue

            entry_client_order_id = generate_client_order_id(
                ExecutionMode.BRACKET, command_id, sequence=_BRACKET_ENTRY_SEQUENCE,
            )
            oco_client_order_id = generate_client_order_id(
                ExecutionMode.BRACKET, command_id, sequence=_BRACKET_PROTECTION_SEQUENCE,
            )

            oco_order = self._scheme_child_order(runtime, oco_client_order_id)
            if oco_order is not None and oco_order.status is not OrderStatus.SUBMITTING:
                continue

            if self._scheme_child_order(runtime, entry_client_order_id) is None:
                continue

            try:
                command = self._bracket_command_from_init(init)
            except ValueError:
                _log.exception(
                    'bracket resume skipped: malformed init params: '
                    'command_id=%s account_id=%s',
                    command_id,
                    runtime.account_id,
                )

                continue

            runtime.brackets[command_id] = _LiveBracket(
                command=command,
                entry_client_order_id=entry_client_order_id,
            )
            _log.info(
                'bracket resumed awaiting protection: command_id=%s account_id=%s',
                command_id,
                runtime.account_id,
            )

    def _resume_unknown_protection(
        self,
        runtime: _AccountRuntime,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Rebuild STATE_UNKNOWN brackets from any unresolved amend phase.

        A protective-OCO amend persists its phase before each venue action
        (`ProtectionAmendRequested` before the cancel, `ProtectionStateUnknown`
        on a halt), so a crash anywhere in the amend — even after the venue
        cancel but before the halt is recorded — leaves an unresolved phase but
        no live `_LiveBracket`, and `_resume_brackets` skips it because the
        pre-amend OCO is already terminal. Every command whose latest protection
        phase is not a terminal `ProtectionActive` / `ProtectionFailed` is
        rebuilt in STATE_UNKNOWN from that phase's candidate list ids (old and
        replacement) and timestamp, so the reconcile watchdog re-queries both
        candidates and resolves it exactly as before the restart.
        '''

        inits: dict[str, BracketInitialized] = {}
        pending: dict[str, ProtectionAmendRequested | ProtectionStateUnknown] = {}
        amends: dict[str, ProtectionAmendRequested] = {}
        for _seq, event in events:
            if isinstance(event, BracketInitialized):
                inits[event.command_id] = event

            elif isinstance(event, (ProtectionAmendRequested, ProtectionStateUnknown)):
                pending[event.command_id] = event
                if isinstance(event, ProtectionAmendRequested):
                    amends[event.command_id] = event

            elif isinstance(event, (ProtectionActive, ProtectionFailed)):
                pending.pop(event.command_id, None)

        for command_id, phase in pending.items():
            if command_id in runtime.brackets:
                continue

            init = inits.get(command_id)
            if init is None:
                continue

            try:
                command = self._bracket_command_from_init(init)
            except ValueError:
                _log.exception(
                    'bracket STATE_UNKNOWN resume skipped: malformed init '
                    'params: command_id=%s account_id=%s',
                    command_id,
                    runtime.account_id,
                )

                continue

            entry_client_order_id = generate_client_order_id(
                ExecutionMode.BRACKET, command_id, sequence=_BRACKET_ENTRY_SEQUENCE,
            )

            entry_order = self._scheme_child_order(runtime, entry_client_order_id)
            avg_entry_price = (
                entry_order.cumulative_notional / entry_order.filled_qty
                if entry_order is not None and entry_order.filled_qty > _ZERO
                else None
            )

            amend = amends.get(command_id)
            current_tp_price: Decimal | None
            current_sl_stop_price: Decimal | None
            current_sl_limit_price: Decimal | None
            if amend is not None:
                current_tp_price = amend.take_profit_price
                current_sl_stop_price = amend.stop_loss_price
                current_sl_limit_price = amend.stop_loss_limit_price
            else:
                current_tp_price = init.take_profit_price
                current_sl_stop_price = init.stop_loss_price
                current_sl_limit_price = init.stop_loss_limit_price

            runtime.brackets[command_id] = _LiveBracket(
                command=command,
                entry_client_order_id=entry_client_order_id,
                protection_placed=True,
                protection_status=BracketProtectionStatus.STATE_UNKNOWN,
                protection_version=phase.protection_version,
                protection_client_order_id=phase.old_list_client_order_id,
                pending_replacement_client_order_id=phase.new_list_client_order_id,
                unknown_since=phase.timestamp,
                avg_entry_price=avg_entry_price,
                current_tp_price=current_tp_price,
                current_sl_stop_price=current_sl_stop_price,
                current_sl_limit_price=current_sl_limit_price,
            )
            _log.info(
                'bracket protection resumed STATE_UNKNOWN for watchdog: '
                'command_id=%s account_id=%s',
                command_id,
                runtime.account_id,
            )

    def _bracket_command_from_init(self, init: BracketInitialized) -> TradeCommand:
        '''Rebuild a bracket command from its durable init event for resume.

        Args:
            init (BracketInitialized): The persisted bracket init event.

        Returns:
            TradeCommand: The reconstructed bracket command.
        '''

        return TradeCommand(
            command_id=init.command_id,
            trade_id=init.trade_id,
            account_id=init.account_id,
            symbol=init.symbol,
            side=init.side,
            qty=init.total_qty,
            order_type=OrderType.MARKET,
            execution_mode=ExecutionMode.BRACKET,
            execution_params=BracketParams(
                take_profit_price=init.take_profit_price,
                take_profit_offset_bps=init.take_profit_offset_bps,
                stop_loss_price=init.stop_loss_price,
                stop_loss_offset_bps=init.stop_loss_offset_bps,
                stop_loss_limit_price=init.stop_loss_limit_price,
            ),
            timeout=init.timeout_seconds or _REPLAY_COMMAND_TIMEOUT_SECONDS,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE,
            created_at=init.timestamp,
        )

    def _resume_schemes(
        self,
        runtime: _AccountRuntime,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Rebuild live scheme state for non-terminal schemes after replay.

        For every `SchemeInitialized` whose latest `SchemeStateChanged` is
        still RUNNING and which has no terminal `TradeOutcomeProduced`, the
        equal-slice params are reconstructed from the persisted mode, slice
        count, and interval; the slice plan is recomputed; and a
        `_LiveScheme` is registered in `runtime.schemes` with the replayed
        cursor, active children, and next-run time so the account loop
        resumes it. A non-terminal scheme in a mode that cannot yet resume,
        or one whose plan can no longer be computed, is left for
        `reconcile_orphan_commands` to terminalize. Terminal-state schemes
        are not resumed.
        '''

        inits: dict[str, SchemeInitialized] = {}
        latest_state: dict[str, SchemeStateChanged] = {}
        terminal_outcomes: set[str] = set()
        frozen_ids: set[str] = set()
        protection_frozen_ids: set[str] = set()

        for _seq, event in events:
            if isinstance(event, SchemeInitialized):
                inits.setdefault(event.command_id, event)
            elif isinstance(event, SchemeStateChanged):
                latest_state[event.command_id] = event
            elif isinstance(event, SliceFailed):
                frozen_ids.add(event.command_id)
            elif isinstance(event, SchemeFrozen):
                frozen_ids.add(event.command_id)
                protection_frozen_ids.add(event.command_id)
            elif isinstance(event, TradeOutcomeProduced) and event.status in _TERMINAL_STATUSES:
                terminal_outcomes.add(event.command_id)

        for command_id, init in inits.items():
            if command_id in terminal_outcomes:
                continue

            state = latest_state.get(command_id)
            scheme_state = state.state if state is not None else SchemeState.RUNNING
            if scheme_state is not SchemeState.RUNNING:
                continue

            if (
                init.execution_mode not in _SCHEME_MODES
                or init.slices_total < _MIN_SCHEME_SLICES
                or init.interval_seconds <= 0
            ):
                continue

            if (
                init.execution_mode is ExecutionMode.SCHEDULED_VWAP
                and len(init.volume_weights) < _MIN_SCHEME_SLICES
            ):
                _log.warning(
                    'cannot resume VWAP scheme without persisted weights: '
                    'command_id=%s',
                    command_id,
                )
                continue

            filters = self._venue_adapter.cached_filters(init.symbol)
            lot_step = filters.lot_step if filters is not None else None
            try:
                rebuilt_params = _rebuild_scheme_params(
                    init.execution_mode,
                    init.slices_total,
                    init.interval_seconds,
                    init.volume_weights,
                )
                slice_qtys = _plan_scheme_slices(
                    rebuilt_params, init.total_qty, init.slices_total, lot_step,
                )
            except ValueError:
                _log.warning(
                    'cannot rebuild or replan scheme on resume; leaving for '
                    'boot cleanup: command_id=%s',
                    command_id,
                )
                continue

            command = TradeCommand(
                command_id=command_id,
                trade_id=init.trade_id,
                account_id=runtime.account_id,
                symbol=init.symbol,
                side=init.side,
                qty=init.total_qty,
                order_type=OrderType.MARKET,
                execution_mode=init.execution_mode,
                execution_params=rebuilt_params,
                timeout=_REPLAY_COMMAND_TIMEOUT_SECONDS,
                reference_price=None,
                maker_preference=MakerPreference.NO_PREFERENCE,
                stp_mode=STPMode.NONE,
                created_at=init.timestamp,
            )

            live_children: set[str] = set()
            if state is not None:
                for child_id in state.active_client_order_ids:
                    order = self._scheme_child_order(runtime, child_id)
                    if order is not None and order.status not in _TERMINAL_ORDER_STATUSES:
                        live_children.add(child_id)

            deadline = (
                init.timestamp + timedelta(seconds=init.timeout_seconds)
                if init.timeout_seconds > 0
                else None
            )

            scheme = _LiveScheme(
                command=command,
                slice_qtys=slice_qtys,
                slices_total=len(slice_qtys),
                interval_seconds=init.interval_seconds,
                cursor=state.cursor if state is not None else 0,
                active_children=live_children,
                next_run_at=state.next_run_at if state is not None else None,
                deadline=deadline,
                frozen=command_id in frozen_ids,
                protection_frozen=command_id in protection_frozen_ids,
            )

            if (
                not scheme.frozen
                and scheme.cursor < scheme.slices_total
                and scheme.next_run_at is None
            ):
                scheme.next_run_at = self._clock()

            runtime.schemes[command_id] = scheme
            self._commands[command_id] = command
            self._accepted_commands[command_id] = runtime.account_id
            self._command_trade_ids[command_id] = init.trade_id

            _log.info(
                'resumed scheme from replay: command_id=%s cursor=%d active=%d frozen=%s',
                command_id,
                scheme.cursor,
                len(scheme.active_children),
                scheme.frozen,
            )

    def _project(self, runtime: _AccountRuntime, event: Event) -> None:
        '''Apply an event to the account's trading-state and ledger projections.

        `RegisterAccount` and `FundTransaction` book into the ledger only;
        `FillReceived` and `TradeClosed` book into both; `ReconciliationMismatch`
        is an alert that books nowhere and advances no projection; every other
        event advances the trading state alone. The ledger is a secondary
        projection, so a projection failure is logged and never propagated
        into the trading path.
        '''

        if isinstance(event, RegisterAccount | FundTransaction):
            self._project_to_ledger(runtime, event)

            return

        if isinstance(event, ReconciliationMismatch):

            return

        runtime.trading_state.apply(event)

        if isinstance(event, FillReceived | TradeClosed):
            self._project_to_ledger(runtime, event)

    def _project_to_ledger(self, runtime: _AccountRuntime, event: Event) -> None:

        try:
            runtime.account_ledger.apply(event)
        except Exception:  # noqa: BLE001 - ledger is a secondary projection; never break trading
            _log.exception(
                'account ledger projection failed: account=%s event=%s',
                runtime.account_id,
                type(event).__name__,
            )

    def _bridge_legacy_registration(
        self,
        runtime: _AccountRuntime,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Register a pre-feature account's ledger with the FIFO default.

        Spine history written before the Account sub-system carries no
        `RegisterAccount` event. When such history books ledger events, the
        strict ledger is registered in memory with the default method so
        replay can project the fills; the synthetic event is never written
        back to the spine.
        '''

        booked = [
            event for _seq, event in events
            if isinstance(event, RegisterAccount | FillReceived | TradeClosed | FundTransaction)
        ]

        if booked and not any(isinstance(event, RegisterAccount) for event in booked):
            runtime.account_ledger.apply(
                RegisterAccount(
                    account_id=runtime.account_id,
                    timestamp=self._clock(),
                    cost_basis_method=CostBasisMethod.FIFO.value,
                )
            )

    async def register_account_on_spine(
        self,
        account_id: str,
        cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO,
    ) -> None:
        '''Append a `RegisterAccount` event and project it into the ledger.

        Called for a genuinely new account so its registration is a durable,
        replayable fact ahead of any booked event. A ledger already
        registered (from replayed history or the legacy bridge) is left
        untouched.

        Args:
            account_id: Account to register on the spine.
            cost_basis_method: Cost-basis method fixed for the account.

        Raises:
            AccountNotRegisteredError: If account_id has no runtime.
        '''

        runtime = self._accounts.get(account_id)

        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        if runtime.account_ledger.cost_basis_method is not None:
            return

        event = RegisterAccount(
            account_id=account_id,
            timestamp=self._clock(),
            cost_basis_method=cost_basis_method.value,
        )
        seq = await self._event_spine.append(event, self._epoch_id)

        if seq is not None:
            self._project(runtime, event)

    async def reconcile_orphan_commands(
        self,
        account_id: str,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Synthesize REJECTED outcomes for orphan command events at boot.

        Two orphan classes are reconciled:

        Class A (PT-FIX-30) — `CommandAccepted` without `OrderSubmitIntent`
        and without terminal `TradeOutcomeProduced`. A SIGKILL between
        `submit_command`'s spine append of `CommandAccepted` and the
        in-memory queue/dict writes leaves a durable `CommandAccepted`
        on the spine with no follow-up. Replay reconstructs
        `_accepted_commands` from the orphan but no outcome will ever
        fire because Praxis never submitted to the venue. Meanwhile the
        Nexus-side launcher had already called
        `CapitalController.send_order(reservation_id, command_id)` so
        the in-flight order notional is locked across restarts.

        Class B (round-18 MAJOR-007) — `OrderSubmitIntent` without
        `OrderSubmitted`, `OrderSubmitFailed`, or terminal
        `TradeOutcomeProduced`. A pre-fix `_validate_order` `ValueError`
        bypassed the `except VenueError` branch and left the intent in
        the spine with no follow-up. Post-MAJOR-007 the local rejection
        raises `LocalOrderRejectedError` (a `VenueError`) so this
        boot-time rescue is defense-in-depth: any future code path that
        again leaves an intent without a follow-up will be cleaned up
        on the next boot rather than stranding capital indefinitely.

        Class C (unresumable scheme) — a `SchemeInitialized` command
        without a terminal `TradeOutcomeProduced` that `replay_events` did
        not resume into `runtime.schemes` (a terminal-state scheme, or one
        whose mode or plan cannot be rebuilt). A non-terminal scheme in a
        resumable mode is resumed by replay and excluded here. An
        unresumable scheme is terminalized on boot — one aggregated
        CANCELED outcome carrying the fills that did settle (from the child
        order projections), which releases the parent reservation while
        preserving the real position. All scheme commands are excluded from
        Class A/B so the scheme-aware Class C is their sole handler.

        Class A/B synthesize `TradeOutcome(REJECTED,
        reason='boot_orphan_command')`; Class C synthesizes
        `TradeOutcome(CANCELED, reason='boot_incomplete_scheme')`. All are
        written to the spine as `TradeOutcomeProduced` and routed through
        `self._on_trade_outcome` so the launcher's `OutcomeProcessor`
        releases Nexus's reservation via lookup of the same `command_id`.

        Args:
            account_id: Account whose events were just replayed.
            events: The same event sequence passed to `replay_events`.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        accepted_trade_ids: dict[str, str] = {}
        intent_trade_ids: dict[str, str] = {}
        intent_clients: dict[str, str] = {}
        completed_via_terminal: set[str] = set()
        completed_via_submit: set[str] = set()

        scheme_trade_ids: dict[str, str] = {}

        for _seq, event in events:
            if isinstance(event, CommandAccepted):
                accepted_trade_ids[event.command_id] = event.trade_id
            elif isinstance(event, SchemeInitialized):
                scheme_trade_ids.setdefault(event.command_id, event.trade_id)
            elif isinstance(event, OrderSubmitIntent):
                intent_trade_ids[event.command_id] = event.trade_id
                intent_clients[event.client_order_id] = event.command_id
            elif isinstance(event, (OrderSubmitted, OrderSubmitFailed)):
                command_id = intent_clients.get(event.client_order_id)
                if command_id is not None:
                    completed_via_submit.add(command_id)
            elif (
                isinstance(event, TradeOutcomeProduced)
                and event.status in _TERMINAL_STATUSES
            ):
                completed_via_terminal.add(event.command_id)

        intent_command_ids = set(intent_trade_ids)
        completed = completed_via_submit | completed_via_terminal
        scheme_command_ids = set(scheme_trade_ids)

        class_a_orphans = [
            cid for cid in accepted_trade_ids
            if cid not in intent_command_ids
            and cid not in completed
            and cid not in scheme_command_ids
        ]
        class_b_orphans = [
            cid for cid in intent_command_ids
            if cid not in completed and cid not in scheme_command_ids
        ]
        class_c_schemes = [
            cid for cid in scheme_trade_ids
            if cid not in completed_via_terminal
            and cid not in runtime.schemes
        ]

        for command_id in class_a_orphans:
            await self._emit_orphan_rejection(
                runtime,
                command_id,
                accepted_trade_ids[command_id],
            )

        for command_id in class_b_orphans:
            trade_id = intent_trade_ids.get(command_id)
            if trade_id is None:
                continue
            await self._emit_orphan_rejection(runtime, command_id, trade_id)

        for command_id in class_c_schemes:
            await self._terminalize_scheme_on_boot(
                runtime,
                command_id,
                scheme_trade_ids[command_id],
            )

    async def _emit_orphan_rejection(
        self,
        runtime: _AccountRuntime,
        command_id: str,
        trade_id: str,
    ) -> None:
        ts = self._clock()
        produced = TradeOutcomeProduced(
            account_id=runtime.account_id,
            timestamp=ts,
            command_id=command_id,
            trade_id=trade_id,
            status=TradeStatus.REJECTED,
            reason=_BOOT_ORPHAN_REASON,
        )
        await self._event_spine.append(produced, self._epoch_id)
        runtime.trading_state.apply(produced)
        self._terminal_commands.add(command_id)

        outcome = TradeOutcome(
            command_id=command_id,
            trade_id=trade_id,
            account_id=runtime.account_id,
            status=TradeStatus.REJECTED,
            target_qty=_ORPHAN_SENTINEL_QTY,
            filled_qty=_ZERO,
            avg_fill_price=None,
            slices_completed=0,
            slices_total=1,
            reason=_BOOT_ORPHAN_REASON,
            created_at=ts,
        )

        _log.info(
            'orphan command reconciled at boot: command_id=%s trade_id=%s account=%s',
            command_id,
            trade_id,
            runtime.account_id,
        )

        await self._dispatch_outcome_with_retry(outcome, source='orphan')

    def _command_fill_totals(
        self,
        runtime: _AccountRuntime,
        command_id: str,
    ) -> tuple[Decimal, Decimal]:
        '''Sum filled qty and notional across every order for a command.

        Reads the order projections (active and closed) for every order whose
        `command_id` matches — a scheme's children, or a single command's
        original and amend-replacement orders — so fills settled across
        multiple orders aggregate to the command total rather than an
        in-memory running sum that a crash discarded.
        '''

        filled_qty = _ZERO
        cumulative_notional = _ZERO

        orders = (
            *runtime.trading_state.orders.values(),
            *runtime.trading_state.closed_orders.values(),
        )
        for order in orders:
            if order.command_id == command_id:
                filled_qty += order.filled_qty
                cumulative_notional += order.cumulative_notional

        return filled_qty, cumulative_notional

    async def _terminalize_scheme_on_boot(
        self,
        runtime: _AccountRuntime,
        command_id: str,
        trade_id: str,
    ) -> None:
        '''Terminalize an unresumable scheme with one CANCELED outcome.

        Reached only for a scheme `replay_events` could not resume (a
        terminal-state scheme, or a mode/plan that cannot be rebuilt). The
        scheme is abandoned safely: a terminal `SchemeStateChanged`
        (CANCELED) plus a single aggregated CANCELED `TradeOutcome` carrying
        the fills that settled. This releases the parent reservation while
        leaving the real position in place; the remaining slices never run.
        '''

        scheme = runtime.trading_state.schemes.get(command_id)
        if scheme is None:
            _log.error(
                'boot scheme terminalize skipped: no projection for '
                'command_id=%s account=%s',
                command_id,
                runtime.account_id,
            )
            return

        ts = self._clock()
        filled_qty, cumulative_notional = self._command_fill_totals(runtime, command_id)
        target_qty = scheme.total_qty

        if filled_qty > target_qty:
            if filled_qty > _ZERO:
                cumulative_notional = cumulative_notional * target_qty / filled_qty
            filled_qty = target_qty

        avg_fill_price = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        changed = SchemeStateChanged(
            account_id=runtime.account_id,
            timestamp=ts,
            command_id=command_id,
            cursor=scheme.cursor,
            filled_qty=filled_qty,
            active_client_order_ids=(),
            next_run_at=None,
            state=SchemeState.CANCELED,
        )
        await self._event_spine.append(changed, self._epoch_id)
        runtime.trading_state.apply(changed)

        produced = TradeOutcomeProduced(
            account_id=runtime.account_id,
            timestamp=ts,
            command_id=command_id,
            trade_id=trade_id,
            status=TradeStatus.CANCELED,
            reason=_BOOT_INCOMPLETE_SCHEME_REASON,
            filled_qty=filled_qty,
            cumulative_notional=cumulative_notional,
            target_qty=target_qty,
        )
        await self._event_spine.append(produced, self._epoch_id)
        runtime.trading_state.apply(produced)
        self._terminal_commands.add(command_id)

        outcome = TradeOutcome(
            command_id=command_id,
            trade_id=trade_id,
            account_id=runtime.account_id,
            status=TradeStatus.CANCELED,
            target_qty=target_qty,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            slices_completed=min(scheme.cursor, scheme.slices_total),
            slices_total=scheme.slices_total,
            reason=_BOOT_INCOMPLETE_SCHEME_REASON,
            created_at=ts,
            cumulative_notional=cumulative_notional,
        )

        _log.info(
            'incomplete scheme terminalized at boot: command_id=%s trade_id=%s '
            'filled=%s account=%s',
            command_id,
            trade_id,
            filled_qty,
            runtime.account_id,
        )

        await self._dispatch_outcome_with_retry(outcome, source='boot_scheme')

    def pull_positions(self, account_id: str) -> dict[tuple[str, str], Position]:
        '''
        Return a detached snapshot of current positions for an account.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            dict[tuple[str, str], Position]: Snapshot of current positions.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        return runtime.trading_state.snapshot_positions()

    def get_account_balances(self, account_id: str) -> dict[Account, Decimal]:
        '''
        Return a detached snapshot of the account-ledger balances.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            dict[Account, Decimal]: Ledger balances by account.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        return runtime.account_ledger.read_balances()

    def get_asset_balances(self, account_id: str) -> dict[str, Decimal]:
        '''
        Return the account's raw per-asset balances for venue reconciliation.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            dict[str, Decimal]: Raw held balance keyed by asset symbol.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        return runtime.account_ledger.read_asset_balances()

    def has_pending_ws_events(self, account_id: str) -> bool:
        '''
        Return whether the account has events queued but not yet projected.

        WS fills and reconciliation events (including fund transactions) are
        appended to the spine and then queued for the account coroutine to
        project. Until that queue drains, the ledger projection lags the
        spine, so a balance comparison against the venue would be stale. A
        True result means the projection is not yet caught up.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            bool: True when events await projection; False when the account is
                unregistered or fully drained.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return False

        return not runtime.ws_event_queue.empty()

    def get_account_trade_pnls(self, account_id: str) -> dict[str, TradePnL]:
        '''
        Return a detached snapshot of per-trade realized P&L for an account.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            dict[str, TradePnL]: Per-trade realized P&L keyed by trade_id.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        return runtime.account_ledger.read_trade_pnls()

    def get_trading_state(self, account_id: str) -> TradingState | None:
        '''
        Return the TradingState for a registered account.

        Args:
            account_id (str): Account identifier to query.

        Returns:
            TradingState | None: Trading state or None if not registered.
        '''

        runtime = self._accounts.get(account_id)
        return runtime.trading_state if runtime is not None else None

    def trade_id_for_command(self, command_id: str) -> str | None:
        '''
        Return the trade_id associated with a command_id.

        Args:
            command_id (str): Command identifier to look up.

        Returns:
            str | None: Trade identifier or None if not found.
        '''

        return self._command_trade_ids.get(command_id)

    def _deadline_at(self, cmd: TradeCommand) -> datetime:
        '''
        Compute the absolute deadline timestamp for a command.

        Args:
            cmd (TradeCommand): Command with timeout and created_at fields

        Returns:
            datetime: Timezone-aware deadline timestamp
        '''

        return cmd.created_at + timedelta(seconds=cmd.timeout)

    def _deadline_exceeded(self, now: datetime, cmd: TradeCommand) -> bool:
        '''
        Determine whether a command deadline has been exceeded.

        Args:
            now (datetime): Current UTC timestamp
            cmd (TradeCommand): Command to check deadline for

        Returns:
            bool: True if current time is at or past the deadline
        '''

        return now >= self._deadline_at(cmd)

    async def unregister_account(self, account_id: str) -> None:
        '''
        Cancel account coroutine and remove per-account state.

        Args:
            account_id (str): Account identifier to unregister.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
        '''

        runtime = self._accounts.pop(account_id, None)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        self._modifiable_snapshot.pop(account_id, None)

        if runtime.task is not None:
            runtime.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await runtime.task

        _log.info('account unregistered: %s', account_id)

    def submit_abort(self, abort: TradeAbort) -> None:
        '''
        Validate and enqueue a TradeAbort to the priority queue.

        Args:
            abort (TradeAbort): Abort instruction targeting a command.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
            ValueError: If command_id is unknown or account_id mismatches.
        '''

        runtime = self._accounts.get(abort.account_id)
        if runtime is None:
            msg = f"account_id '{abort.account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        should_enqueue = validate_trade_abort(
            abort,
            self._accepted_commands,
            self._terminal_commands,
        )

        if not should_enqueue:
            _log.info(
                'abort no-op (command already terminal): command_id=%s',
                abort.command_id,
            )
            return

        runtime.priority_queue.put_nowait(abort)
        _log.info(
            'abort enqueued: command_id=%s account_id=%s',
            abort.command_id,
            abort.account_id,
        )

    def submit_modify(self, modify: TradeModify) -> None:
        '''
        Validate and enqueue a TradeModify to the priority queue.

        Args:
            modify (TradeModify): Amend instruction targeting a command.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
            ValueError: If command_id is unknown, account_id mismatches, or
                the amend parameters do not match the command's mode.
        '''

        runtime = self._accounts.get(modify.account_id)
        if runtime is None:
            msg = f"account_id '{modify.account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        bracket_commands = {
            entry_id: bracket.command
            for entry_id, bracket in runtime.brackets.items()
            if bracket.protection_placed
            and bracket.protection_client_order_id is not None
            and bracket.protection_status is BracketProtectionStatus.ACTIVE
        }

        should_enqueue = validate_trade_modify(
            modify,
            self._commands,
            self._terminal_commands,
            bracket_commands,
        )

        if not should_enqueue:
            _log.info(
                'modify no-op (command already terminal): command_id=%s',
                modify.command_id,
            )
            return

        runtime.priority_queue.put_nowait(modify)
        _log.info(
            'modify enqueued: command_id=%s account_id=%s',
            modify.command_id,
            modify.account_id,
        )

    def enqueue_ws_event(self, account_id: str, event: Event) -> None:
        '''
        Enqueue an external domain event for processing by the account coroutine.

        This is used for events that must be applied via the per-account
        single-writer coroutine, including WebSocket traffic and reconciliation
        events.

        asyncio.Queue.put_nowait is not thread-safe. This method must only
        be called from the event loop thread.

        Args:
            account_id (str): Account identifier.
            event (Event): External domain event to apply.

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
            RuntimeError: If called from outside the event loop thread.
        '''

        if (
            self._loop_thread_id is not None
            and threading.get_ident() != self._loop_thread_id
        ):
            msg = (
                'enqueue_ws_event called from non-event-loop thread. '
                'asyncio.Queue.put_nowait is not thread-safe.'
            )
            raise RuntimeError(msg)

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        runtime.ws_event_queue.put_nowait(event)

    def set_reconciling(self, account_id: str, reconciling: bool) -> None:

        '''
        Gate or release an account's command submission during reconnect reconcile.

        While reconciling the account's writer keeps draining WS and
        reconciliation events but does not dequeue new commands.

        Args:
            account_id (str): Account identifier.
            reconciling (bool): True to gate submission, False to release.

        Raises:
            AccountNotRegisteredError: If the account is not registered.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        runtime.reconciling = reconciling

    def request_protection_scan(self, account_id: str) -> None:
        '''Request the account writer run the protection watchdog next cycle.

        Sets a flag the account loop consumes so the STATE_UNKNOWN watchdog and
        the remediation drain execute on the single account writer rather than
        racing it from the reconcile task. The reconcile task calls this on its
        cadence; an unknown or reconciling account simply runs it on a later
        cycle.

        Args:
            account_id (str): Account identifier.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        runtime.protection_scan_requested = True

    def is_order_capable(self, account_id: str) -> bool:

        '''
        Report whether an account can currently submit orders.

        An account is not order-capable while reconciling, or once poisoned
        by a projection failure (fail-stop until restart).

        Args:
            account_id (str): Account identifier.

        Returns:
            bool: True when the account is registered, not reconciling, and
            not poisoned.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return False

        return not runtime.reconciling and not runtime.poisoned

    async def submit_command(
        self,
        *,
        trade_id: str,
        account_id: str,
        symbol: str,
        side: OrderSide,
        qty: Decimal | None,
        order_type: OrderType,
        execution_mode: ExecutionMode,
        execution_params: ExecutionParams,
        timeout: int,
        reference_price: Decimal | None,
        maker_preference: MakerPreference,
        stp_mode: STPMode,
        created_at: datetime,
        strategy_id: str | None = None,
        quote_qty: Decimal | None = None,
        command_id: str | None = None,
    ) -> str:
        '''
        Accept a command, assign command_id, persist, and enqueue.

        Args:
            trade_id (str): Manager correlation identifier.
            account_id (str): Target account identifier.
            symbol (str): Trading pair symbol.
            side (OrderSide): Order direction.
            qty (Decimal | None): Base-asset quantity. Mutually exclusive
                with `quote_qty`.
            quote_qty (Decimal | None): Quote-asset spend (e.g. USDT)
                for quote-native MARKET BUY. Mutually exclusive with
                `qty`.
            order_type (OrderType): Order type.
            execution_mode (ExecutionMode): Execution strategy.
            execution_params (ExecutionParams): Mode-specific parameters.
            timeout (int): Execution deadline in seconds.
            reference_price (Decimal | None): Optional reference price.
            maker_preference (MakerPreference): Maker/taker preference.
            stp_mode (STPMode): Self-trade prevention mode.
            created_at (datetime): Command creation time.
            strategy_id (str | None): Nexus strategy identifier for position attribution.
            command_id (str | None): Caller-supplied command identifier.
                When supplied it becomes the command's identity verbatim,
                letting the caller register the command in its own state
                before the handoff. It must be non-empty and have at
                least 16 characters after stripping hyphens (the
                `generate_client_order_id` derivation floor — validated
                here so a too-short id is rejected before any state is
                persisted rather than failing at submission). An
                identifier already in use by any accepted or in-memory
                command is rejected rather than regenerated. The
                identity is reserved in the accepted registry before the
                spine append's await (and rolled back if the append
                fails), so two concurrent submissions of the same id
                cannot interleave at the yield — exactly one wins. When
                omitted a UUID is minted exactly as before.

        Returns:
            str: Assigned command_id (the caller-supplied identifier
                when given, otherwise a minted UUID).

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
            CommandQueueFullError: If the account's command queue is at
                capacity; the command is rejected fail-closed before any
                durable state is written.
            ExecutionModeNotEnabledError: If the command's execution mode is
                not enabled by the per-mode capability gate.
            ValueError: If command fails inbound validation, including
                an empty, too-short, or already-in-use caller-supplied
                `command_id`.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        if command_id is not None:
            if not command_id:
                msg = 'caller-supplied command_id must be a non-empty string'
                raise ValueError(msg)

            validate_command_id_for_client_order_id(command_id)

            if (
                command_id in self._accepted_commands
                or command_id in self._commands
            ):
                msg = f"command_id '{command_id}' is already in use"
                raise ValueError(msg)
        else:
            command_id = str(uuid.uuid4())

        cmd = TradeCommand(
            command_id=command_id,
            trade_id=trade_id,
            account_id=account_id,
            symbol=symbol,
            side=side,
            qty=qty,
            quote_qty=quote_qty,
            order_type=order_type,
            execution_mode=execution_mode,
            execution_params=execution_params,
            timeout=timeout,
            reference_price=reference_price,
            maker_preference=maker_preference,
            stp_mode=stp_mode,
            created_at=created_at,
        )

        validate_trade_command(cmd)

        if (
            self._enabled_modes is not None
            and cmd.execution_mode not in self._enabled_modes
        ):
            _log.warning(
                'execution mode not enabled; rejecting command: '
                'account_id=%s mode=%s',
                account_id,
                cmd.execution_mode.value,
            )
            msg = (
                f"execution mode {cmd.execution_mode.value} is not enabled "
                'for this host'
            )
            raise ExecutionModeNotEnabledError(msg)

        if (
            runtime.command_queue.qsize() + runtime.queue_reservations
            >= _COMMAND_QUEUE_MAXSIZE
        ):
            _log.warning(
                'command queue full; rejecting command (fail-closed): '
                'account_id=%s size=%d',
                account_id,
                _COMMAND_QUEUE_MAXSIZE,
            )
            msg = (
                f"command queue for account '{account_id}' is at capacity "
                f'({_COMMAND_QUEUE_MAXSIZE}); rejecting (fail-closed)'
            )
            raise CommandQueueFullError(msg)

        runtime.queue_reservations += 1
        try:
            event = CommandAccepted(
                account_id=account_id,
                timestamp=self._clock(),
                command_id=command_id,
                trade_id=trade_id,
                strategy_id=strategy_id,
            )
            self._accepted_commands[command_id] = account_id

            try:
                await self._event_spine.append(event, self._epoch_id)
            except BaseException:
                self._accepted_commands.pop(command_id, None)
                self._aborted_commands.pop(command_id, None)
                raise

            try:
                runtime.command_queue.put_nowait(cmd)
            except asyncio.QueueFull:
                # Defensive: the reservation guarantees a free slot, so this
                # is unreachable. If a future reservation bug ever let it
                # fire, roll back the durable accept rather than stranding it.
                self._accepted_commands.pop(command_id, None)
                self._aborted_commands.pop(command_id, None)
                msg = (
                    f"command queue for account '{account_id}' is at capacity "
                    f'({_COMMAND_QUEUE_MAXSIZE}); rejecting (fail-closed)'
                )
                raise CommandQueueFullError(msg) from None
        finally:
            runtime.queue_reservations -= 1

        self._commands[command_id] = cmd
        self._command_trade_ids[command_id] = trade_id

        if strategy_id is not None:
            runtime.trading_state.trade_strategy_ids[trade_id] = strategy_id

        _log.info(
            'command accepted: command_id=%s trade_id=%s account_id=%s',
            command_id,
            trade_id,
            account_id,
        )

        return command_id

    async def quiesce(self, account_id: str) -> None:
        '''Wait until an account's queued commands are fully processed.

        Blocks until every command enqueued for `account_id` has been
        submitted, filled, and had its outcome dispatched — the account
        loop calls `command_queue.task_done()` only after
        `_process_command` (which awaits outcome delivery) returns. Used
        by deterministic replay to settle a bar's effects before
        advancing the clock. Returns immediately for an unregistered
        account.

        Args:
            account_id: Account whose command queue to drain.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        await runtime.command_queue.join()

    async def _account_loop(self, runtime: _AccountRuntime) -> None:
        '''
        Drain priority and command queues for a single account.

        Runs until cancelled. Priority queue is drained fully on each
        iteration before taking one item from the command queue.

        Args:
            runtime (_AccountRuntime): Per-account state to process.
        '''

        try:
            while True:
                while not runtime.ws_event_queue.empty():
                    event = runtime.ws_event_queue.get_nowait()
                    if runtime.poisoned:
                        continue
                    try:
                        self._project(runtime, event)
                    except asyncio.CancelledError:
                        raise
                    except Exception:  # noqa: BLE001
                        runtime.poisoned = True
                        _log.exception(
                            'projection failed; poisoning account (fail-stop, '
                            'restart required): event_type=%s account_id=%s',
                            type(event).__name__,
                            runtime.account_id,
                        )
                        continue
                    try:
                        await self._emit_ws_outcome(runtime, event)
                        await self._on_scheme_child_event(runtime, event)
                        await self._on_bracket_event(runtime, event)
                    except asyncio.CancelledError:
                        raise
                    except Exception:  # noqa: BLE001
                        _log.exception(
                            'failed to emit WS-driven TradeOutcome: '
                            'event_type=%s account_id=%s',
                            type(event).__name__,
                            runtime.account_id,
                        )

                while not runtime.priority_queue.empty():
                    control = runtime.priority_queue.get_nowait()
                    _log.info(
                        'priority control received: type=%s command_id=%s account_id=%s',
                        type(control).__name__,
                        control.command_id,
                        runtime.account_id,
                    )
                    try:
                        if isinstance(control, TradeModify):
                            await self._process_modify(runtime, control)
                        else:
                            await self._process_abort(runtime, control)
                    except asyncio.CancelledError:
                        raise
                    except Exception:  # noqa: BLE001
                        _log.exception(
                            'unhandled exception while processing priority control: '
                            'type=%s command_id=%s account_id=%s',
                            type(control).__name__,
                            control.command_id,
                            runtime.account_id,
                        )

                self._modifiable_snapshot[runtime.account_id] = frozenset(
                    self.modifiable_command_ids(runtime.account_id),
                )

                if runtime.reconciling or runtime.poisoned:
                    await asyncio.sleep(_QUEUE_POLL_INTERVAL)
                    continue

                await self._advance_due_schemes(runtime)
                await self._place_pending_bracket_protection(runtime)

                if runtime.protection_scan_requested:
                    runtime.protection_scan_requested = False
                    await self._run_protection_scan(runtime)

                if runtime.command_queue.empty():
                    await asyncio.sleep(_QUEUE_POLL_INTERVAL)
                    continue

                cmd = runtime.command_queue.get_nowait()

                _log.info(
                    'command dequeued: command_id=%s trade_id=%s account_id=%s',
                    cmd.command_id,
                    cmd.trade_id,
                    runtime.account_id,
                )

                try:
                    if cmd.execution_mode in _SCHEME_MODES:
                        if self._deadline_exceeded(self._clock(), cmd):
                            await self._expire_stale_command(runtime, cmd)
                        else:
                            await self._start_scheme(runtime, cmd)
                    elif cmd.execution_mode == ExecutionMode.BRACKET:
                        await self._process_bracket(runtime, cmd)
                    elif cmd.execution_mode == ExecutionMode.ICEBERG:
                        await self._process_iceberg(runtime, cmd)
                    elif cmd.execution_mode == ExecutionMode.LADDER_DCA:
                        if self._deadline_exceeded(self._clock(), cmd):
                            await self._expire_stale_command(runtime, cmd)
                        else:
                            await self._start_ladder(runtime, cmd)
                    else:
                        await self._process_command(runtime, cmd)
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001
                    _log.exception(
                        'unhandled exception while processing command: '
                        'command_id=%s trade_id=%s account_id=%s',
                        cmd.command_id,
                        cmd.trade_id,
                        runtime.account_id,
                    )
                finally:
                    runtime.command_queue.task_done()
        except asyncio.CancelledError:
            _log.info('account loop cancelled: %s', runtime.account_id)
            raise
        finally:
            _log.info('account loop exited: %s', runtime.account_id)

    def _slippage_guard_reason(
        self, cmd: TradeCommand, estimate: SlippageEstimate | None,
    ) -> str | None:
        '''Return a rejection reason when a MARKET order's estimated slippage is too wide.

        Guards MARKET orders only; a LIMIT order self-caps at its price. The
        adverse direction is positive slippage for a BUY and negative for a
        SELL, so both are compared as a positive breach against the limit.
        '''

        if (
            self._max_slippage_bps is None
            or estimate is None
            or cmd.order_type is not OrderType.MARKET
        ):
            return None

        adverse_bps = (
            estimate.slippage_estimate_bps
            if cmd.side is OrderSide.BUY
            else -estimate.slippage_estimate_bps
        )

        if adverse_bps <= self._max_slippage_bps:
            return None

        _log.warning(
            'slippage guard rejected: command_id=%s trade_id=%s adverse_bps=%s max_bps=%s',
            cmd.command_id,
            cmd.trade_id,
            adverse_bps,
            self._max_slippage_bps,
        )

        return f'estimated slippage {adverse_bps} bps exceeds max {self._max_slippage_bps} bps'

    async def _expire_stale_command(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> None:
        '''Expire a scheme command whose deadline passed while it was queued.

        Admission control: a scheme command dequeued after its
        `created_at + timeout` deadline is expired before `_start_scheme`
        runs, so a backlog that outlived its commands neither emits a
        SchemeInitialized nor places any child order. It terminates EXPIRED
        with no fills. (Single-shot commands retain their own post-submit
        deadline handling in `_process_command`.)
        '''

        _log.warning(
            'command expired at dispatch (deadline passed while queued): '
            'command_id=%s trade_id=%s account_id=%s',
            cmd.command_id,
            cmd.trade_id,
            runtime.account_id,
        )

        await self._build_outcome(
            runtime,
            cmd,
            TradeStatus.EXPIRED,
            filled_qty=_ZERO,
            avg_fill_price=None,
            reason='command deadline exceeded before dispatch',
        )

    async def _process_command(  # noqa: PLR0911 - one return per pre-submit rejection reason
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> TradeOutcome:
        '''
        Submit a single order to the venue and report outcome.

        Persist an OrderSubmitIntent before the venue call for crash
        durability, then append OrderSubmitted + FillReceived events
        on success or OrderSubmitFailed on venue error. Emit TradeClosed
        for terminal outcomes with fills, TradeOutcomeProduced for all
        and invoke the on_trade_outcome callback if set.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            cmd (TradeCommand): Command to execute.

        Returns:
            TradeOutcome: Execution outcome for this command.
        '''

        abort_reason = self._aborted_commands.pop(cmd.command_id, None)
        if abort_reason is not None:
            _log.info(
                'command pre-aborted: command_id=%s trade_id=%s',
                cmd.command_id,
                cmd.trade_id,
            )
            return await self._build_outcome(
                runtime,
                cmd,
                TradeStatus.CANCELED,
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason=abort_reason,
            )

        if cmd.execution_mode != ExecutionMode.SINGLE_SHOT:
            reject_reason = (
                f"execution mode {cmd.execution_mode.value} was misrouted to the "
                'single-shot path'
            )
            _log.error(
                'misrouted execution mode reached _process_command: '
                'command_id=%s mode=%s',
                cmd.command_id,
                cmd.execution_mode.value,
            )
            return await self._build_outcome(
                runtime,
                cmd,
                TradeStatus.REJECTED,
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason=reject_reason,
            )

        assert isinstance(cmd.execution_params, SingleShotParams)

        estimate = None
        try:
            book = await self._venue_adapter.query_order_book(
                cmd.symbol,
                limit=_SLIPPAGE_BOOK_LIMIT,
            )
            if cmd.is_quote_native:
                assert cmd.quote_qty is not None
                estimate = estimate_slippage_for_quote(
                    book, cmd.quote_qty, cmd.side, symbol=cmd.symbol,
                )
            else:
                assert cmd.qty is not None
                estimate = estimate_slippage(book, cmd.qty, cmd.side, symbol=cmd.symbol)

            if estimate is None:
                _log.warning(
                    'slippage estimate unavailable: command_id=%s trade_id=%s',
                    cmd.command_id,
                    cmd.trade_id,
                )
            else:
                _log.info(
                    'slippage estimate computed: command_id=%s trade_id=%s slippage_estimate_bps=%s mid_price=%s simulated_vwap=%s',
                    cmd.command_id,
                    cmd.trade_id,
                    estimate.slippage_estimate_bps,
                    estimate.mid_price,
                    estimate.simulated_vwap,
                )
        except VenueError as exc:
            _log.warning(
                'slippage estimate skipped: command_id=%s trade_id=%s reason=%s',
                cmd.command_id,
                cmd.trade_id,
                exc.args[0] if exc.args else str(exc),
            )

        slippage_reject = self._slippage_guard_reason(cmd, estimate)

        if slippage_reject is not None:
            return await self._build_outcome(
                runtime,
                cmd,
                TradeStatus.REJECTED,
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason=slippage_reject,
            )

        client_order_id = generate_client_order_id(
            cmd.execution_mode,
            cmd.command_id,
            sequence=0,
        )
        now = self._clock()

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=now,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            client_order_id=client_order_id,
            symbol=cmd.symbol,
            side=cmd.side,
            order_type=cmd.order_type,
            qty=cmd.qty,
            quote_qty=cmd.quote_qty,
            price=cmd.execution_params.price,
            stop_price=cmd.execution_params.stop_price,
            stop_limit_price=cmd.execution_params.stop_limit_price,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)
        runtime.command_to_order[cmd.command_id] = client_order_id

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                cmd.side,
                cmd.order_type,
                cmd.qty,
                price=cmd.execution_params.price,
                stop_price=cmd.execution_params.stop_price,
                stop_limit_price=cmd.execution_params.stop_limit_price,
                client_order_id=client_order_id,
                quote_qty=cmd.quote_qty,
            )
            post_venue_ts = self._clock()
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError) as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, cmd, client_order_id, exc,
            )
            if rescued is None:
                return await self._record_submit_failed(
                    runtime, cmd, client_order_id, str(exc.args[0]),
                )
            result = rescued
            post_venue_ts = self._clock()
        except VenueError as exc:
            return await self._record_submit_failed(
                runtime, cmd, client_order_id, str(exc.args[0]),
            )
        except ValueError as exc:
            return await self._record_submit_failed(
                runtime, cmd, client_order_id, f'adapter rejected params: {exc}',
            )

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=post_venue_ts,
            client_order_id=client_order_id,
            venue_order_id=result.venue_order_id,
            leg_client_order_ids=result.leg_client_order_ids,
        )
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        for fill in result.immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=post_venue_ts,
                client_order_id=client_order_id,
                venue_order_id=result.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=cmd.command_id,
                symbol=cmd.symbol,
                side=cmd.side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        _log.info(
            'order submitted: client_order_id=%s venue_order_id=%s fills=%d',
            client_order_id,
            result.venue_order_id,
            len(result.immediate_fills),
        )

        filled_qty = sum((f.qty for f in result.immediate_fills), _ZERO)

        if (
            cmd.is_quote_native
            and result.status == OrderStatus.FILLED
            and filled_qty > _ZERO
        ):
            quote_filled = OrderQuoteNativeFilled(
                account_id=cmd.account_id,
                timestamp=post_venue_ts,
                client_order_id=client_order_id,
            )
            await self._event_spine.append(quote_filled, self._epoch_id)
            runtime.trading_state.apply(quote_filled)

        if filled_qty > _ZERO:
            total_notional: Decimal = sum(
                (f.qty * f.price for f in result.immediate_fills),
                _ZERO,
            )
            avg_fill_price: Decimal | None = total_notional / filled_qty
        else:
            total_notional = _ZERO
            avg_fill_price = None

        if estimate is not None and avg_fill_price is not None:
            execution_slippage_bps = (
                (avg_fill_price - estimate.mid_price)
                / estimate.mid_price
                * _BPS_MULTIPLIER
            )
            _log.info(
                'execution slippage computed: command_id=%s trade_id=%s execution_slippage_bps=%s mid_price=%s avg_fill_price=%s',
                cmd.command_id,
                cmd.trade_id,
                execution_slippage_bps,
                estimate.mid_price,
                avg_fill_price,
            )

        if avg_fill_price is not None and cmd.reference_price is not None:
            arrival_slippage_bps = (
                (avg_fill_price - cmd.reference_price)
                / cmd.reference_price
                * _BPS_MULTIPLIER
            )
            _log.info(
                'arrival slippage computed: command_id=%s trade_id=%s arrival_slippage_bps=%s reference_price=%s avg_fill_price=%s',
                cmd.command_id,
                cmd.trade_id,
                arrival_slippage_bps,
                cmd.reference_price,
                avg_fill_price,
            )

        if cmd.is_quote_native:

            if result.status == OrderStatus.FILLED and filled_qty > _ZERO:
                status = TradeStatus.FILLED
            elif filled_qty > _ZERO:
                status = TradeStatus.PARTIAL
            else:
                status = TradeStatus.PENDING
        else:
            assert cmd.qty is not None
            if filled_qty > cmd.qty:
                _log.warning(
                    'overfill detected: command_id=%s filled_qty=%s target_qty=%s; clamping',
                    cmd.command_id,
                    filled_qty,
                    cmd.qty,
                )
                if filled_qty > _ZERO:
                    total_notional = total_notional * cmd.qty / filled_qty
                filled_qty = cmd.qty
            if filled_qty >= cmd.qty:
                status = TradeStatus.FILLED
            elif filled_qty > _ZERO:
                status = TradeStatus.PARTIAL
            else:
                status = TradeStatus.PENDING

        reason: str | None = None
        if status in (
            TradeStatus.PENDING,
            TradeStatus.PARTIAL,
        ) and self._deadline_exceeded(post_venue_ts, cmd):
            status = TradeStatus.EXPIRED
            reason = 'deadline exceeded'
            cancel_confirmed = True
            try:
                if cmd.order_type == OrderType.OCO:
                    await self._venue_adapter.cancel_order_list(
                        cmd.account_id,
                        cmd.symbol,
                        client_order_id=client_order_id,
                    )
                else:
                    await self._venue_adapter.cancel_order(
                        cmd.account_id,
                        cmd.symbol,
                        client_order_id=client_order_id,
                    )
            except NotFoundError:
                pass
            except VenueError as exc:
                reason = f"deadline exceeded; cancel failed: {exc.args[0]}"
                cancel_confirmed = False
            if cancel_confirmed:
                expired = OrderExpired(
                    account_id=cmd.account_id,
                    timestamp=post_venue_ts,
                    client_order_id=client_order_id,
                    venue_order_id=result.venue_order_id,
                )
                await self._event_spine.append(expired, self._epoch_id)
                runtime.trading_state.apply(expired)

        return await self._build_outcome(
            runtime,
            cmd,
            status,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            reason=reason,
            cumulative_notional=total_notional,
        )

    async def _process_bracket(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> TradeOutcome:
        '''Execute a bracket: a MARKET entry, then a protective OCO on fill.

        Submits the entry as a single MARKET order (reusing the persist-
        before-send child protocol). On a filled entry, computes the take-
        profit and stop-loss legs from BracketParams — absolute prices or
        basis-point offsets from the entry average fill — and submits a
        protective OCO on the opposite side for the filled quantity,
        carrying the deterministic bracket exit command id so the leg that
        later fills produces the position-closing EXIT outcome. The bracket
        command's own outcome reports the entry.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            cmd (TradeCommand): Bracket command to execute.

        Returns:
            TradeOutcome: The entry outcome for this command.
        '''

        abort_reason = self._aborted_commands.pop(cmd.command_id, None)
        if abort_reason is not None:
            _log.info(
                'bracket pre-aborted: command_id=%s trade_id=%s',
                cmd.command_id,
                cmd.trade_id,
            )

            return await self._build_outcome(
                runtime,
                cmd,
                TradeStatus.CANCELED,
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason=abort_reason,
            )

        assert isinstance(cmd.execution_params, BracketParams)
        assert cmd.qty is not None

        params = cmd.execution_params
        init = BracketInitialized(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            symbol=cmd.symbol,
            side=cmd.side,
            total_qty=cmd.qty,
            take_profit_price=params.take_profit_price,
            take_profit_offset_bps=params.take_profit_offset_bps,
            stop_loss_price=params.stop_loss_price,
            stop_loss_offset_bps=params.stop_loss_offset_bps,
            stop_loss_limit_price=params.stop_loss_limit_price,
            timeout_seconds=cmd.timeout,
        )
        await self._event_spine.append(init, self._epoch_id)
        runtime.trading_state.apply(init)

        entry_client_order_id = await self._submit_market_slice(
            runtime, cmd, _BRACKET_ENTRY_SEQUENCE, cmd.qty,
        )

        if entry_client_order_id is None:
            return await self._build_outcome(
                runtime,
                cmd,
                TradeStatus.REJECTED,
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason='bracket entry submission failed',
            )

        runtime.command_to_order[cmd.command_id] = entry_client_order_id
        bracket = _LiveBracket(command=cmd, entry_client_order_id=entry_client_order_id)
        runtime.brackets[cmd.command_id] = bracket

        entry_order = self._scheme_child_order(runtime, entry_client_order_id)

        if entry_order is not None and entry_order.status in _TERMINAL_ORDER_STATUSES:
            return await self._settle_bracket_entry(runtime, bracket, entry_order)

        filled_qty = entry_order.filled_qty if entry_order is not None else _ZERO
        cumulative_notional = (
            entry_order.cumulative_notional if entry_order is not None else _ZERO
        )
        avg_fill_price = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        return await self._build_outcome(
            runtime,
            cmd,
            TradeStatus.PENDING,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            reason='bracket entry pending',
            cumulative_notional=cumulative_notional,
        )

    async def _settle_bracket_entry(
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        entry_order: Order,
    ) -> TradeOutcome:
        '''Report a settled bracket entry outcome, then place its protection.

        Runs on the command path when the entry filled immediately (no
        WebSocket round trip). The entry outcome is delivered before the
        protective OCO is placed, mirroring the WebSocket path: a definitive
        protection failure remediates by flattening, whose exit outcome must
        not reach Nexus before the entry it closes has been recorded. A
        terminal entry with no fill leaves nothing to protect and reports the
        venue's terminal state.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            bracket (_LiveBracket): The bracket being settled.
            entry_order (Order): The terminal entry order projection.

        Returns:
            TradeOutcome: The entry outcome for the bracket command.
        '''

        cmd = bracket.command
        assert cmd.qty is not None
        runtime.brackets.pop(cmd.command_id, None)

        filled_qty = entry_order.filled_qty
        cumulative_notional = entry_order.cumulative_notional

        if filled_qty <= _ZERO:
            _log.warning(
                'bracket entry settled without fill; no protection: '
                'command_id=%s status=%s',
                cmd.command_id,
                entry_order.status.value,
            )

            return await self._build_outcome(
                runtime,
                cmd,
                _TERMINAL_ORDER_TO_TRADE_STATUS.get(
                    entry_order.status, TradeStatus.REJECTED,
                ),
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason='bracket entry unfilled',
            )

        avg_entry_price = cumulative_notional / filled_qty

        status = (
            TradeStatus.FILLED if filled_qty >= cmd.qty else TradeStatus.PARTIAL
        )

        outcome = await self._build_outcome(
            runtime,
            cmd,
            status,
            filled_qty=filled_qty,
            avg_fill_price=avg_entry_price,
            reason=None,
            cumulative_notional=cumulative_notional,
        )

        await self._place_bracket_protection(
            runtime, bracket, filled_qty, avg_entry_price,
        )

        return outcome

    async def _on_bracket_event(self, runtime: _AccountRuntime, event: Event) -> None:
        '''Place a bracket's protective OCO once its entry order settles.

        The account coroutine calls this for every WebSocket-driven event.
        When the event settles a tracked bracket's entry order, the
        protective OCO is placed for the filled quantity; the entry outcome
        itself is emitted by `_emit_ws_outcome` on the same event. A terminal
        entry with no fill leaves nothing to protect.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            event (Event): The WebSocket-driven event to inspect.
        '''

        if not isinstance(
            event, FillReceived | OrderCanceled | OrderExpired | OrderRejected,
        ):
            return

        order = (
            runtime.trading_state.orders.get(event.client_order_id)
            or runtime.trading_state.closed_orders.get(event.client_order_id)
        )
        if order is None:
            return

        bracket = runtime.brackets.get(order.command_id)
        if bracket is None or order.client_order_id != bracket.entry_client_order_id:
            return

        if order.status not in _TERMINAL_ORDER_STATUSES:
            return

        runtime.brackets.pop(order.command_id, None)

        if order.filled_qty <= _ZERO:
            _log.warning(
                'bracket entry settled without fill; no protection: '
                'command_id=%s status=%s',
                order.command_id,
                order.status.value,
            )

            return

        avg_entry_price = order.cumulative_notional / order.filled_qty
        await self._place_bracket_protection(
            runtime, bracket, order.filled_qty, avg_entry_price,
        )

    async def _place_pending_bracket_protection(self, runtime: _AccountRuntime) -> None:
        '''Place protection for a resumed bracket whose entry has settled.

        A bracket rebuilt by `_resume_brackets` whose entry order is already
        terminal — its fill arrived before the crash, so no live WebSocket
        event will drive `_on_bracket_event` — has its protective OCO placed
        here on the next account-loop pass. A resumed bracket whose entry is
        still open is left for the fill event; a terminal entry with no fill
        has nothing to protect.
        '''

        for command_id, bracket in list(runtime.brackets.items()):
            if bracket.protection_placed:
                continue

            entry_order = self._scheme_child_order(runtime, bracket.entry_client_order_id)
            if entry_order is None or entry_order.status not in _TERMINAL_ORDER_STATUSES:
                continue

            runtime.brackets.pop(command_id, None)

            if entry_order.filled_qty <= _ZERO:
                continue

            avg_entry_price = entry_order.cumulative_notional / entry_order.filled_qty
            await self._recover_bracket_entry_outcome(runtime, bracket, entry_order)
            await self._place_bracket_protection(
                runtime, bracket, entry_order.filled_qty, avg_entry_price,
            )

    async def _recover_bracket_entry_outcome(
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        entry_order: Order,
    ) -> None:
        '''Emit the entry outcome for a resumed bracket whose fill preceded a crash.

        Replay projects a durable entry `FillReceived` into the trading state
        but does not re-emit its `TradeOutcome`. When boot recovery places
        protection for an already-filled entry whose entry outcome was never
        produced (no terminal `TradeOutcomeProduced` was replayed, so the
        command is not in `_terminal_commands`), emit it now so Nexus receives
        the entry fill it missed. A bracket whose entry outcome was produced
        before the crash is already terminal and is skipped.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            bracket (_LiveBracket): The resumed bracket.
            entry_order (Order): The terminal, filled entry order projection.
        '''

        cmd = bracket.command
        if cmd.command_id in self._terminal_commands:
            return

        assert cmd.qty is not None
        filled_qty = entry_order.filled_qty
        status = (
            TradeStatus.FILLED if filled_qty >= cmd.qty else TradeStatus.PARTIAL
        )

        await self._build_outcome(
            runtime,
            cmd,
            status,
            filled_qty=filled_qty,
            avg_fill_price=entry_order.cumulative_notional / filled_qty,
            reason=None,
            cumulative_notional=entry_order.cumulative_notional,
        )

    async def _place_bracket_protection(
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        qty: Decimal,
        avg_entry_price: Decimal,
    ) -> None:
        '''Submit the protective OCO for a filled bracket entry.

        The OCO is placed on the side opposite the entry for the filled
        quantity, with take-profit and stop-loss legs from BracketParams.
        On success the deterministic exit command id is registered in
        `_commands` and `_command_trade_ids`, so the leg that later fills is
        mapped to a trade id (Trading's WebSocket conversion) and emits a
        position-closing EXIT outcome (`_emit_ws_outcome`) — the identity the
        Nexus exit registration shares. A timeout or duplicate reuses the
        single-shot OCO rescue before failing closed; a definitive failure
        (wrong-side legs, an unsalvageable timeout/duplicate, or a venue error)
        routes the naked entry through the shared remediation — freeze, flatten,
        Nexus hold — rather than leaving it unprotected.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            bracket (_LiveBracket): The bracket being protected.
            qty (Decimal): Filled entry quantity to protect.
            avg_entry_price (Decimal): Entry average fill price.
        '''

        if bracket.protection_placed:
            return

        bracket.protection_placed = True
        cmd = bracket.command

        protective_side = (
            OrderSide.SELL if cmd.side is OrderSide.BUY else OrderSide.BUY
        )
        tp_price, sl_stop_price, sl_limit_price = self._bracket_protective_prices(
            cmd, avg_entry_price,
        )
        exit_command_id = bracket_exit_command_id(cmd.command_id)
        client_order_id = generate_client_order_id(
            cmd.execution_mode,
            cmd.command_id,
            sequence=_BRACKET_PROTECTION_SEQUENCE,
        )
        exit_cmd = self._bracket_exit_command(
            cmd, exit_command_id, protective_side, qty,
            tp_price, sl_stop_price, sl_limit_price,
        )
        now = self._clock()

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=now,
            command_id=exit_command_id,
            trade_id=cmd.trade_id,
            client_order_id=client_order_id,
            symbol=cmd.symbol,
            side=protective_side,
            order_type=OrderType.OCO,
            qty=qty,
            quote_qty=None,
            price=tp_price,
            stop_price=sl_stop_price,
            stop_limit_price=sl_limit_price,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)

        if not self._bracket_legs_valid_for_entry(cmd, tp_price, sl_stop_price, avg_entry_price):
            _log.error(
                'bracket protective legs on the wrong side of the entry fill; '
                'remediating naked entry: command_id=%s side=%s '
                'avg_entry=%s tp=%s sl=%s',
                cmd.command_id,
                cmd.side.value,
                avg_entry_price,
                tp_price,
                sl_stop_price,
            )
            await self._remediate_failed_initial_protection(
                runtime, bracket, exit_cmd, client_order_id, qty,
                'bracket protective legs on the wrong side of the entry fill',
                (),
            )

            return

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                protective_side,
                OrderType.OCO,
                qty,
                price=tp_price,
                stop_price=sl_stop_price,
                stop_limit_price=sl_limit_price,
                client_order_id=client_order_id,
            )
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError) as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, exit_cmd, client_order_id, exc,
            )
            if rescued is None:
                _log.exception(
                    'bracket protective OCO failed; remediating naked entry: '
                    'command_id=%s exit_command_id=%s',
                    cmd.command_id,
                    exit_command_id,
                )
                await self._remediate_failed_initial_protection(
                    runtime, bracket, exit_cmd, client_order_id, qty,
                    f'bracket protective OCO submit failed: {exc.args[0]}',
                    (client_order_id,),
                )

                return

            result = rescued
        except VenueError as exc:
            _log.exception(
                'bracket protective OCO failed; remediating naked entry: '
                'command_id=%s exit_command_id=%s reason=%s',
                cmd.command_id,
                exit_command_id,
                str(exc.args[0]) if exc.args else str(exc),
            )
            await self._remediate_failed_initial_protection(
                runtime, bracket, exit_cmd, client_order_id, qty,
                f'bracket protective OCO failed: {exc}',
                (client_order_id,),
            )

            return

        self._commands[exit_command_id] = exit_cmd
        self._command_trade_ids[exit_command_id] = cmd.trade_id
        runtime.command_to_order[exit_command_id] = client_order_id

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            client_order_id=client_order_id,
            venue_order_id=result.venue_order_id,
            leg_client_order_ids=result.leg_client_order_ids,
        )
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        bracket.protection_client_order_id = client_order_id
        bracket.avg_entry_price = avg_entry_price
        bracket.current_tp_price = tp_price
        bracket.current_sl_stop_price = sl_stop_price
        bracket.current_sl_limit_price = sl_limit_price
        bracket.protection_status = BracketProtectionStatus.ACTIVE
        runtime.brackets[cmd.command_id] = bracket

        for fill in result.immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=client_order_id,
                venue_order_id=result.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=exit_command_id,
                symbol=cmd.symbol,
                side=protective_side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        _log.info(
            'bracket protection placed: command_id=%s exit_command_id=%s '
            'side=%s qty=%s tp=%s sl=%s venue_order_id=%s',
            cmd.command_id,
            exit_command_id,
            protective_side.value,
            qty,
            tp_price,
            sl_stop_price,
            result.venue_order_id,
        )

        oco_order = self._scheme_child_order(runtime, client_order_id)
        if (
            oco_order is not None
            and oco_order.status in _TERMINAL_ORDER_STATUSES
            and oco_order.filled_qty > _ZERO
        ):
            await self._build_outcome(
                runtime,
                exit_cmd,
                _TERMINAL_ORDER_TO_TRADE_STATUS.get(
                    oco_order.status, TradeStatus.FILLED,
                ),
                filled_qty=oco_order.filled_qty,
                avg_fill_price=oco_order.cumulative_notional / oco_order.filled_qty,
                reason=None,
                cumulative_notional=oco_order.cumulative_notional,
            )

    def _bracket_legs_valid_for_entry(
        self,
        cmd: TradeCommand,
        tp_price: Decimal,
        sl_stop_price: Decimal,
        avg_entry_price: Decimal,
    ) -> bool:
        '''Whether the protective legs sit on the correct side of the entry.

        A long's take-profit must sit above and its stop-loss below the
        entry average fill; a short inverts. This re-checks at placement
        time what intake validation cannot: absolute legs valid at submit
        (take-profit above stop-loss) can still land on the wrong side of an
        entry that filled far from the reference — a long take-profit below
        the fill would be an immediately-marketable, nonsensical OCO.

        Args:
            cmd (TradeCommand): The bracket command carrying the side.
            tp_price (Decimal): Resolved take-profit price.
            sl_stop_price (Decimal): Resolved stop-loss trigger price.
            avg_entry_price (Decimal): Entry average fill price.

        Returns:
            bool: True when both legs are on the correct side of the entry.
        '''

        if cmd.side is OrderSide.BUY:
            return tp_price > avg_entry_price and sl_stop_price < avg_entry_price

        return tp_price < avg_entry_price and sl_stop_price > avg_entry_price

    def _bracket_exit_command(
        self,
        cmd: TradeCommand,
        exit_command_id: str,
        protective_side: OrderSide,
        qty: Decimal,
        tp_price: Decimal,
        sl_stop_price: Decimal,
        sl_limit_price: Decimal | None,
    ) -> TradeCommand:
        '''Build the synthetic command registered for a bracket's protective OCO.

        The protective OCO carries this command's id (`exit_command_id`) so
        its position-closing fill produces an EXIT outcome via the shared
        WebSocket-outcome path. It is a lookup-only registration — never
        enqueued for execution.

        Args:
            cmd (TradeCommand): The originating bracket command.
            exit_command_id (str): Deterministic protective-exit command id.
            protective_side (OrderSide): Side opposite the entry.
            qty (Decimal): Filled entry quantity being protected.
            tp_price (Decimal): Take-profit limit price.
            sl_stop_price (Decimal): Stop-loss trigger price.
            sl_limit_price (Decimal | None): Stop-loss limit price, if any.

        Returns:
            TradeCommand: The synthetic protective-exit command.
        '''

        return TradeCommand(
            command_id=exit_command_id,
            trade_id=cmd.trade_id,
            account_id=cmd.account_id,
            symbol=cmd.symbol,
            side=protective_side,
            qty=qty,
            order_type=OrderType.OCO,
            execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(
                price=tp_price,
                stop_price=sl_stop_price,
                stop_limit_price=sl_limit_price,
            ),
            timeout=cmd.timeout,
            reference_price=None,
            maker_preference=cmd.maker_preference,
            stp_mode=cmd.stp_mode,
            created_at=cmd.created_at,
        )

    def _bracket_protective_prices(
        self,
        cmd: TradeCommand,
        avg_entry_price: Decimal,
    ) -> tuple[Decimal, Decimal, Decimal | None]:
        '''Compute the take-profit, stop-loss trigger, and stop-limit prices.

        Take-profit and stop-loss are given as absolute prices or as basis-
        point offsets from the entry average fill. For a long entry the
        take-profit sits above and the stop-loss below the entry; the
        offsets invert for a short. Offset-derived prices are snapped to the
        venue tick so the OCO legs satisfy the PRICE_FILTER; absolute prices
        are assumed already on the tick grid.

        Args:
            cmd (TradeCommand): The bracket command carrying BracketParams.
            avg_entry_price (Decimal): Entry average fill price.

        Returns:
            tuple[Decimal, Decimal, Decimal | None]: Take-profit price,
                stop-loss trigger price, and optional stop-limit price.
        '''

        params = cmd.execution_params
        assert isinstance(params, BracketParams)

        profit_direction = _ONE if cmd.side is OrderSide.BUY else -_ONE

        if params.take_profit_price is not None:
            tp_price = params.take_profit_price
        else:
            assert params.take_profit_offset_bps is not None
            tp_price = self._snap_price(
                cmd.symbol,
                avg_entry_price
                * (_ONE + profit_direction * params.take_profit_offset_bps / _BPS_MULTIPLIER),
            )

        if params.stop_loss_price is not None:
            sl_stop_price = params.stop_loss_price
        else:
            assert params.stop_loss_offset_bps is not None
            sl_stop_price = self._snap_price(
                cmd.symbol,
                avg_entry_price
                * (_ONE - profit_direction * params.stop_loss_offset_bps / _BPS_MULTIPLIER),
            )

        return tp_price, sl_stop_price, params.stop_loss_limit_price

    def _snap_price(self, symbol: str, price: Decimal) -> Decimal:
        '''Snap a price down to the symbol's tick grid when filters are cached.

        Args:
            symbol (str): Trading pair whose PRICE_FILTER tick applies.
            price (Decimal): Raw price to snap.

        Returns:
            Decimal: The price floored to a tick multiple, or the raw price
                when the symbol's filters are not cached.
        '''

        filters = self._venue_adapter.cached_filters(symbol)
        if filters is None:
            return price

        return (price // filters.tick_size) * filters.tick_size

    async def _process_iceberg(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> TradeOutcome:
        '''Submit a native iceberg LIMIT order and report its outcome.

        Iceberg works the command quantity as a single resting LIMIT order
        carrying Binance's `icebergQty`: the venue shows only `display_qty`
        at a time and refills it from the hidden reserve, preserving queue
        priority. Praxis submits one order for the full quantity at
        `limit_price`; the venue's incremental fills arrive as WebSocket
        `executionReport`s and drive PARTIAL then FILLED outcomes through the
        shared WS-outcome path (the command is registered in `_commands` at
        intake), and a `TradeAbort` cancels the resting order. When
        `display_qty` equals the total there is no hidden reserve, so a plain
        LIMIT order is submitted.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            cmd (TradeCommand): Iceberg command to execute.

        Returns:
            TradeOutcome: The initial outcome (typically PENDING for a
                resting order; FILLED / PARTIAL if it crosses on entry).
        '''

        abort_reason = self._aborted_commands.pop(cmd.command_id, None)
        if abort_reason is not None:
            _log.info(
                'iceberg pre-aborted: command_id=%s trade_id=%s',
                cmd.command_id,
                cmd.trade_id,
            )

            return await self._build_outcome(
                runtime,
                cmd,
                TradeStatus.CANCELED,
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason=abort_reason,
            )

        assert isinstance(cmd.execution_params, IcebergParams)
        assert cmd.qty is not None

        params = cmd.execution_params
        iceberg_qty = params.display_qty if params.display_qty < cmd.qty else None
        client_order_id = generate_client_order_id(
            cmd.execution_mode, cmd.command_id, sequence=0,
        )
        now = self._clock()

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=now,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            client_order_id=client_order_id,
            symbol=cmd.symbol,
            side=cmd.side,
            order_type=OrderType.LIMIT,
            qty=cmd.qty,
            quote_qty=None,
            price=params.limit_price,
            stop_price=None,
            stop_limit_price=None,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)
        runtime.command_to_order[cmd.command_id] = client_order_id

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                cmd.side,
                OrderType.LIMIT,
                cmd.qty,
                price=params.limit_price,
                client_order_id=client_order_id,
                iceberg_qty=iceberg_qty,
            )
            post_venue_ts = self._clock()
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError) as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, cmd, client_order_id, exc,
            )
            if rescued is None:
                return await self._record_submit_failed(
                    runtime, cmd, client_order_id, str(exc.args[0]),
                )
            result = rescued
            post_venue_ts = self._clock()
        except VenueError as exc:
            return await self._record_submit_failed(
                runtime, cmd, client_order_id, str(exc.args[0]),
            )
        except ValueError as exc:
            return await self._record_submit_failed(
                runtime, cmd, client_order_id, f'adapter rejected params: {exc}',
            )

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=post_venue_ts,
            client_order_id=client_order_id,
            venue_order_id=result.venue_order_id,
        )
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        for fill in result.immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=post_venue_ts,
                client_order_id=client_order_id,
                venue_order_id=result.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=cmd.command_id,
                symbol=cmd.symbol,
                side=cmd.side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        order = runtime.trading_state.orders.get(client_order_id)
        filled_qty = order.filled_qty if order is not None else _ZERO
        cumulative_notional = order.cumulative_notional if order is not None else _ZERO
        avg_fill_price = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        if filled_qty >= cmd.qty:
            status = TradeStatus.FILLED
        elif filled_qty > _ZERO:
            status = TradeStatus.PARTIAL
        else:
            status = TradeStatus.PENDING

        return await self._build_outcome(
            runtime,
            cmd,
            status,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            reason=None,
            cumulative_notional=cumulative_notional,
        )

    async def _record_submit_failed(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        client_order_id: str,
        reason: str,
    ) -> TradeOutcome:
        '''Persist `OrderSubmitFailed` and emit a REJECTED `TradeOutcome`.

        Shared sink for submit failures that the rescue path could not
        salvage and for direct venue rejections (round-18 MAJOR-002).
        '''

        await self._append_submit_failed(runtime, cmd, client_order_id, reason)

        return await self._build_outcome(
            runtime,
            cmd,
            TradeStatus.REJECTED,
            filled_qty=_ZERO,
            avg_fill_price=None,
            reason=reason,
        )

    async def _append_submit_failed(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        client_order_id: str,
        reason: str,
    ) -> None:
        '''Persist an `OrderSubmitFailed` event and apply it, no outcome.

        The event-only half of a submit failure. Single-shot follows it
        with a REJECTED `TradeOutcome`; a scheme slice defers the outcome
        to the scheme's single terminal emission, so it stops here.
        '''

        failed = OrderSubmitFailed(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            client_order_id=client_order_id,
            reason=reason,
        )
        await self._event_spine.append(failed, self._epoch_id)
        runtime.trading_state.apply(failed)
        _log.warning(
            'order submit failed: client_order_id=%s reason=%s',
            client_order_id,
            reason,
        )

    async def _rescue_by_client_order_id(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        client_order_id: str,
        trigger: VenueError,
    ) -> SubmitResult | None:
        '''Query the venue by `client_order_id` after a non-idempotent POST failure.

        Round-18 MAJOR-002: when a POST times out at the transport
        layer (`OrderSubmitTimeoutError`) or the venue rejects with
        `-2010 Duplicate clientOrderId`
        (`DuplicateClientOrderIdError`), the venue may have already
        accepted an earlier copy of the order. Synthesizing REJECTED
        without confirming would let the venue carry a live order
        Praxis no longer tracks. The rescue queries the venue with
        the deterministic `client_order_id`; on success the caller
        treats the returned `SubmitResult` as the canonical
        `submit_order` result and continues the normal lifecycle.

        Args:
            runtime: Per-account runtime (logging context).
            cmd: Original command (carries symbol for the query).
            client_order_id: clientOrderId stamped on the original POST.
            trigger: The exception that triggered the rescue
                (logged for operator forensics).

        Returns:
            `SubmitResult` (status from the venue query,
            `immediate_fills=()` because any fills carried at
            confirmation time arrive separately via the WS reconcile
            path) when the venue confirms the order exists.
            None when the venue reports the order does not exist
            (caller must classify as REJECTED), or when the rescue
            query itself fails (caller must classify as REJECTED;
            conservative default — operator will see the warn log
            and the WS reconcile path will repair if the venue
            actually held the order).
        '''

        if cmd.order_type is OrderType.OCO:
            return await self._rescue_oco_by_list_id(
                runtime, cmd, client_order_id, trigger,
            )

        try:
            venue_order = await self._venue_adapter.query_order(
                cmd.account_id,
                cmd.symbol,
                client_order_id=client_order_id,
            )
        except NotFoundError:
            _log.warning(
                'rescue confirmed no venue order: account_id=%s '
                'client_order_id=%s trigger=%s — classifying REJECTED',
                runtime.account_id,
                client_order_id,
                type(trigger).__name__,
            )
            return None
        except VenueError as query_exc:
            _log.exception(
                'rescue query failed: account_id=%s client_order_id=%s '
                'trigger=%s query_error=%s — classifying REJECTED',
                runtime.account_id,
                client_order_id,
                type(trigger).__name__,
                str(query_exc.args[0]) if query_exc.args else str(query_exc),
            )
            return None

        _log.warning(
            'rescue confirmed live venue order: account_id=%s '
            'client_order_id=%s venue_order_id=%s status=%s trigger=%s',
            runtime.account_id,
            client_order_id,
            venue_order.venue_order_id,
            venue_order.status.value,
            type(trigger).__name__,
        )
        return SubmitResult(
            venue_order_id=venue_order.venue_order_id,
            status=venue_order.status,
            immediate_fills=(),
        )

    async def _rescue_oco_by_list_id(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        client_order_id: str,
        trigger: VenueError,
    ) -> SubmitResult | None:
        '''Query an OCO list after a non-idempotent OCO POST failure.

        The OCO analogue of `_rescue_by_client_order_id`: a single-order
        query cannot confirm an OCO, whose durable identity is its
        `listClientOrderId` (the deterministic command id). Queries the
        order list; a REJECT list status or a not-found list means the OCO
        was not accepted (caller classifies REJECTED). An ALL_DONE list is
        terminal — its legs are queried to resolve the true terminal status
        (mirroring the single-order rescue, which passes the venue status
        through rather than forcing OPEN); an EXECUTING list is still live,
        so the status is OPEN. In every confirmed case `immediate_fills` is
        empty because trade-level fills arrive separately via the reconcile
        path, keyed by the leg client order ids.
        '''

        try:
            order_list = await self._venue_adapter.query_order_list(
                cmd.account_id,
                list_client_order_id=client_order_id,
            )
        except NotFoundError:
            _log.warning(
                'oco rescue confirmed no venue list: account_id=%s '
                'list_client_order_id=%s trigger=%s — classifying REJECTED',
                runtime.account_id,
                client_order_id,
                type(trigger).__name__,
            )
            return None
        except VenueError as query_exc:
            _log.exception(
                'oco rescue query failed: account_id=%s list_client_order_id=%s '
                'trigger=%s query_error=%s — classifying REJECTED',
                runtime.account_id,
                client_order_id,
                type(trigger).__name__,
                str(query_exc.args[0]) if query_exc.args else str(query_exc),
            )
            return None

        if order_list.list_order_status == _OCO_LIST_STATUS_REJECT:
            _log.warning(
                'oco rescue found rejected list: account_id=%s '
                'list_client_order_id=%s order_list_id=%s — classifying REJECTED',
                runtime.account_id,
                client_order_id,
                order_list.order_list_id,
            )
            return None

        if order_list.list_order_status == _OCO_LIST_STATUS_ALL_DONE:
            status = await self._resolve_terminal_oco_status(
                cmd, client_order_id, order_list,
            )
        else:
            status = OrderStatus.OPEN

        _log.warning(
            'oco rescue confirmed venue list: account_id=%s '
            'list_client_order_id=%s order_list_id=%s list_status=%s '
            'resolved_status=%s trigger=%s',
            runtime.account_id,
            client_order_id,
            order_list.order_list_id,
            order_list.list_order_status,
            status.value,
            type(trigger).__name__,
        )
        return SubmitResult(
            venue_order_id=order_list.order_list_id,
            status=status,
            immediate_fills=(),
            leg_client_order_ids=tuple(
                leg.client_order_id for leg in order_list.legs
            ),
        )

    async def _resolve_terminal_oco_status(
        self,
        cmd: TradeCommand,
        client_order_id: str,
        order_list: VenueOrderList,
    ) -> OrderStatus:
        '''Resolve an ALL_DONE OCO list's terminal status from its legs.

        The order-list query carries no per-leg status, so each leg is
        queried and the results are reduced by
        `_aggregate_oco_terminal_status`. Trade-level fills are not
        reconstructed here — they arrive via the reconcile path keyed by
        the leg client order ids. If any leg query fails the list is
        treated as live (OPEN) so the reconcile path heals it, rather than
        risk mis-terminalizing a leg that may have filled.

        Args:
            cmd (TradeCommand): Original command (carries the account id).
            client_order_id (str): List client order id (logging context).
            order_list (VenueOrderList): The confirmed ALL_DONE list.

        Returns:
            OrderStatus: The resolved terminal status, or OPEN when a leg
                query fails.
        '''

        leg_statuses: list[OrderStatus] = []
        for leg in order_list.legs:
            try:
                venue_order = await self._venue_adapter.query_order(
                    cmd.account_id,
                    leg.symbol,
                    client_order_id=leg.client_order_id,
                )
            except VenueError as query_exc:
                _log.exception(
                    'oco rescue leg query failed: account_id=%s '
                    'list_client_order_id=%s leg_client_order_id=%s '
                    'query_error=%s — treating list live',
                    cmd.account_id,
                    client_order_id,
                    leg.client_order_id,
                    str(query_exc.args[0]) if query_exc.args else str(query_exc),
                )

                return OrderStatus.OPEN

            leg_statuses.append(venue_order.status)

        return _aggregate_oco_terminal_status(tuple(leg_statuses))

    async def _start_scheme(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> None:
        '''Begin a scheme (TWAP, Time DCA, or Scheduled VWAP).

        TWAP and Time DCA submit equal MARKET children at a fixed interval;
        Scheduled VWAP submits one child per volume weight at a fixed
        interval. All share one producer, differing only in slice sizing. A
        pre-submission abort short-circuits to a CANCELED terminal outcome
        before any child is placed. A planning failure (lot grid too coarse
        for the requested split) rejects the command. On success
        `SchemeInitialized` is appended, the live scheduler state is
        registered, and the first slice is submitted synchronously; the
        remaining slices fire from `_advance_due_schemes` at their interval.
        '''

        slices_total, interval_seconds = _scheme_schedule(cmd.execution_params)
        abort_reason = self._aborted_commands.pop(cmd.command_id, None)

        if abort_reason is not None:
            _log.info(
                'scheme pre-aborted before first slice: command_id=%s',
                cmd.command_id,
            )
            await self._emit_scheme_terminal(
                runtime,
                cmd,
                status=TradeStatus.CANCELED,
                filled_qty=_ZERO,
                cumulative_notional=_ZERO,
                slices_completed=0,
                slices_total=slices_total,
                reason=abort_reason,
            )
            return

        assert cmd.qty is not None
        filters = self._venue_adapter.cached_filters(cmd.symbol)
        lot_step = filters.lot_step if filters is not None else None

        try:
            slice_qtys = _plan_scheme_slices(
                cmd.execution_params, cmd.qty, slices_total, lot_step,
            )
        except ValueError as exc:
            _log.warning(
                'scheme slice planning failed: command_id=%s reason=%s',
                cmd.command_id,
                exc,
            )
            await self._emit_scheme_terminal(
                runtime,
                cmd,
                status=TradeStatus.REJECTED,
                filled_qty=_ZERO,
                cumulative_notional=_ZERO,
                slices_completed=0,
                slices_total=slices_total,
                reason=f'scheme slice planning failed: {exc}',
            )
            return

        init = SchemeInitialized(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            execution_mode=cmd.execution_mode,
            symbol=cmd.symbol,
            side=cmd.side,
            total_qty=cmd.qty,
            slices_total=len(slice_qtys),
            interval_seconds=interval_seconds,
            timeout_seconds=cmd.timeout,
            volume_weights=(
                cmd.execution_params.volume_weights
                if isinstance(cmd.execution_params, ScheduledVwapParams)
                else ()
            ),
        )
        await self._event_spine.append(init, self._epoch_id)
        runtime.trading_state.apply(init)

        scheme = _LiveScheme(
            command=cmd,
            slice_qtys=slice_qtys,
            slices_total=len(slice_qtys),
            interval_seconds=interval_seconds,
            deadline=(
                init.timestamp + timedelta(seconds=cmd.timeout)
                if cmd.timeout > 0
                else None
            ),
        )
        runtime.schemes[cmd.command_id] = scheme

        _log.info(
            'scheme started: command_id=%s mode=%s slices=%d interval=%ds',
            cmd.command_id,
            cmd.execution_mode.value,
            scheme.slices_total,
            interval_seconds,
        )

        await self._advance_scheme_guarded(runtime, scheme, self._clock())

    async def _advance_due_schemes(self, runtime: _AccountRuntime) -> None:
        '''Submit the next slice of every scheme whose interval has elapsed.

        Called each account-loop iteration while the account is
        order-capable. Follow-up slices are timer-driven within the
        account coroutine (never re-queued as commands), so this is the
        only path that advances a running scheme after its first slice. A
        scheme that is not due for advancement is checked for finalization
        instead — the backstop that completes a resumed scheme whose
        children all settled during downtime.
        '''

        now = self._clock()

        for scheme in list(runtime.schemes.values()):
            if (
                scheme.pending_terminal is None
                and scheme.amend_phase is None
                and scheme.deadline is not None
                and now >= scheme.deadline
            ):
                await self._expire_scheme(runtime, scheme)
                continue

            due = (
                scheme.state is SchemeState.RUNNING
                and not scheme.frozen
                and scheme.pending_terminal is None
                and scheme.next_run_at is not None
                and now >= scheme.next_run_at
            )

            if due:
                await self._advance_scheme_guarded(runtime, scheme, now)
            else:
                await self._maybe_finalize_scheme(runtime, scheme)

    async def _advance_scheme_guarded(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        now: datetime,
    ) -> None:
        '''Advance one scheme, converting any error into a terminal outcome.

        A raw exception from `_advance_scheme` must never leave the scheme
        RUNNING in `runtime.schemes`: the scheduler would retry the same
        cursor every poll, and a failure between the venue submit and the
        durable `SchemeStateChanged` would re-submit the slice (the
        deterministic client order id makes the venue reject the duplicate,
        but the spin is still wrong). On error the scheme is finalized
        FAILED best-effort and removed from the scheduler so it cannot be
        retried; a boot-time terminalization backstops any append that
        could not complete here.
        '''

        try:
            await self._advance_scheme(runtime, scheme, now)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            command_id = scheme.command.command_id
            _log.exception(
                'scheme advance failed; finalizing FAILED: '
                'command_id=%s account_id=%s',
                command_id,
                runtime.account_id,
            )
            if command_id in runtime.schemes:
                with contextlib.suppress(Exception):
                    await self._finalize_scheme(
                        runtime,
                        scheme,
                        status=TradeStatus.REJECTED,
                        scheme_state=SchemeState.FAILED,
                        reason='scheme advance error',
                    )
                runtime.schemes.pop(command_id, None)

    async def _advance_scheme(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        now: datetime,
    ) -> None:
        '''Submit the slice at the current cursor and advance the schedule.

        The child is submitted, then tracked as active until its order
        reaches a terminal status; its fills — immediate and later
        WebSocket — aggregate into the parent through the child order
        projections. The cursor advances on the interval, independent of
        fills; the scheme finalizes FILLED only once every slice is
        submitted and every child has settled (see
        `_maybe_finalize_scheme`). A slice that cannot be placed freezes the
        scheme (see `_on_slice_failure`): a PARTIAL outcome is reported and
        it waits for the Manager or its deadline.
        '''

        index = scheme.cursor
        slice_qty = scheme.slice_qtys[index]
        cmd = scheme.command

        client_order_id = await self._submit_market_slice(runtime, cmd, index, slice_qty)

        if client_order_id is None:
            await self._on_slice_failure(
                runtime,
                scheme,
                generate_client_order_id(cmd.execution_mode, cmd.command_id, sequence=index),
                f'scheme slice {index} submission failed',
            )
            return

        order = self._scheme_child_order(runtime, client_order_id)
        if order is not None and order.status not in _TERMINAL_ORDER_STATUSES:
            scheme.active_children.add(client_order_id)

        scheme.cursor = index + 1

        if scheme.cursor < scheme.slices_total:
            scheme.next_run_at = now + timedelta(seconds=scheme.interval_seconds)
            await self._append_scheme_progress(runtime, scheme, SchemeState.RUNNING)
        else:
            scheme.next_run_at = None
            if scheme.active_children:
                await self._append_scheme_progress(runtime, scheme, SchemeState.RUNNING)

        await self._maybe_finalize_scheme(runtime, scheme)

    async def _submit_market_slice(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        index: int,
        slice_qty: Decimal,
    ) -> str | None:
        '''Persist-before-send one MARKET child order for a scheme slice.

        Mirrors the single-shot submit protocol for a single child:
        `OrderSubmitIntent` before the venue call, `OrderSubmitted` plus
        one `FillReceived` per immediate fill on success,
        `OrderSubmitFailed` on a definitive failure. Returns the child
        `client_order_id` on success (its fills are applied to the order
        projection, from which the scheme aggregates), or None when the
        slice could not be placed.
        '''

        client_order_id = generate_client_order_id(
            cmd.execution_mode,
            cmd.command_id,
            sequence=index,
        )
        now = self._clock()

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=now,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            client_order_id=client_order_id,
            symbol=cmd.symbol,
            side=cmd.side,
            order_type=OrderType.MARKET,
            qty=slice_qty,
            quote_qty=None,
            price=None,
            stop_price=None,
            stop_limit_price=None,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                cmd.side,
                OrderType.MARKET,
                slice_qty,
                price=None,
                stop_price=None,
                stop_limit_price=None,
                client_order_id=client_order_id,
                quote_qty=None,
            )
            post_venue_ts = self._clock()
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError) as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, cmd, client_order_id, exc,
            )
            if rescued is None:
                await self._append_submit_failed(
                    runtime, cmd, client_order_id, str(exc.args[0]),
                )
                return None
            result = rescued
            post_venue_ts = self._clock()
        except VenueError as exc:
            await self._append_submit_failed(
                runtime, cmd, client_order_id, str(exc.args[0]),
            )
            return None
        except ValueError as exc:
            await self._append_submit_failed(
                runtime, cmd, client_order_id, f'adapter rejected params: {exc}',
            )
            return None

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=post_venue_ts,
            client_order_id=client_order_id,
            venue_order_id=result.venue_order_id,
            leg_client_order_ids=result.leg_client_order_ids,
        )
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        for fill in result.immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=post_venue_ts,
                client_order_id=client_order_id,
                venue_order_id=result.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=cmd.command_id,
                symbol=cmd.symbol,
                side=cmd.side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        _log.info(
            'scheme slice submitted: command_id=%s slice=%d client_order_id=%s fills=%d',
            cmd.command_id,
            index,
            client_order_id,
            len(result.immediate_fills),
        )

        return client_order_id

    async def _start_ladder(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> None:
        '''Begin a Ladder DCA: rest one LIMIT order at every price level.

        Unlike the interval schemes, a ladder posts all of its children at
        once — a static grid of resting LIMIT orders at explicit prices,
        each sized from the level allocation. There is no interval schedule
        (`next_run_at` stays None); the ladder aggregates fills as rungs fill
        and completes once every rung has settled, reusing the shared scheme
        child-settle, finalize, abort, and deadline machinery. A pre-abort
        short-circuits to CANCELED; a planning failure rejects; a rung that
        cannot be placed freezes the ladder (the placed rungs keep resting)
        to await the Manager or the deadline.
        '''

        abort_reason = self._aborted_commands.pop(cmd.command_id, None)
        if abort_reason is not None:
            _log.info('ladder pre-aborted before first rung: command_id=%s', cmd.command_id)
            await self._emit_scheme_terminal(
                runtime, cmd,
                status=TradeStatus.CANCELED,
                filled_qty=_ZERO, cumulative_notional=_ZERO,
                slices_completed=0, slices_total=0, reason=abort_reason,
            )
            return

        assert isinstance(cmd.execution_params, LadderDcaParams)
        assert cmd.qty is not None

        params = cmd.execution_params
        filters = self._venue_adapter.cached_filters(cmd.symbol)
        lot_step = filters.lot_step if filters is not None else None

        try:
            levels = _ladder_levels(params, cmd.qty, lot_step)
        except ValueError as exc:
            _log.warning('ladder planning failed: command_id=%s reason=%s', cmd.command_id, exc)
            await self._emit_scheme_terminal(
                runtime, cmd,
                status=TradeStatus.REJECTED,
                filled_qty=_ZERO, cumulative_notional=_ZERO,
                slices_completed=0, slices_total=len(params.price_levels),
                reason=f'ladder planning failed: {exc}',
            )
            return

        init = SchemeInitialized(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            execution_mode=cmd.execution_mode,
            symbol=cmd.symbol,
            side=cmd.side,
            total_qty=cmd.qty,
            slices_total=len(levels),
            interval_seconds=0,
            timeout_seconds=cmd.timeout,
            volume_weights=params.level_weights or (),
            price_levels=params.price_levels,
        )
        await self._event_spine.append(init, self._epoch_id)
        runtime.trading_state.apply(init)

        scheme = _LiveScheme(
            command=cmd,
            slice_qtys=[qty for qty, _price in levels],
            slices_total=len(levels),
            interval_seconds=0,
            deadline=(
                init.timestamp + timedelta(seconds=cmd.timeout)
                if cmd.timeout > 0
                else None
            ),
        )
        runtime.schemes[cmd.command_id] = scheme

        for index, (qty, price) in enumerate(levels):
            client_order_id = await self._submit_limit_level(runtime, cmd, index, qty, price)

            if client_order_id is None:
                await self._on_slice_failure(
                    runtime,
                    scheme,
                    generate_client_order_id(cmd.execution_mode, cmd.command_id, sequence=index),
                    f'ladder rung {index} submission failed',
                )
                return

            order = self._scheme_child_order(runtime, client_order_id)
            if order is not None and order.status not in _TERMINAL_ORDER_STATUSES:
                scheme.active_children.add(client_order_id)

            scheme.cursor = index + 1
            await self._append_scheme_progress(runtime, scheme, SchemeState.RUNNING)

        _log.info(
            'ladder started: command_id=%s rungs=%d active=%d',
            cmd.command_id,
            scheme.slices_total,
            len(scheme.active_children),
        )

        await self._maybe_finalize_scheme(runtime, scheme)

    async def _submit_limit_level(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        index: int,
        level_qty: Decimal,
        level_price: Decimal,
        generation: int = 0,
    ) -> str | None:
        '''Persist-before-send one resting LIMIT child for a ladder rung.

        The LIMIT sibling of `_submit_market_slice`: `OrderSubmitIntent`
        before the venue call, `OrderSubmitted` plus one `FillReceived` per
        immediate fill on success, `OrderSubmitFailed` on a definitive
        failure. Returns the rung `client_order_id` on success (usually
        resting OPEN; its later fills aggregate through the order
        projection), or None when the rung could not be placed. `generation`
        qualifies the client order id (retry=generation) so an amended rung
        never collides with a cancelled rung of the same index.
        '''

        client_order_id = generate_client_order_id(
            cmd.execution_mode, cmd.command_id, sequence=index, retry=generation,
        )
        now = self._clock()

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=now,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            client_order_id=client_order_id,
            symbol=cmd.symbol,
            side=cmd.side,
            order_type=OrderType.LIMIT,
            qty=level_qty,
            quote_qty=None,
            price=level_price,
            stop_price=None,
            stop_limit_price=None,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                cmd.side,
                OrderType.LIMIT,
                level_qty,
                price=level_price,
                client_order_id=client_order_id,
            )
            post_venue_ts = self._clock()
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError) as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, cmd, client_order_id, exc,
            )
            if rescued is None:
                await self._append_submit_failed(
                    runtime, cmd, client_order_id, str(exc.args[0]),
                )
                return None
            result = rescued
            post_venue_ts = self._clock()
        except VenueError as exc:
            await self._append_submit_failed(
                runtime, cmd, client_order_id, str(exc.args[0]),
            )
            return None
        except ValueError as exc:
            await self._append_submit_failed(
                runtime, cmd, client_order_id, f'adapter rejected params: {exc}',
            )
            return None

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=post_venue_ts,
            client_order_id=client_order_id,
            venue_order_id=result.venue_order_id,
        )
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        for fill in result.immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=post_venue_ts,
                client_order_id=client_order_id,
                venue_order_id=result.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=cmd.command_id,
                symbol=cmd.symbol,
                side=cmd.side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        _log.info(
            'ladder rung submitted: command_id=%s rung=%d client_order_id=%s price=%s fills=%d',
            cmd.command_id,
            index,
            client_order_id,
            level_price,
            len(result.immediate_fills),
        )

        return client_order_id

    def _scheme_child_order(
        self,
        runtime: _AccountRuntime,
        client_order_id: str,
    ) -> Order | None:
        '''Return a scheme child's order projection, active or closed.'''

        return (
            runtime.trading_state.orders.get(client_order_id)
            or runtime.trading_state.closed_orders.get(client_order_id)
        )

    async def _append_scheme_progress(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        state: SchemeState,
    ) -> None:
        '''Append a `SchemeStateChanged` from the current live scheme state.

        Cumulative fill is derived from the child order projections so the
        durable transition reflects every settled child, immediate or
        WebSocket, without an in-memory running total a crash could lose.
        '''

        cmd = scheme.command
        filled_qty, _ = self._command_fill_totals(runtime, cmd.command_id)

        changed = SchemeStateChanged(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            cursor=scheme.cursor,
            filled_qty=filled_qty,
            active_client_order_ids=tuple(sorted(scheme.active_children)),
            next_run_at=scheme.next_run_at,
            state=state,
        )
        await self._event_spine.append(changed, self._epoch_id)
        runtime.trading_state.apply(changed)

    async def _maybe_finalize_scheme(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
    ) -> None:
        '''Finalize the scheme once no child is still working.

        Called after every slice advance and every child-settle event. A
        pending terminal (abort or deadline) resolves first; a frozen scheme
        (a slice failed, awaiting the Manager) holds without completing;
        otherwise the scheme completes FILLED once every slice has been
        submitted and every child has fully filled. Does nothing while any
        child remains active.

        Completion status is FILLED, not PARTIAL: reaching this branch means
        every child settled FILLED (a non-fill terminal child routes to a
        pending FAILED via `_on_scheme_child_event`), so the only shortfall
        possible is sub-lot dust from `plan_even_slices` flooring each slice
        to the lot step — economically negligible and un-tradeable, the same
        dust a single-shot MARKET order leaves. PARTIAL is not a terminal
        `TradeStatus`, so it cannot be the outcome of a completed command.

        A ladder mid-amend (`amend_phase` set) never finalizes here: the amend
        driver empties `active_children` while retiring the old grid, so
        finalizing on that transient emptiness would complete the ladder before
        the new grid is placed. The driver finalizes once the amend resolves.
        '''

        if scheme.amend_phase is not None:
            return

        if scheme.active_children:
            return

        if scheme.pending_terminal is not None:
            status, scheme_state, reason = scheme.pending_terminal
            await self._finalize_scheme(
                runtime,
                scheme,
                status=status,
                scheme_state=scheme_state,
                reason=reason,
            )
            return

        if scheme.frozen:
            return

        if scheme.cursor >= scheme.slices_total:
            await self._finalize_scheme(
                runtime,
                scheme,
                status=TradeStatus.FILLED,
                scheme_state=SchemeState.COMPLETED,
                reason=None,
            )

    async def _on_scheme_child_event(
        self,
        runtime: _AccountRuntime,
        event: Event,
    ) -> None:
        '''Fold a scheme child's WebSocket fill/terminal event into its parent.

        Fills already updated the child order projection via `_project`;
        this settles the child (drops it from the scheme's active set once
        its order is terminal) and finalizes the scheme when the last child
        settles. A child that reaches a terminal status without fully
        filling — rejected, expired, or cancelled outside the parent abort
        flow — is a slice failure: the scheme freezes (see
        `_on_slice_failure`), reports a PARTIAL outcome, and waits for the
        Manager or its deadline (never a FILLED short of target). Events for
        non-scheme commands or already-finalized schemes are ignored.
        '''

        if not isinstance(event, (FillReceived, OrderCanceled, OrderExpired, OrderRejected)):
            return

        order = self._scheme_child_order(runtime, event.client_order_id)
        if order is None:
            return

        scheme = runtime.schemes.get(order.command_id)
        if scheme is None:
            return

        if order.status in _TERMINAL_ORDER_STATUSES:
            scheme.active_children.discard(event.client_order_id)

            if scheme.amend_phase is not None:
                return

            if (
                order.status is not OrderStatus.FILLED
                and scheme.pending_terminal is None
                and not scheme.frozen
            ):
                await self._on_slice_failure(
                    runtime,
                    scheme,
                    event.client_order_id,
                    f'child {event.client_order_id} terminated '
                    f'{order.status.value} without full fill',
                )
                return

        await self._maybe_finalize_scheme(runtime, scheme)

    async def _cancel_active_children(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
    ) -> None:
        '''Best-effort cancel every still-working child of a scheme.

        A confirmed cancel appends `OrderCanceled` so the child projection
        reaches a terminal status and drains from the active set. A market
        child already filling cannot be cancelled: `NotFoundError` and other
        venue errors are swallowed, and the child settles through its own
        fill or expiry event instead.
        '''

        cmd = scheme.command

        for client_order_id in tuple(scheme.active_children):
            order = self._scheme_child_order(runtime, client_order_id)
            if order is None:
                scheme.active_children.discard(client_order_id)
                continue

            try:
                await self._venue_adapter.cancel_order(
                    cmd.account_id,
                    cmd.symbol,
                    client_order_id=client_order_id,
                )
            except NotFoundError:
                continue
            except VenueError as exc:
                _log.warning(
                    'scheme child cancel failed: command_id=%s child=%s reason=%s',
                    cmd.command_id,
                    client_order_id,
                    exc.args[0] if exc.args else str(exc),
                )
                continue

            canceled = OrderCanceled(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=client_order_id,
                venue_order_id=order.venue_order_id,
                reason='scheme aborted',
            )
            await self._event_spine.append(canceled, self._epoch_id)
            runtime.trading_state.apply(canceled)
            scheme.active_children.discard(client_order_id)

    async def _finalize_scheme(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        *,
        status: TradeStatus,
        scheme_state: SchemeState,
        reason: str | None,
    ) -> None:
        '''Emit the terminal scheme transition and the single trade outcome.

        Appends a terminal `SchemeStateChanged`, then the aggregated
        terminal `TradeOutcome` (fills derived from the child order
        projections). Removes the scheme from the live scheduler set so no
        further slices fire.
        '''

        cmd = scheme.command
        scheme.state = scheme_state
        scheme.next_run_at = None
        scheme.active_children.clear()
        runtime.schemes.pop(cmd.command_id, None)

        await self._append_scheme_progress(runtime, scheme, scheme_state)

        filled_qty, cumulative_notional = self._command_fill_totals(runtime, cmd.command_id)

        await self._emit_scheme_terminal(
            runtime,
            cmd,
            status=status,
            filled_qty=filled_qty,
            cumulative_notional=cumulative_notional,
            slices_completed=scheme.cursor,
            slices_total=scheme.slices_total,
            reason=reason,
        )

    async def _abort_scheme(
        self,
        runtime: _AccountRuntime,
        abort: TradeAbort,
    ) -> None:
        '''Abort a running scheme: stop scheduling, cancel children, finalize.

        Marks the scheme for a terminal CANCELED outcome and cancels any
        still-working child at the venue. The single aggregated CANCELED
        outcome fires once every child has settled — immediately when none
        are working, otherwise as the cancels confirm.
        '''

        scheme = runtime.schemes.get(abort.command_id)
        if scheme is None:
            return

        _log.info(
            'aborting running scheme: command_id=%s account_id=%s reason=%s',
            abort.command_id,
            runtime.account_id,
            abort.reason,
        )

        scheme.pending_terminal = (
            TradeStatus.CANCELED,
            SchemeState.CANCELED,
            abort.reason,
        )
        scheme.next_run_at = None
        await self._cancel_active_children(runtime, scheme)
        await self._maybe_finalize_scheme(runtime, scheme)

    async def _freeze_account_schemes(
        self,
        runtime: _AccountRuntime,
        reason: str,
    ) -> list[str]:
        '''Durably freeze every live scheme on the account against new slices.

        Appends a `SchemeFrozen` for each running, non-terminal scheme and
        freezes it in memory so `_advance_due_schemes` fires no further
        slice. The durable event lands the scheme in the replay freeze set,
        so a restart resumes it frozen instead of re-arming its timer — the
        naked-protection interlock that stops schemes buying while a bracket
        is unprotected, across restarts. A scheme frozen only by a slice
        failure (amend-resumable) is upgraded to protection-frozen so an
        amend cannot resume it during the remediation. Idempotent: an
        already-protection-frozen or terminalizing scheme is skipped.

        Args:
            runtime (_AccountRuntime): Account whose schemes to freeze.
            reason (str): Freeze reason recorded on each event.

        Returns:
            list[str]: Command ids newly frozen by this call.
        '''

        frozen: list[str] = []

        for command_id, scheme in runtime.schemes.items():
            if scheme.protection_frozen or scheme.pending_terminal is not None:
                continue

            event = SchemeFrozen(
                account_id=runtime.account_id,
                timestamp=self._clock(),
                command_id=command_id,
                reason=reason,
            )
            await self._event_spine.append(event, self._epoch_id)

            scheme.frozen = True
            scheme.protection_frozen = True
            scheme.next_run_at = None
            frozen.append(command_id)

        return frozen

    def _protection_response_for(
        self, account_id: str,
    ) -> BracketProtectionFailureResponse:
        '''Resolve the account's bracket-protection failure response.

        Defaults to the fail-safe FLATTEN_THEN_HALT when no per-account
        resolver was wired, so an unconfigured deployment flattens rather
        than leaving a naked position.
        '''

        if self._protection_failure_response is None:
            return BracketProtectionFailureResponse.FLATTEN_THEN_HALT

        return self._protection_failure_response(account_id)

    async def _free_asset_balance(self, account_id: str, asset: str) -> Decimal:
        '''Return the venue free balance of an asset, or zero if absent.'''

        entries = await self._venue_adapter.query_balance(
            account_id, frozenset({asset}),
        )
        for entry in entries:
            if entry.asset == asset:
                return entry.free

        return _ZERO

    async def _conservative_flatten_buy_price(
        self, cmd: TradeCommand, fallback: Decimal,
    ) -> Decimal:
        '''Return a fresh conservative price to cap a BUY flatten by free quote.

        A BUY flatten (closing a short) pays the current ask, not the historical
        entry price — when the market has risen against the stop, the usual
        failure direction, sizing the quote cap on the entry price buys more
        than the free balance covers and the venue rejects the remediation. The
        current best ask plus a fee/slippage buffer bounds the market cost; a
        book query that fails falls back to the entry price.
        '''

        try:
            book = await self._venue_adapter.query_order_book(cmd.symbol)
        except VenueError:
            return fallback

        if not book.asks:
            return fallback

        return book.asks[0].price * _FLATTEN_BUY_PRICE_BUFFER

    async def _current_flatten_sell_price(
        self, cmd: TradeCommand, fallback: Decimal,
    ) -> Decimal:
        '''Return a fresh market price for a SELL flatten's tradability check.

        Binance applies MARKET-order notional rules at current market pricing,
        so a SELL flatten (closing a long) is checked against the current best
        bid, not the historical entry price — after a large adverse move the
        entry-price notional can read below the venue minimum while the current
        notional clears it, which would otherwise reject a viable remediation
        and leave the position naked. A book query that fails, or an empty bid
        side, falls back to the entry price.
        '''

        try:
            book = await self._venue_adapter.query_order_book(cmd.symbol)
        except VenueError:
            return fallback

        if not book.bids:
            return fallback

        return book.bids[0].price

    def _record_protection_remediation(
        self,
        account_id: str,
        command_id: str,
        protection_version: int,
        reason: str,
    ) -> None:
        '''Record a protection remediation for durable delivery to Nexus.

        Kept in memory keyed by command id and delivered (idempotently) by
        `drain_protection_remediations` on the reconcile cycle: the Nexus hold
        is sticky, so re-delivery after a restart is a no-op. Applies to both
        policies — Nexus's handler decides HALT vs REDUCE_ONLY.
        '''

        self._pending_remediations[command_id] = ProtectionRemediation(
            account_id=account_id,
            timestamp=self._clock().astimezone(UTC),
            protection_remediation_id=f'protection-{command_id}-{protection_version}',
            command_id=command_id,
            protection_version=protection_version,
            reason=reason,
        )

    def seed_protection_remediations(
        self,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Re-seed pending remediations from replayed `ProtectionFailed` events.

        A failed bracket's Nexus hold must be delivered after a restart, and a
        failed bracket is not resumed into `runtime.brackets`, so the pending
        set is rebuilt from the durable failure markers — except commands
        already recorded delivered by a `ProtectionRemediationDelivered`. The
        Nexus hold is sticky and operator-cleared, so re-delivering an
        already-delivered remediation would re-apply a hold an operator may
        have since lifted; the delivered marker prevents that.
        '''

        delivered: set[str] = {
            event.command_id
            for _seq, event in events
            if isinstance(event, ProtectionRemediationDelivered)
        }

        for _seq, event in events:
            if isinstance(event, ProtectionFailed) and event.command_id not in delivered:
                self._record_protection_remediation(
                    event.account_id,
                    event.command_id,
                    event.protection_version,
                    event.reason,
                )

    async def drain_protection_remediations(self, account_id: str) -> None:
        '''Deliver pending protection remediations for an account to Nexus.

        Mirrors the reconciliation-mismatch delivery: each pending remediation
        is delivered through the injected callback, dropped from the pending
        set on success, and left to retry on the next cycle on any failure
        (including the Nexus runtime not being ready yet).
        '''

        if self._on_protection_remediation is None:
            return

        pending = [
            (command_id, remediation)
            for command_id, remediation in self._pending_remediations.items()
            if remediation.account_id == account_id
        ]
        for command_id, remediation in pending:
            try:
                await self._on_protection_remediation(remediation)
            except Exception:  # noqa: BLE001 - leave pending to retry next cycle
                _log.exception(
                    'failed to deliver protection remediation to Nexus; will '
                    'retry next cycle: command_id=%s',
                    command_id,
                )

                continue

            delivered = ProtectionRemediationDelivered(
                account_id=remediation.account_id,
                timestamp=self._clock(),
                command_id=command_id,
                protection_remediation_id=remediation.protection_remediation_id,
            )
            await self._event_spine.append(delivered, self._epoch_id)
            self._pending_remediations.pop(command_id, None)

    async def _remediate_naked_bracket(
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        version: int,
        reason: str,
        remainder: Decimal,
        oco_candidates: tuple[str, ...],
    ) -> None:
        '''Apply the naked-protection remediation: freeze, record, flatten, hold.

        Freezes the account's schemes against adding exposure, records the
        durable `ProtectionFailed` marker, flattens the remainder when the
        account policy is FLATTEN_THEN_HALT, and delivers the Nexus hold
        immediately (retried on the reconcile cycle). Shared by the definitive
        amend-failure path and the STATE_UNKNOWN watchdog once a bracket is
        confirmed naked.

        Args:
            runtime (_AccountRuntime): Account whose bracket is naked.
            bracket (_LiveBracket): The unprotected bracket.
            version (int): Protective-OCO revision that failed.
            reason (str): Human-readable trigger.
            remainder (Decimal): Venue-reconciled remaining position.
            oco_candidates (tuple[str, ...]): Every OCO list id the flatten must
                confirm terminal before selling — the cancelled OCO and any
                ambiguous replacement — persisted on the marker so boot recovery
                guards them too.
        '''

        cmd = bracket.command
        await self._freeze_account_schemes(
            runtime,
            f'bracket protection failed: command_id={cmd.command_id} '
            f'version={version}',
        )
        await self._append_protection_failed(
            cmd, version, reason, oco_candidates,
        )
        bracket.protection_status = BracketProtectionStatus.FAILED
        self._record_protection_remediation(
            cmd.account_id, cmd.command_id, version, reason,
        )
        _log.warning(
            'bracket protection failed; account schemes frozen: command_id=%s '
            'version=%d reason=%s',
            cmd.command_id,
            version,
            reason,
        )

        if (
            self._protection_response_for(cmd.account_id)
            is BracketProtectionFailureResponse.FLATTEN_THEN_HALT
        ):
            await self._flatten_bracket_remainder(
                runtime, bracket, version, reason,
                remainder, oco_candidates,
            )

        await self.drain_protection_remediations(cmd.account_id)

    async def _remediate_failed_initial_protection(
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        exit_cmd: TradeCommand,
        client_order_id: str,
        qty: Decimal,
        reason: str,
        oco_candidates: tuple[str, ...],
    ) -> None:
        '''Remediate a bracket whose initial protective OCO failed (TD-130).

        The whole filled entry is naked, so the bracket is tracked FAILED and
        routed through the shared naked-protection remediation (freeze, flatten,
        hold) instead of being left unprotected with only a log. The durable
        `ProtectionFailed` is appended (inside the remediation) before the
        exit's `OrderSubmitFailed`, so a crash between the two still leaves the
        crash-durable marker that boot flatten recovery keys on. The failure is
        recorded against the first protective revision, since the original
        placement (version 0) never rested a protective OCO.

        `oco_candidates` is the protective OCO's list id when the OCO may have
        reached the venue (an unsalvageable timeout or a venue error), so the
        flatten re-checks the venue for a live leg before selling; it is empty
        only when the OCO was never POSTed (wrong-side legs), where a second
        sell is impossible and the guard is safely skipped.
        '''

        version = max(bracket.protection_version, _BRACKET_FIRST_PROTECTION_VERSION)
        runtime.brackets[bracket.command.command_id] = bracket
        await self._remediate_naked_bracket(
            runtime, bracket, version, reason, qty, oco_candidates,
        )
        await self._append_submit_failed(
            runtime, exit_cmd, client_order_id, reason,
        )

    async def _working_protective_oco(
        self, cmd: TradeCommand, list_client_order_id: str,
    ) -> VenueOrderList | None:
        '''Return a protective OCO list only while it is still working.

        A list the venue reports REJECT or ALL_DONE (cancelled or a leg filled),
        or that the venue no longer knows (NotFound), is no longer protecting
        and returns None; a working list is returned so its legs can be
        re-tracked. Raises `VenueError` when the query cannot be completed, so
        the caller stays STATE_UNKNOWN rather than act on an unconfirmed state.
        '''

        try:
            order_list = await self._venue_adapter.query_order_list(
                cmd.account_id, list_client_order_id=list_client_order_id,
            )
        except NotFoundError:
            return None

        if order_list.list_order_status in (
            _OCO_LIST_STATUS_REJECT, _OCO_LIST_STATUS_ALL_DONE,
        ):
            return None

        return order_list

    async def _reactivate_protection(
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        client_order_id: str,
        order_list: VenueOrderList,
    ) -> None:
        '''Re-track a protective OCO the watchdog confirmed still working.

        Re-tracking only succeeds when the trading state already carries the
        order (its OrderSubmitIntent was persisted when the OCO was submitted
        and replays on boot). A submitted event for an unknown order would
        no-op in the trading state and strand leg-fill routing, so an absent
        order leaves the bracket STATE_UNKNOWN for the next cycle instead.
        '''

        cmd = bracket.command
        exit_command_id = bracket_exit_command_id(cmd.command_id)

        if runtime.trading_state.orders.get(client_order_id) is None:
            _log.warning(
                'bracket protection re-track skipped: order absent from trading '
                'state; command_id=%s client_order_id=%s',
                cmd.command_id,
                client_order_id,
            )
            return

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            client_order_id=client_order_id,
            venue_order_id=order_list.order_list_id,
            leg_client_order_ids=tuple(
                leg.client_order_id for leg in order_list.legs
            ),
        )
        runtime.command_to_order[exit_command_id] = client_order_id
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        active = ProtectionActive(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=bracket.protection_version,
            new_list_client_order_id=client_order_id,
        )
        await self._event_spine.append(active, self._epoch_id)
        bracket.protection_client_order_id = client_order_id
        bracket.protection_status = BracketProtectionStatus.ACTIVE
        bracket.unknown_since = None
        bracket.pending_replacement_client_order_id = None
        _log.info(
            'bracket protection re-confirmed working by watchdog: command_id=%s '
            'client_order_id=%s',
            cmd.command_id,
            client_order_id,
        )

    async def _run_protection_scan(self, runtime: _AccountRuntime) -> None:
        '''Run the reconcile-tick watchdogs and drains on the account writer.

        Requested by the off-critical-path reconcile task via
        `request_protection_scan` and executed here so the watchdogs' writes —
        protection re-track, scheme freeze, flatten submit, and ladder-amend
        cancel/place — run on the single account writer rather than racing it
        from the reconcile task. A failure is logged and swallowed so a venue
        error cannot stop the account loop.
        '''

        try:
            await self.resolve_unknown_protection(runtime.account_id)
            await self.drain_protection_remediations(runtime.account_id)
            await self.resolve_ladder_amends(runtime.account_id)
            await self.resolve_pending_amends(runtime.account_id)
            await self.resolve_held_protection_amends(runtime.account_id)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            _log.exception(
                'protection scan failed: account_id=%s', runtime.account_id,
            )

    async def resolve_ladder_amends(self, account_id: str) -> None:
        '''Advance any stalled or crash-resumed ladder amend on the writer.

        A live amend that could not confirm a cancel or a placement, or one
        rebuilt mid-flight on boot, holds with `amend_phase` set and its
        context retained. Each reconcile tick re-drives it — retrying the
        fail-closed cancels or the missing placements idempotently — until it
        completes or halts again on a still-unconfirmable venue.

        Args:
            account_id (str): Account whose ladder amends to advance.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        for scheme in list(runtime.schemes.values()):
            if scheme.amend_phase is None or scheme.amend_context is None:
                continue

            await self._drive_ladder_amend(runtime, scheme)

    async def resolve_unknown_protection(self, account_id: str) -> None:
        '''Resolve brackets stuck in STATE_UNKNOWN on the account writer.

        A protective-OCO amend that could not confirm its venue outcome leaves
        the bracket STATE_UNKNOWN. Each cycle the venue is re-queried:

        - a still-working OCO (the ambiguity resolved in favour of protection)
          is re-tracked ACTIVE;
        - every candidate the venue confirms terminal is resolved by remaining
          quantity now: a filled protective leg (remainder <= 0) closed the
          position, so the bracket is simply dropped; a genuine naked remainder
          (> 0) is remediated at once (freeze, flatten, hold);
        - a query that cannot be completed leaves the bracket STATE_UNKNOWN and,
          only once the restore deadline elapses without ever confirming the
          venue state, is remediated fail-safe on the local projection.

        Confirmed outcomes act immediately; the deadline gates only the
        unconfirmable case, so a routine take-profit fill never freezes schemes
        or halts the account.

        Args:
            account_id (str): Account whose brackets to resolve.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        for _command_id, bracket in list(runtime.brackets.items()):
            if bracket.protection_status is not BracketProtectionStatus.STATE_UNKNOWN:
                continue

            cmd = bracket.command
            candidates = [
                candidate
                for candidate in (
                    bracket.pending_replacement_client_order_id,
                    bracket.protection_client_order_id,
                )
                if candidate is not None
            ]

            working: tuple[str, VenueOrderList] | None = None
            query_failed = False
            for candidate in candidates:
                try:
                    order_list = await self._working_protective_oco(cmd, candidate)
                except VenueError:
                    query_failed = True
                    continue

                if order_list is not None:
                    working = (candidate, order_list)
                    break

            if working is not None:
                await self._reactivate_protection(
                    runtime, bracket, working[0], working[1],
                )
                continue

            if query_failed:
                await self._remediate_unconfirmable_bracket(runtime, bracket)
                continue

            await self._resolve_confirmed_terminal_bracket(runtime, bracket)

    async def _resolve_confirmed_terminal_bracket(
        self, runtime: _AccountRuntime, bracket: _LiveBracket,
    ) -> None:
        '''Resolve a STATE_UNKNOWN bracket whose OCO the venue confirms terminal.

        The venue confirmed no candidate list is working, so the outcome turns
        on venue-truth remaining quantity: a protective leg that filled closes
        the position (remainder <= 0) and the bracket is dropped without a
        halt; a positive remainder is genuinely naked and is remediated now.
        '''

        cmd = bracket.command
        exit_command_id = bracket_exit_command_id(cmd.command_id)
        entry_filled, _ = self._command_fill_totals(runtime, cmd.command_id)
        exit_projected, _ = self._command_fill_totals(runtime, exit_command_id)
        protective_side = (
            OrderSide.SELL if cmd.side is OrderSide.BUY else OrderSide.BUY
        )

        candidates = [
            candidate
            for candidate in (
                bracket.protection_client_order_id,
                bracket.pending_replacement_client_order_id,
            )
            if candidate is not None
        ]
        exit_venue = _ZERO
        candidate_projected = _ZERO
        for candidate in candidates:
            try:
                order_list = await self._venue_adapter.query_order_list(
                    cmd.account_id, list_client_order_id=candidate,
                )
                candidate_venue = _ZERO
                for leg in order_list.legs:
                    leg_order = await self._venue_adapter.query_order(
                        cmd.account_id, cmd.symbol, client_order_id=leg.client_order_id,
                    )
                    candidate_venue += leg_order.filled_qty
            except NotFoundError:
                continue
            except VenueError:
                return

            leg_client_order_ids = tuple(
                leg.client_order_id for leg in order_list.legs
            )
            candidate_order = self._scheme_child_order(runtime, candidate)
            candidate_local = (
                candidate_order.filled_qty if candidate_order is not None else _ZERO
            )
            reconciled = await self._backfill_terminal_order_fills(
                runtime, cmd.account_id, cmd.symbol, exit_command_id, cmd.trade_id,
                protective_side, candidate, leg_client_order_ids,
                candidate_local, candidate_venue,
            )
            if not reconciled:
                return

            exit_venue += candidate_venue
            candidate_projected += candidate_local

        remainder = entry_filled - (exit_projected - candidate_projected + exit_venue)
        if remainder <= _ZERO:
            exit_cmd = self._commands.get(exit_command_id)
            exit_filled, exit_notional = self._command_fill_totals(
                runtime, exit_command_id,
            )
            if exit_cmd is not None and exit_filled > _ZERO:
                await self._build_outcome(
                    runtime,
                    exit_cmd,
                    TradeStatus.FILLED,
                    filled_qty=exit_filled,
                    avg_fill_price=exit_notional / exit_filled,
                    reason=None,
                    cumulative_notional=exit_notional,
                )

            runtime.brackets.pop(cmd.command_id, None)
            _log.info(
                'bracket protection resolved: position closed by a protective '
                'fill; command_id=%s',
                cmd.command_id,
            )
            return

        await self._remediate_naked_bracket(
            runtime,
            bracket,
            bracket.protection_version,
            'protection confirmed terminal and position naked',
            remainder,
            self._bracket_oco_candidates(bracket),
        )

    async def _remediate_unconfirmable_bracket(
        self, runtime: _AccountRuntime, bracket: _LiveBracket,
    ) -> None:
        '''Fail-safe remediate a bracket whose venue state stays unconfirmable.

        A candidate query kept failing, so the venue truth is unknown. The
        bracket holds STATE_UNKNOWN until the restore deadline elapses; only
        then, still unable to confirm, is it remediated on the local fill
        projection (the flatten free-caps the sized quantity).
        '''

        if bracket.unknown_since is None:
            return

        elapsed = (self._clock() - bracket.unknown_since).total_seconds()
        if elapsed < self._restore_deadline_seconds:
            return

        cmd = bracket.command
        exit_command_id = bracket_exit_command_id(cmd.command_id)
        entry_filled, _ = self._command_fill_totals(runtime, cmd.command_id)
        exit_projected, _ = self._command_fill_totals(runtime, exit_command_id)
        remainder = entry_filled - exit_projected
        if remainder <= _ZERO:
            return

        await self._remediate_naked_bracket(
            runtime,
            bracket,
            bracket.protection_version,
            'protection unconfirmable past restore deadline',
            remainder,
            self._bracket_oco_candidates(bracket),
        )

    async def _oco_has_live_leg(
        self, cmd: TradeCommand, list_client_order_id: str,
    ) -> bool:
        '''Whether any leg of a protective OCO is still live or partly filled.

        A second MARKET against a stop-limit that is still executing is a short
        on spot (no reduceOnly), so the flatten must not run while any leg of
        the cancelled OCO is non-terminal. A query failure is treated as live
        (fail-closed): the caller stays STATE_UNKNOWN rather than flatten blind.
        '''

        try:
            order_list = await self._venue_adapter.query_order_list(
                cmd.account_id, list_client_order_id=list_client_order_id,
            )
            for leg in order_list.legs:
                leg_order = await self._venue_adapter.query_order(
                    cmd.account_id, cmd.symbol, client_order_id=leg.client_order_id,
                )
                if leg_order.status not in _TERMINAL_ORDER_STATUSES:
                    return True
        except NotFoundError:
            return False
        except VenueError:
            _log.exception(
                'flatten live-leg guard query failed; treating as live: '
                'command_id=%s',
                cmd.command_id,
            )
            return True

        return False

    async def _flatten_bracket_remainder(
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        protection_version: int,
        reason: str,
        remainder: Decimal,
        oco_candidates: tuple[str, ...] = (),
    ) -> None:
        '''Market-close the reconciled remainder of an unprotected bracket.

        The naked position left when a protective-OCO amend fails is closed
        with a MARKET order on the protective side, sized as the caller's
        venue-reconciled remainder capped by the fresh free balance of the cap
        asset (base for a SELL flatten, quote for a BUY) and lot-snapped down —
        never the raw balance, which would dump unrelated account inventory. A
        remainder below the lot or notional minimum, or no free cap asset, is
        left for a halt-and-alert rather than a dust order or an oversell.
        Before submitting, any still-live protective leg aborts the flatten
        (STATE_UNKNOWN): a second MARKET against an executing stop is a short.
        The `FlattenInitiated` intent is persisted before the venue submit, so
        a crash replays it and the deterministic client id is queried before
        any resubmission. The flatten submits under the bracket exit command
        id, so its fill produces the position-closing EXIT outcome. Runs on the
        account loop (single writer); the free balance is read immediately
        before submit and never cached across flattens.

        Args:
            runtime (_AccountRuntime): Account whose bracket to flatten.
            bracket (_LiveBracket): The unprotected bracket.
            protection_version (int): Protective-OCO revision that failed.
            reason (str): Human-readable trigger for the flatten.
            remainder (Decimal): Venue-reconciled remaining position to close
                (entry filled minus the cancelled OCO's venue-truth fills).
            oco_candidates (tuple[str, ...]): Every protective OCO list id that
                could still be live — the cancelled OCO and any ambiguously
                submitted replacement — each re-checked for a live leg
                immediately before flattening; the flatten aborts if any is live
                or unconfirmable, so a market close can never race a still-live
                protective OCO. Empty skips the guard.
        '''

        cmd = bracket.command
        exit_command_id = bracket_exit_command_id(cmd.command_id)
        protective_side = (
            OrderSide.SELL if cmd.side is OrderSide.BUY else OrderSide.BUY
        )

        filters = self._venue_adapter.cached_filters(cmd.symbol)
        cap_asset = (
            filters.base_asset if protective_side is OrderSide.SELL
            else filters.quote_asset
        ) if filters is not None else ''
        if filters is None or not cap_asset:
            _log.error(
                'cannot flatten bracket without symbol filters and the cap asset; '
                'position left unprotected for halt: command_id=%s reason=%s',
                cmd.command_id,
                reason,
            )
            return

        for candidate in oco_candidates:
            if await self._oco_has_live_leg(cmd, candidate):
                _log.warning(
                    'flatten aborted; a protective leg is still live, partially '
                    'filled, or unconfirmable, staying STATE_UNKNOWN: '
                    'command_id=%s candidate=%s',
                    cmd.command_id,
                    candidate,
                )
                return

        entry_filled, entry_notional = self._command_fill_totals(runtime, cmd.command_id)

        if remainder <= _ZERO or entry_filled <= _ZERO:
            _log.info(
                'flatten no-op; bracket remainder already closed: command_id=%s',
                cmd.command_id,
            )
            return

        avg_entry_price = entry_notional / entry_filled
        free = await self._free_asset_balance(cmd.account_id, cap_asset)

        if protective_side is OrderSide.SELL:
            cap = free
            market_price = await self._current_flatten_sell_price(cmd, avg_entry_price)
        else:
            buy_price = await self._conservative_flatten_buy_price(cmd, avg_entry_price)
            cap = free / buy_price if buy_price > _ZERO else _ZERO
            market_price = buy_price

        qty = (min(remainder, cap) // filters.lot_step) * filters.lot_step

        if qty < remainder:
            _log.warning(
                'flatten capped below remainder by free %s balance; shortfall: '
                'command_id=%s remainder=%s free=%s qty=%s',
                cap_asset,
                cmd.command_id,
                remainder,
                free,
                qty,
            )

        notional = qty * market_price
        if qty < filters.lot_min or notional < filters.min_notional:
            _log.error(
                'flatten remainder below lot or notional minimum; position left '
                'unprotected for halt: command_id=%s qty=%s notional=%s',
                cmd.command_id,
                qty,
                notional,
            )
            return

        client_order_id = generate_client_order_id(
            ExecutionMode.BRACKET, cmd.command_id, sequence=_BRACKET_FLATTEN_SEQUENCE,
        )

        flatten = FlattenInitiated(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=protection_version,
            qty=qty,
            client_order_id=client_order_id,
        )
        await self._event_spine.append(flatten, self._epoch_id)

        await self._submit_flatten_order(
            runtime, cmd, exit_command_id, protective_side, qty, client_order_id,
        )

    def _flatten_exit_command(
        self,
        cmd: TradeCommand,
        exit_command_id: str,
        protective_side: OrderSide,
        qty: Decimal,
    ) -> TradeCommand:
        '''Build the MARKET exit command the flatten order settles under.'''

        return TradeCommand(
            command_id=exit_command_id,
            trade_id=cmd.trade_id,
            account_id=cmd.account_id,
            symbol=cmd.symbol,
            side=protective_side,
            qty=qty,
            order_type=OrderType.MARKET,
            execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(),
            timeout=cmd.timeout,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE,
            created_at=self._clock(),
        )

    async def _submit_flatten_order(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        exit_command_id: str,
        protective_side: OrderSide,
        qty: Decimal,
        client_order_id: str,
    ) -> None:
        '''Submit and project the MARKET flatten order under the exit id.'''

        exit_cmd = self._flatten_exit_command(
            cmd, exit_command_id, protective_side, qty,
        )

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=exit_command_id,
            trade_id=cmd.trade_id,
            client_order_id=client_order_id,
            symbol=cmd.symbol,
            side=protective_side,
            order_type=OrderType.MARKET,
            qty=qty,
            quote_qty=None,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                protective_side,
                OrderType.MARKET,
                qty,
                client_order_id=client_order_id,
            )
        except VenueError as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, exit_cmd, client_order_id, exc,
            )
            if rescued is None:
                _log.exception(
                    'flatten submit unconfirmable; position may be naked: '
                    'command_id=%s client_order_id=%s',
                    cmd.command_id,
                    client_order_id,
                )
                await self._append_submit_failed(
                    runtime,
                    exit_cmd,
                    client_order_id,
                    str(exc.args[0]) if exc.args else str(exc),
                )

                return

            result = rescued

        self._commands[exit_command_id] = exit_cmd
        self._command_trade_ids[exit_command_id] = cmd.trade_id
        runtime.command_to_order[exit_command_id] = client_order_id

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            client_order_id=client_order_id,
            venue_order_id=result.venue_order_id,
            leg_client_order_ids=result.leg_client_order_ids,
        )
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        for fill in result.immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=client_order_id,
                venue_order_id=result.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=exit_command_id,
                symbol=cmd.symbol,
                side=protective_side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        _log.info(
            'bracket flatten submitted: command_id=%s exit_command_id=%s side=%s '
            'qty=%s venue_order_id=%s',
            cmd.command_id,
            exit_command_id,
            protective_side.value,
            qty,
            result.venue_order_id,
        )

        flat_order = self._scheme_child_order(runtime, client_order_id)
        if (
            flat_order is not None
            and flat_order.status in _TERMINAL_ORDER_STATUSES
            and flat_order.filled_qty > _ZERO
        ):
            await self._build_outcome(
                runtime,
                exit_cmd,
                _TERMINAL_ORDER_TO_TRADE_STATUS.get(
                    flat_order.status, TradeStatus.FILLED,
                ),
                filled_qty=flat_order.filled_qty,
                avg_fill_price=flat_order.cumulative_notional / flat_order.filled_qty,
                reason=None,
                cumulative_notional=flat_order.cumulative_notional,
            )

    async def recover_incomplete_flattens(
        self,
        account_id: str,
        events: list[tuple[int, Event]],
    ) -> None:
        '''Reconcile or re-attempt the flatten for a failed-protection bracket.

        Keyed on `ProtectionFailed` (the durable naked marker), not on
        `FlattenInitiated`, so a crash after recording the failure but before
        the flatten intent still retries — the flatten is required whenever
        the account policy is FLATTEN_THEN_HALT. The flatten client id is
        deterministic, so for each failed bracket whose flatten order has not
        settled filled the venue is queried by that id: a filled order is
        reconciled from its trades (never resubmitted), a still-working order
        is left in place, and a never-reached or terminal-unfilled order is
        re-flattened against a freshly re-capped free balance under the same
        client id.

        Args:
            account_id (str): Account whose events were just replayed.
            events (list[tuple[int, Event]]): The replayed event sequence.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        if (
            self._protection_response_for(account_id)
            is not BracketProtectionFailureResponse.FLATTEN_THEN_HALT
        ):
            return

        inits: dict[str, BracketInitialized] = {}
        failed: dict[str, ProtectionFailed] = {}
        for _seq, event in events:
            if isinstance(event, BracketInitialized):
                inits[event.command_id] = event
            elif isinstance(event, ProtectionFailed):
                failed[event.command_id] = event

        for command_id, protection_failed in failed.items():
            flatten_client_order_id = generate_client_order_id(
                ExecutionMode.BRACKET, command_id, sequence=_BRACKET_FLATTEN_SEQUENCE,
            )
            order = self._scheme_child_order(runtime, flatten_client_order_id)
            if (
                order is not None
                and order.status in _TERMINAL_ORDER_STATUSES
                and order.filled_qty > _ZERO
            ):
                continue

            init = inits.get(command_id)
            if init is None:
                _log.error(
                    'flatten recovery skipped; no bracket init: command_id=%s '
                    'account_id=%s',
                    command_id,
                    account_id,
                )

                continue

            cmd = self._bracket_command_from_init(init)
            exit_command_id = bracket_exit_command_id(command_id)
            protective_side = (
                OrderSide.SELL if cmd.side is OrderSide.BUY else OrderSide.BUY
            )

            try:
                venue_order = await self._venue_adapter.query_order(
                    cmd.account_id,
                    cmd.symbol,
                    client_order_id=flatten_client_order_id,
                )
            except NotFoundError:
                venue_order = None
            except VenueError:
                _log.exception(
                    'flatten recovery query failed; left for later reconcile: '
                    'command_id=%s',
                    command_id,
                )

                continue

            if venue_order is not None and venue_order.filled_qty > _ZERO:
                await self._reconcile_flatten_fills(
                    runtime,
                    cmd,
                    exit_command_id,
                    protective_side,
                    flatten_client_order_id,
                    venue_order,
                )

                continue

            if (
                venue_order is not None
                and venue_order.status not in _TERMINAL_ORDER_STATUSES
            ):
                _log.info(
                    'flatten recovery: order still working, left in place: '
                    'command_id=%s',
                    command_id,
                )

                continue

            await self._boot_reflatten(
                runtime, cmd, command_id, protection_failed.protection_version,
                protection_failed.oco_list_client_order_ids,
            )

    async def _reconcile_flatten_fills(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        exit_command_id: str,
        protective_side: OrderSide,
        client_order_id: str,
        venue_order: VenueOrder,
    ) -> None:
        '''Project a flatten that filled at the venue but was not recorded.

        Only projects when the local flatten order carries no fills yet: the
        fill projection sums quantities rather than deduplicating by trade id,
        so re-projecting an order that already recorded fills would double
        count. A partially-recorded order is left for the live WS reconcile.
        '''

        existing = self._scheme_child_order(runtime, client_order_id)
        if existing is not None and existing.filled_qty > _ZERO:
            _log.warning(
                'flatten recovery: order already carries fills, leaving for live '
                'reconcile: command_id=%s',
                cmd.command_id,
            )

            return

        exit_cmd = self._flatten_exit_command(
            cmd, exit_command_id, protective_side, venue_order.qty,
        )
        self._commands[exit_command_id] = exit_cmd
        self._command_trade_ids[exit_command_id] = cmd.trade_id
        runtime.command_to_order[exit_command_id] = client_order_id

        if existing is None:
            intent = OrderSubmitIntent(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                command_id=exit_command_id,
                trade_id=cmd.trade_id,
                client_order_id=client_order_id,
                symbol=cmd.symbol,
                side=protective_side,
                order_type=OrderType.MARKET,
                qty=venue_order.qty,
                quote_qty=None,
            )
            await self._event_spine.append(intent, self._epoch_id)
            runtime.trading_state.apply(intent)

            submitted = OrderSubmitted(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=client_order_id,
                venue_order_id=venue_order.venue_order_id,
                leg_client_order_ids=(),
            )
            await self._event_spine.append(submitted, self._epoch_id)
            runtime.trading_state.apply(submitted)

        trades = await self._venue_adapter.query_trades(cmd.account_id, cmd.symbol)
        for trade in trades:
            if trade.client_order_id != client_order_id:
                continue

            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=client_order_id,
                venue_order_id=venue_order.venue_order_id,
                venue_trade_id=trade.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=exit_command_id,
                symbol=cmd.symbol,
                side=protective_side,
                qty=trade.qty,
                price=trade.price,
                fee=trade.fee,
                fee_asset=trade.fee_asset,
                is_maker=trade.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        flat_order = self._scheme_child_order(runtime, client_order_id)
        if flat_order is not None and flat_order.filled_qty > _ZERO:
            await self._build_outcome(
                runtime,
                exit_cmd,
                _TERMINAL_ORDER_TO_TRADE_STATUS.get(
                    flat_order.status, TradeStatus.FILLED,
                ),
                filled_qty=flat_order.filled_qty,
                avg_fill_price=flat_order.cumulative_notional / flat_order.filled_qty,
                reason=None,
                cumulative_notional=flat_order.cumulative_notional,
            )

        _log.info(
            'flatten recovery reconciled venue fills: command_id=%s '
            'exit_command_id=%s filled=%s',
            cmd.command_id,
            exit_command_id,
            venue_order.filled_qty,
        )

    async def _backfill_terminal_order_fills(
        self,
        runtime: _AccountRuntime,
        account_id: str,
        symbol: str,
        command_id: str,
        trade_id: str,
        side: OrderSide,
        local_client_order_id: str,
        venue_client_order_ids: tuple[str, ...],
        local_filled: Decimal,
        venue_filled: Decimal,
    ) -> bool:
        '''Project venue fills an amend missed, before the order is terminalized.

        An amend queries a cancelled order's authoritative venue fill to size
        the replacement but marks the order canceled locally. A fill that raced
        the cancel and was missed on the WebSocket is otherwise lost: both the
        old and the replacement orders look terminal, and open-order
        reconciliation skips them, leaving the ledger and position short. When
        venue truth exceeds the local projection the order's trades are queried
        and any not-yet-recorded fill is projected onto `local_client_order_id`;
        the spine deduplicates on `venue_trade_id`, so an already-seen trade is a
        silent no-op. A protective OCO fills on a leg id distinct from the parent
        list id, so the venue-side match set is passed apart from the local
        attribution id.

        Returns False when the local projection could not be brought up to
        venue truth — the trade query failed, or the trades returned still fall
        short of `venue_filled` (venue eventual-consistency). The caller must
        then hold the amend for reconcile rather than terminalize the order and
        place a replacement, so a missed fill is never stranded on an order that
        open-order reconciliation would skip.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            account_id (str): Account whose order is being terminalized.
            symbol (str): Trading symbol of the order.
            command_id (str): Command the projected fills belong to.
            trade_id (str): Position trade id the fills book against.
            side (OrderSide): Side of the fills being projected.
            local_client_order_id (str): Order id the fills attribute to.
            venue_client_order_ids (tuple[str, ...]): Venue-side order ids whose
                trades belong to this order.
            local_filled (Decimal): Locally-projected filled quantity.
            venue_filled (Decimal): Authoritative venue filled quantity.

        Returns:
            bool: True when the local projection reached venue truth, False when
                the amend must be held for reconcile.
        '''

        if venue_filled <= local_filled:
            return True

        match = set(venue_client_order_ids)
        try:
            trades = await self._venue_adapter.query_trades(account_id, symbol)
        except VenueError as exc:
            _log.warning(
                'amend fill backfill query failed, holding amend for reconcile: '
                'command_id=%s reason=%s',
                command_id,
                exc.args[0] if exc.args else str(exc),
            )
            return False

        accounted = local_filled
        for trade in trades:
            if trade.client_order_id not in match:
                continue

            fill_event = FillReceived(
                account_id=account_id,
                timestamp=self._clock(),
                client_order_id=local_client_order_id,
                venue_order_id=trade.venue_order_id,
                venue_trade_id=trade.venue_trade_id,
                trade_id=trade_id,
                command_id=command_id,
                symbol=symbol,
                side=side,
                qty=trade.qty,
                price=trade.price,
                fee=trade.fee,
                fee_asset=trade.fee_asset,
                is_maker=trade.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)
                accounted += trade.qty

        return accounted >= venue_filled

    async def _boot_reflatten(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        command_id: str,
        protection_version: int,
        oco_candidates: tuple[str, ...],
    ) -> None:
        '''Re-attempt a flatten that never reached the venue after a restart.

        Passes the protective OCO list ids from `ProtectionFailed` so the same
        live-leg guard the live flatten enforced runs on boot: if the runtime
        flatten aborted because a leg was live or unconfirmable, boot recovery
        re-checks every candidate and holds rather than market-flattening
        against a still-live protective OCO.
        '''

        entry_client_order_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=_BRACKET_ENTRY_SEQUENCE,
        )
        bracket = _LiveBracket(
            command=cmd, entry_client_order_id=entry_client_order_id,
        )
        exit_command_id = bracket_exit_command_id(command_id)
        entry_filled, _ = self._command_fill_totals(runtime, cmd.command_id)
        exit_filled, _ = self._command_fill_totals(runtime, exit_command_id)
        remainder = entry_filled - exit_filled
        _log.warning(
            'flatten recovery: re-attempting flatten never confirmed at venue: '
            'command_id=%s',
            command_id,
        )
        await self._flatten_bracket_remainder(
            runtime, bracket, protection_version, 'boot flatten recovery',
            remainder, oco_candidates,
        )

    async def _on_slice_failure(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        client_order_id: str,
        reason: str,
    ) -> None:
        '''Freeze a scheme on a slice failure and report a PARTIAL outcome.

        Per RFC 5.13: a slice that cannot be placed or a child that
        terminates without filling does not fail the whole command. A
        durable `SliceFailed` is appended, a non-terminal PARTIAL outcome
        with the fills gathered so far is reported to the Manager, and the
        scheme is frozen — no further slices are scheduled. It waits for the
        Manager (`TradeAbort`, or `TradeModify` once amend lands) or for its
        deadline, both of which drive the single terminal outcome.
        '''

        cmd = scheme.command
        _log.warning(
            'scheme slice failed; freezing to await Manager: command_id=%s reason=%s',
            cmd.command_id,
            reason,
        )

        failed = SliceFailed(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            client_order_id=client_order_id,
            reason=reason,
        )
        await self._event_spine.append(failed, self._epoch_id)

        scheme.frozen = True
        scheme.next_run_at = None

        await self._emit_scheme_partial(runtime, scheme, reason)

    async def _emit_scheme_partial(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        reason: str | None,
    ) -> None:
        '''Report a non-terminal PARTIAL outcome for a frozen scheme.

        Mirrors `_emit_scheme_terminal` but leaves the scheme live: no
        terminal command bookkeeping, no `TradeClosed`. The aggregated fills
        so far are derived from the child order projections and clamped to
        the command target.
        '''

        cmd = scheme.command
        ts = self._clock()
        filled_qty, cumulative_notional = self._command_fill_totals(runtime, cmd.command_id)

        if cmd.qty is not None and filled_qty > cmd.qty:
            if filled_qty > _ZERO:
                cumulative_notional = cumulative_notional * cmd.qty / filled_qty
            filled_qty = cmd.qty

        avg_fill_price = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        outcome = TradeOutcome(
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            account_id=cmd.account_id,
            status=TradeStatus.PARTIAL,
            target_qty=cmd.qty,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            slices_completed=scheme.cursor,
            slices_total=scheme.slices_total,
            reason=reason,
            created_at=ts,
            cumulative_notional=cumulative_notional,
        )

        produced = TradeOutcomeProduced(
            account_id=cmd.account_id,
            timestamp=ts,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            status=TradeStatus.PARTIAL,
            reason=reason,
            filled_qty=filled_qty,
            cumulative_notional=cumulative_notional,
            target_qty=cmd.qty,
        )
        await self._event_spine.append(produced, self._epoch_id)
        runtime.trading_state.apply(produced)

        await self._dispatch_outcome_with_retry(outcome, source='scheme_partial')

    async def _expire_scheme(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
    ) -> None:
        '''Force-terminate a scheme that exceeded its deadline.

        The deadline backstop: a scheme still live at its `command.timeout`
        wall-clock — a frozen scheme the Manager never acted on, or one
        stuck on a child that never settles — is expired. Working children
        are cancelled and the single terminal outcome is EXPIRED once they
        drain.
        '''

        _log.warning(
            'scheme deadline exceeded; expiring: command_id=%s account_id=%s',
            scheme.command.command_id,
            runtime.account_id,
        )

        scheme.pending_terminal = (
            TradeStatus.EXPIRED,
            SchemeState.FAILED,
            'scheme deadline exceeded',
        )
        scheme.next_run_at = None
        await self._cancel_active_children(runtime, scheme)
        await self._maybe_finalize_scheme(runtime, scheme)

    async def _emit_scheme_terminal(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        *,
        status: TradeStatus,
        filled_qty: Decimal,
        cumulative_notional: Decimal,
        slices_completed: int,
        slices_total: int,
        reason: str | None,
    ) -> TradeOutcome:
        '''Build the aggregated terminal `TradeOutcome` for a scheme command.

        Mirrors `_build_outcome` for a multi-slice parent: clamps an
        overfill to the command target, records terminal command
        bookkeeping, closes the position when the aggregated fills reduce
        it to dust, appends `TradeOutcomeProduced`, and dispatches the
        single outcome to the Manager callback.
        '''

        ts = self._clock()

        if cmd.qty is not None and filled_qty > cmd.qty:
            _log.warning(
                'scheme overfill detected: command_id=%s filled_qty=%s target_qty=%s; clamping',
                cmd.command_id,
                filled_qty,
                cmd.qty,
            )
            if filled_qty > _ZERO:
                cumulative_notional = cumulative_notional * cmd.qty / filled_qty
            filled_qty = cmd.qty

        avg_fill_price = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        outcome = TradeOutcome(
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            account_id=cmd.account_id,
            status=status,
            target_qty=cmd.qty,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            slices_completed=slices_completed,
            slices_total=slices_total,
            reason=reason,
            created_at=ts,
            cumulative_notional=cumulative_notional,
        )

        self._terminal_commands.add(cmd.command_id)
        self._commands.pop(cmd.command_id, None)
        self._aborted_commands.pop(cmd.command_id, None)

        if filled_qty > _ZERO and self._closes_position(
            runtime, cmd.account_id, cmd.trade_id, cmd.side
        ):
            closed = TradeClosed(
                account_id=cmd.account_id,
                timestamp=ts,
                trade_id=cmd.trade_id,
                command_id=cmd.command_id,
            )
            await self._event_spine.append(closed, self._epoch_id)
            self._project(runtime, closed)

        produced = TradeOutcomeProduced(
            account_id=cmd.account_id,
            timestamp=ts,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            status=status,
            reason=reason,
            filled_qty=filled_qty,
            cumulative_notional=cumulative_notional,
            target_qty=cmd.qty,
        )
        await self._event_spine.append(produced, self._epoch_id)
        runtime.trading_state.apply(produced)

        await self._dispatch_outcome_with_retry(outcome, source='scheme')

        return outcome

    async def _process_abort(
        self,
        runtime: _AccountRuntime,
        abort: TradeAbort,
    ) -> TradeOutcome | None:
        '''
        Cancel an active order and report CANCELED outcome.

        Look up the target order by command_id. If found, cancel via
        venue adapter, emit OrderCanceled on success or NotFoundError,
        and build a CANCELED TradeOutcome with cumulative fill data.
        If no order exists yet, mark for pre-submission short-circuit.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            abort (TradeAbort): Abort instruction to process.

        Returns:
            TradeOutcome | None: CANCELED outcome, or None if deferred
                or already terminal.
        '''

        if abort.command_id in self._terminal_commands:
            _log.info(
                'abort no-op (command already terminal): command_id=%s',
                abort.command_id,
            )
            return None

        if abort.command_id in runtime.schemes:
            await self._abort_scheme(runtime, abort)
            return None

        client_order_id = runtime.command_to_order.get(abort.command_id)
        order = (
            runtime.trading_state.orders.get(client_order_id)
            if client_order_id
            else None
        )

        if order is None:
            if abort.command_id in self._accepted_commands:
                self._aborted_commands[abort.command_id] = abort.reason
                _log.info(
                    'abort marked for pre-submission: command_id=%s',
                    abort.command_id,
                )
            else:
                _log.warning(
                    'abort for unknown command: command_id=%s',
                    abort.command_id,
                )
            return None

        filled_qty = order.filled_qty
        venue_order_id = order.venue_order_id

        reason = abort.reason
        cancel_confirmed = True
        try:
            if order.order_type == OrderType.OCO:
                await self._venue_adapter.cancel_order_list(
                    order.account_id,
                    order.symbol,
                    client_order_id=client_order_id,
                )
            else:
                await self._venue_adapter.cancel_order(
                    order.account_id,
                    order.symbol,
                    client_order_id=client_order_id,
                )
        except NotFoundError:
            pass
        except VenueError as exc:
            reason = f"{abort.reason}; cancel failed: {exc.args[0]}"
            cancel_confirmed = False

        if cancel_confirmed:
            canceled = OrderCanceled(
                account_id=order.account_id,
                timestamp=self._clock(),
                client_order_id=order.client_order_id,
                venue_order_id=venue_order_id,
                reason=abort.reason,
            )
            await self._event_spine.append(canceled, self._epoch_id)
            runtime.trading_state.apply(canceled)

        avg_fill_price: Decimal | None = None
        if filled_qty > _ZERO:
            avg_fill_price = order.cumulative_notional / filled_qty

        trade_id = self._command_trade_ids.get(abort.command_id)
        if trade_id is None:
            _log.error(
                'abort outcome skipped: missing trade_id for command_id=%s '
                'account_id=%s client_order_id=%s',
                abort.command_id,
                order.account_id,
                client_order_id,
            )
            return None

        return await self._build_abort_outcome(
            runtime,
            order,
            trade_id,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            reason=reason,
        )

    async def _process_modify(  # noqa: PLR0911
        self,
        runtime: _AccountRuntime,
        modify: TradeModify,
    ) -> None:
        '''Apply an order-price amend to a resting single order.

        Cancel-then-query-then-place: the resting order is cancelled, the
        venue is queried for the authoritative filled quantity, and a
        replacement is placed for the unfilled remainder at the amended
        price. Deriving the remainder from the venue's post-cancel truth —
        not a stale local snapshot — means a fill racing the cancel can
        never make the replacement over-order. A durable
        `OrderAmendInitiated` is written before the cancel; on boot the amend
        sequence is rebuilt from it so a later amend cannot reuse a client
        order id, and a crash mid-amend recovers to a safe state through the
        existing boot reconcile (the order rests at the old price if never
        cancelled, or terminalizes if it was) — completing the re-price
        across a crash is a follow-up. Fills carry across the superseded and
        replacement orders through `_command_fill_totals`, so the command's
        outcome stays correct; in the rare case where a fill lands on the
        old order between the query and the replacement, that fill is still
        captured in the projection (its WebSocket report applies as usual)
        and the outcome reconverges on the next fill, with position and
        ledger always exact.

        A running scheme (TWAP / Time DCA / Scheduled VWAP) is routed to
        `_process_scheme_modify`; single resting-order modes (SingleShot
        LIMIT, Iceberg) are amended here; other modes are rejected pending
        their own slices.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            modify (TradeModify): Amend instruction targeting a command.
        '''

        command_id = modify.command_id

        if isinstance(modify.modify_params, BracketModify):
            await self._process_bracket_modify(
                runtime, command_id, modify.modify_params,
            )
            return

        if command_id in self._terminal_commands:
            _log.info('modify no-op (command terminal): command_id=%s', command_id)
            return

        cmd = self._commands.get(command_id)
        if cmd is None:
            _log.warning('modify for unknown command: command_id=%s', command_id)
            return

        if command_id in runtime.pending_amends:
            _log.warning(
                'modify rejected: a prior amend is held pending fill '
                'reconciliation: command_id=%s', command_id,
            )
            return

        scheme = runtime.schemes.get(command_id)
        if scheme is not None:
            if isinstance(
                modify.modify_params,
                (TwapModify, TimeDcaModify, ScheduledVwapModify),
            ):
                await self._process_scheme_modify(runtime, scheme, modify)
            elif isinstance(modify.modify_params, LadderDcaModify):
                await self._process_ladder_modify(runtime, scheme, modify)
            else:
                _log.warning(
                    'modify rejected: amend not yet supported for mode %s command_id=%s',
                    cmd.execution_mode.value,
                    command_id,
                )
            return

        if not isinstance(modify.modify_params, (SingleShotModify, IcebergModify)):
            _log.warning(
                'modify rejected: amend not yet supported for mode %s command_id=%s',
                cmd.execution_mode.value,
                command_id,
            )
            return

        if isinstance(modify.modify_params, SingleShotModify) and (
            modify.modify_params.stop_price is not None
            or modify.modify_params.stop_limit_price is not None
        ):
            _log.warning(
                'modify rejected: stop-field amend not supported '
                '(limit price only): command_id=%s',
                command_id,
            )
            return

        old_client_order_id = runtime.command_to_order.get(command_id)
        order = (
            runtime.trading_state.orders.get(old_client_order_id)
            if old_client_order_id
            else None
        )
        if order is None or order.order_type is not OrderType.LIMIT:
            _log.warning(
                'modify rejected: no resting LIMIT order for command_id=%s', command_id,
            )
            return

        assert old_client_order_id is not None
        assert cmd.qty is not None
        new_price, new_display = self._resolve_amend(cmd, modify.modify_params)
        if new_price is None:
            _log.warning(
                'modify rejected: no limit price to amend command_id=%s', command_id,
            )
            return

        amend_seq = runtime.amend_counts.get(command_id, 0) + 1
        new_client_order_id = generate_client_order_id(
            cmd.execution_mode, command_id, sequence=amend_seq,
        )

        amend_event = OrderAmendInitiated(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=command_id,
            trade_id=cmd.trade_id,
            symbol=cmd.symbol,
            side=cmd.side,
            total_qty=cmd.qty,
            old_client_order_id=old_client_order_id,
            new_client_order_id=new_client_order_id,
            price=new_price,
            display_qty=new_display,
        )
        await self._event_spine.append(amend_event, self._epoch_id)
        runtime.amend_counts[command_id] = amend_seq

        venue_order = await self._cancel_and_query(cmd, old_client_order_id)
        if venue_order is None:
            _log.warning(
                'modify aborted: order state unconfirmed, leaving order live: '
                'command_id=%s',
                command_id,
            )
            return

        if venue_order.status not in _TERMINAL_ORDER_STATUSES:
            _log.warning(
                'modify aborted: order still live at venue, not replacing: '
                'command_id=%s status=%s',
                command_id,
                venue_order.status.value,
            )
            return

        if venue_order.status is OrderStatus.FILLED:
            # The order filled at the venue rather than cancelling; leave it
            # open locally so its pending fills settle to the command total.
            await self._emit_amend_outcome(runtime, cmd)
            return

        # The order cancelled (terminal, not filled); complete the amend once
        # the venue fill reconciles, else park it for the reconcile scan.
        pending = _PendingSingleAmend(
            old_client_order_id=old_client_order_id,
            new_client_order_id=new_client_order_id,
            new_price=new_price,
            new_display=new_display,
        )
        completed = await self._drive_single_amend(runtime, cmd, pending, venue_order)
        if not completed:
            runtime.pending_amends[command_id] = pending
            _log.warning(
                'modify held: venue fill unreconciled after cancel; parked for '
                'the reconcile scan to retry rather than terminalizing the old '
                'order and placing a replacement against an understated ledger: '
                'command_id=%s',
                command_id,
            )

    async def _drive_single_amend(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        pending: _PendingSingleAmend,
        venue_order: VenueOrder,
    ) -> bool:
        '''Complete a single-order amend once its venue fill reconciles.

        Projects any fill the cancel raced before terminalizing the old order,
        then places the remainder at the amended price. Returns False when the
        backfill cannot reach venue truth: the caller then leaves the amend
        parked and the old order non-terminal so the missed fill stays
        recoverable on the next reconcile scan rather than being stranded on a
        terminal order behind an understated ledger. Shared by the live amend
        and the scan retry, so a re-drive after the old order was already
        terminalized by reconcile still sizes and places the replacement.
        '''

        old = pending.old_client_order_id
        order = self._scheme_child_order(runtime, old)
        local_filled = order.filled_qty if order is not None else _ZERO
        reconciled = await self._backfill_terminal_order_fills(
            runtime, cmd.account_id, cmd.symbol, cmd.command_id, cmd.trade_id,
            cmd.side, old, (old,), local_filled, venue_order.filled_qty,
        )
        if not reconciled:
            return False

        if runtime.trading_state.orders.get(old) is not None:
            canceled = OrderCanceled(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=old,
                venue_order_id=venue_order.venue_order_id,
                reason='amend',
            )
            await self._event_spine.append(canceled, self._epoch_id)
            runtime.trading_state.apply(canceled)

        assert cmd.qty is not None
        command_filled, _ = self._command_fill_totals(runtime, cmd.command_id)
        remainder = cmd.qty - command_filled
        filters = self._venue_adapter.cached_filters(cmd.symbol)
        lot_min = filters.lot_min if filters is not None else _ZERO

        if remainder <= _ZERO or remainder < lot_min:
            # Only sub-lot dust remains after the cancel; it cannot be
            # re-placed, so the command completes on the fills so far — the
            # same dust shortfall a scheme reports FILLED.
            await self._emit_amend_terminal(runtime, cmd)
            return True

        await self._place_amend_replacement(
            runtime, cmd, pending.new_client_order_id, pending.new_price,
            pending.new_display, remainder,
        )
        return True

    async def resolve_pending_amends(self, account_id: str) -> None:
        '''Retry each single-order amend held pending fill reconciliation.

        A single-order amend parks when the fill the cancel raced could not be
        reconciled to venue truth. On each reconcile scan the parked order is
        re-queried and re-driven: once the projection reaches venue truth the
        old order is terminalized and the replacement placed, and the park is
        cleared. A re-query that cannot confirm the order leaves it parked for
        the next scan.

        Args:
            account_id (str): Account whose parked amends to retry.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        for command_id, pending in list(runtime.pending_amends.items()):
            cmd = self._commands.get(command_id)
            if cmd is None:
                runtime.pending_amends.pop(command_id, None)
                continue

            venue_order = await self._cancel_and_query(
                cmd, pending.old_client_order_id,
            )
            if venue_order is None or venue_order.status not in _TERMINAL_ORDER_STATUSES:
                continue

            completed = await self._drive_single_amend(
                runtime, cmd, pending, venue_order,
            )
            if completed:
                runtime.pending_amends.pop(command_id, None)

    async def _process_ladder_modify(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        modify: TradeModify,
    ) -> None:
        '''Amend a resting ladder's grid by strict two-phase cancel-then-place.

        A ladder rests one LIMIT rung per level; a `LadderDcaModify` gives an
        absolute new grid for the unfilled remainder. The amend is a durable
        state machine that never adds exposure over a live rung: it persists
        `LadderAmendInitiated` before touching the venue, retires every
        old-generation rung and confirms each venue-terminal, and only then —
        once the remainder is venue-truth — persists `LadderAmendPlanned` (the
        exact replacement rungs) and places them at `retry=generation`,
        finishing at `LadderAmendCompleted`. A cancel/query that cannot confirm
        halts in `LadderAmendStateUnknown` for the watchdog; a failure with no
        rung yet cancelled aborts cleanly and leaves the old grid untouched.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            scheme (_LiveScheme): The live ladder being amended.
            modify (TradeModify): Amend carrying a `LadderDcaModify`.
        '''

        cmd = scheme.command
        command_id = cmd.command_id
        params = modify.modify_params
        assert isinstance(params, LadderDcaModify)

        if scheme.amend_phase is not None:
            _log.warning(
                'ladder modify rejected: an amend is already in flight: '
                'command_id=%s phase=%s',
                command_id,
                scheme.amend_phase,
            )
            return

        if scheme.frozen or scheme.pending_terminal is not None:
            _log.warning(
                'ladder modify rejected: ladder frozen or stopping, not '
                'amendable: command_id=%s',
                command_id,
            )
            return

        if not isinstance(cmd.execution_params, LadderDcaParams):
            _log.warning(
                'ladder modify rejected: not a ladder command: command_id=%s',
                command_id,
            )
            return

        current = cmd.execution_params
        new_price_levels = (
            params.price_levels if params.price_levels is not None
            else current.price_levels
        )
        new_weights = (
            params.level_weights if params.level_weights is not None
            else current.level_weights
        )
        try:
            LadderDcaParams(
                price_levels=new_price_levels, level_weights=new_weights,
            )
        except ValueError as exc:
            _log.warning(
                'ladder modify rejected: amended grid invalid: command_id=%s '
                'reason=%s',
                command_id,
                exc,
            )
            return

        old_generation = scheme.amend_generation
        new_generation = old_generation + 1

        initiated = LadderAmendInitiated(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=command_id,
            generation=new_generation,
            price_levels=new_price_levels,
            level_weights=new_weights or (),
            old_slices_total=scheme.slices_total,
            new_slices_total=len(new_price_levels),
        )
        await self._event_spine.append(initiated, self._epoch_id)
        scheme.amend_phase = 'CANCELLING'
        scheme.amend_context = _LadderAmendContext(
            old_generation=old_generation,
            new_generation=new_generation,
            old_slices_total=scheme.slices_total,
            price_levels=new_price_levels,
            level_weights=new_weights or (),
        )

        await self._drive_ladder_amend(runtime, scheme)

    async def _drive_ladder_amend(
        self, runtime: _AccountRuntime, scheme: _LiveScheme,
    ) -> None:
        '''Advance an in-flight ladder amend from its current phase to done.

        Shared by the live driver, the reconcile watchdog, and boot resume, so
        an amend finishes identically whether it just started, stalled in
        STATE_UNKNOWN, or crashed mid-flight. CANCELLING retires and confirms
        every old rung, then fixes and persists the replacement plan; PLACING
        places the planned rungs. Each step is idempotent — already-terminal
        old rungs and already-resting new rungs are adopted — so re-driving
        never double-cancels or double-places.
        '''

        cmd = scheme.command
        ctx = scheme.amend_context
        if ctx is None:
            return

        new_params = LadderDcaParams(
            price_levels=ctx.price_levels,
            level_weights=ctx.level_weights or None,
        )

        if scheme.amend_phase == 'CANCELLING':
            retired = await self._retire_ladder_generation(
                runtime, cmd, scheme,
                ctx.old_generation, ctx.old_slices_total, ctx.new_generation,
            )
            if retired is None:
                return

            venue_filled, projected_filled = retired
            assert cmd.qty is not None
            command_filled, _ = self._command_fill_totals(runtime, cmd.command_id)
            remainder = cmd.qty - (command_filled - projected_filled + venue_filled)
            planned = self._plan_ladder_amend(cmd, new_params, remainder)

            if not planned:
                await self._complete_ladder_amend(
                    runtime, cmd, scheme, ctx.new_generation, new_params,
                )
                return

            planned_event = LadderAmendPlanned(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                command_id=cmd.command_id,
                generation=ctx.new_generation,
                sequences=tuple(index for index, _price, _qty in planned),
                prices=tuple(price for _index, price, _qty in planned),
                qtys=tuple(qty for _index, _price, qty in planned),
            )
            await self._event_spine.append(planned_event, self._epoch_id)
            ctx.planned = planned
            scheme.amend_phase = 'PLACING'

        if scheme.amend_phase == 'PLACING':
            if scheme.protection_frozen:
                _log.info(
                    'ladder amend placement held: protection frozen, no new '
                    'rungs placed: command_id=%s',
                    cmd.command_id,
                )
                return

            assert ctx.planned is not None
            await self._place_ladder_generation(
                runtime, cmd, scheme, ctx.new_generation, ctx.planned, new_params,
            )

    def _plan_ladder_amend(
        self,
        cmd: TradeCommand,
        new_params: LadderDcaParams,
        remainder: Decimal,
    ) -> list[tuple[int, Decimal, Decimal]]:
        '''Plan the replacement rungs (re-indexed 0..M-1) for the remainder.

        The remainder is split across the new grid and floored to the lot
        step; a rung that floors to a sub-lot or sub-notional quantity is
        dropped and the survivors are re-indexed contiguously so resume scans
        a gap-free `0..M-1`. An empty plan means the remainder is untradeable
        dust and the ladder finalizes on the fills so far.
        '''

        filters = self._venue_adapter.cached_filters(cmd.symbol)
        lot_step = filters.lot_step if filters is not None else None
        lot_min = filters.lot_min if filters is not None else _ZERO
        min_notional = filters.min_notional if filters is not None else _ZERO

        if remainder <= _ZERO:
            return []

        levels = _ladder_levels(new_params, remainder, lot_step)
        planned: list[tuple[int, Decimal, Decimal]] = []
        for qty, price in levels:
            if qty < lot_min or qty * price < min_notional:
                continue

            planned.append((len(planned), price, qty))

        return planned

    async def _retire_ladder_generation(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        scheme: _LiveScheme,
        old_generation: int,
        old_slices_total: int,
        new_generation: int,
    ) -> tuple[Decimal, Decimal] | None:
        '''Cancel and venue-confirm every old-generation rung terminal.

        Returns `(venue_filled, projected_filled)` for the old grid once every
        rung is positively terminal: `venue_filled` sums each rung's
        authoritative venue quantity (queried after cancel, or the projection
        for a rung already terminal), and `projected_filled` sums the same
        rungs' local projections. The caller replaces the retiring generation's
        projected fills inside the command total with `venue_filled`, so the
        remainder stays exact across repeated amends. `cancel_committed` is set
        the moment a cancel is sent — a sent-but-unconfirmed cancel may already
        have retired the rung — so any failure after that point is
        `LadderAmendStateUnknown` for the watchdog, never a clean abort.
        Returns None in every halt case.
        '''

        ctx = scheme.amend_context
        total_filled = _ZERO
        projected_filled = _ZERO
        for index in range(old_slices_total):
            rung_id = generate_client_order_id(
                ExecutionMode.LADDER_DCA, cmd.command_id,
                sequence=index, retry=old_generation,
            )
            order = self._scheme_child_order(runtime, rung_id)
            if order is None:
                continue

            if order.status in _TERMINAL_ORDER_STATUSES:
                if order.status is OrderStatus.CANCELED and ctx is not None:
                    ctx.cancel_committed = True

                projected_filled += order.filled_qty
                total_filled += order.filled_qty
                scheme.active_children.discard(rung_id)
                continue

            if ctx is not None:
                ctx.cancel_committed = True

            try:
                await self._venue_adapter.cancel_order(
                    cmd.account_id, cmd.symbol, client_order_id=rung_id,
                )
            except NotFoundError:
                pass
            except VenueError:
                await self._halt_ladder_amend(
                    cmd, scheme, new_generation, 'CANCELLING', 'rung cancel failed',
                )
                return None

            try:
                venue_order = await self._venue_adapter.query_order(
                    cmd.account_id, cmd.symbol, client_order_id=rung_id,
                )
            except (NotFoundError, VenueError):
                await self._halt_ladder_amend(
                    cmd, scheme, new_generation, 'CANCELLING',
                    'rung query unconfirmable after cancel',
                )
                return None

            if venue_order.status not in _TERMINAL_ORDER_STATUSES:
                await self._halt_ladder_amend(
                    cmd, scheme, new_generation, 'CANCELLING',
                    'rung still live after cancel',
                )
                return None

            reconciled = await self._backfill_terminal_order_fills(
                runtime, cmd.account_id, cmd.symbol, cmd.command_id, cmd.trade_id,
                cmd.side, rung_id, (rung_id,),
                order.filled_qty, venue_order.filled_qty,
            )
            if not reconciled:
                await self._halt_ladder_amend(
                    cmd, scheme, new_generation, 'CANCELLING',
                    'rung fills unreconciled after cancel',
                )
                return None

            if runtime.trading_state.orders.get(rung_id) is not None:
                canceled = OrderCanceled(
                    account_id=cmd.account_id,
                    timestamp=self._clock(),
                    client_order_id=rung_id,
                    venue_order_id=order.venue_order_id,
                    reason='ladder amend',
                )
                await self._event_spine.append(canceled, self._epoch_id)
                runtime.trading_state.apply(canceled)

            projected_filled += order.filled_qty
            total_filled += venue_order.filled_qty
            scheme.active_children.discard(rung_id)

        return total_filled, projected_filled

    async def _halt_ladder_amend(
        self,
        cmd: TradeCommand,
        scheme: _LiveScheme,
        generation: int,
        phase: str,
        reason: str,
    ) -> None:
        '''Abort a torn-free amend or hold an unconfirmable one for the watchdog.

        The amend may abort cleanly (durable `LadderAmendAborted`, ladder
        resumes running) only while no cancel has ever been committed to the
        venue — a decision that must hold across watchdog retries and a restart,
        so it reads the context's `cancel_committed` (set the moment a cancel is
        sent, and true for any resumed amend) rather than a per-drive count that
        resets each retry. Once a cancel is committed the venue may already have
        retired a rung, so the amend holds in `LadderAmendStateUnknown` with its
        phase for the reconcile watchdog to finish.
        '''

        committed = scheme.amend_context is not None and scheme.amend_context.cancel_committed
        if not committed:
            aborted = LadderAmendAborted(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                command_id=cmd.command_id,
                generation=generation,
                reason=reason,
            )
            await self._event_spine.append(aborted, self._epoch_id)
            scheme.amend_phase = None
            scheme.amend_context = None
            _log.warning(
                'ladder amend aborted, old grid intact: command_id=%s reason=%s',
                cmd.command_id,
                reason,
            )
            return

        unknown = LadderAmendStateUnknown(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            generation=generation,
            phase=phase,
            reason=reason,
        )
        await self._event_spine.append(unknown, self._epoch_id)
        scheme.amend_phase = phase
        _log.warning(
            'ladder amend unconfirmable; holding for watchdog: command_id=%s '
            'phase=%s reason=%s',
            cmd.command_id,
            phase,
            reason,
        )

    async def _place_ladder_generation(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        scheme: _LiveScheme,
        generation: int,
        planned: list[tuple[int, Decimal, Decimal]],
        new_params: LadderDcaParams,
    ) -> None:
        '''Place the planned new-generation rungs, then complete the amend.

        Each planned rung already resting (crash-resume) is adopted; a missing
        one is placed at `retry=generation`. A placement failure halts in
        `LadderAmendStateUnknown` (PLACING) with the placed rungs resting for
        the watchdog to finish; otherwise the new grid becomes the live grid
        and the amend completes.
        '''

        new_active: set[str] = set()
        for index, price, qty in planned:
            rung_id = generate_client_order_id(
                ExecutionMode.LADDER_DCA, cmd.command_id,
                sequence=index, retry=generation,
            )
            existing = self._scheme_child_order(runtime, rung_id)
            if existing is not None:
                if existing.status not in _TERMINAL_ORDER_STATUSES:
                    new_active.add(rung_id)
                    continue

                if existing.status is OrderStatus.FILLED:
                    continue

                await self._halt_ladder_amend(
                    cmd, scheme, generation, 'PLACING',
                    f'ladder amend rung {index} terminated '
                    f'{existing.status.value} without fill',
                )
                return

            client_order_id = await self._submit_limit_level(
                runtime, cmd, index, qty, price, generation=generation,
            )
            if client_order_id is None:
                await self._halt_ladder_amend(
                    cmd, scheme, generation, 'PLACING',
                    f'ladder amend rung {index} placement failed',
                )
                return

            order = self._scheme_child_order(runtime, client_order_id)
            if order is not None and order.status not in _TERMINAL_ORDER_STATUSES:
                new_active.add(client_order_id)

        scheme.active_children |= new_active
        scheme.slice_qtys = [qty for _index, _price, qty in planned]
        scheme.slices_total = len(planned)
        scheme.cursor = len(planned)
        await self._complete_ladder_amend(runtime, cmd, scheme, generation, new_params)

    async def _complete_ladder_amend(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        scheme: _LiveScheme,
        generation: int,
        new_params: LadderDcaParams,
    ) -> None:
        '''Mark the amend complete and adopt the new grid as the live grid.

        Persists `LadderAmendCompleted`, promotes the generation, updates the
        command's params so a later amend merges against the new grid, clears
        the amend phase, and lets the ladder finalize once its rungs settle.
        An amend that placed nothing (dust remainder) leaves `slices_total`
        unchanged so the already-satisfied cursor finalizes the ladder FILLED.
        '''

        completed = LadderAmendCompleted(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            generation=generation,
        )
        await self._event_spine.append(completed, self._epoch_id)

        new_command = replace(cmd, execution_params=new_params)
        scheme.command = new_command
        self._commands[cmd.command_id] = new_command
        scheme.amend_generation = generation
        scheme.amend_phase = None
        scheme.amend_context = None

        _log.info(
            'ladder amend complete: command_id=%s generation=%d rungs=%d',
            cmd.command_id,
            generation,
            scheme.slices_total,
        )
        await self._maybe_finalize_scheme(runtime, scheme)

    async def _process_bracket_modify(
        self,
        runtime: _AccountRuntime,
        command_id: str,
        params: BracketModify,
    ) -> None:
        '''Amend a live bracket's protective OCO by cancel-then-replace.

        Drives the durable `Protection*` state machine: the partial
        `BracketModify` is merged against the bracket's current legs into a
        full two-leg snapshot, `ProtectionAmendRequested` is persisted before
        the venue cancel, the resting OCO is cancelled, the remaining exposure
        is reconciled from venue truth (entry filled minus the cancelled OCO's
        filled), and a replacement OCO is placed for that remainder. Each
        spine append precedes the venue action it authorizes
        (persist-before-cancel, persist-before-place). Success ends in
        `ProtectionActive` with the bracket re-pointed at the new list; an
        ambiguous cancel halts in `ProtectionStateUnknown` for reconciliation;
        a definitive replace failure lands in `ProtectionFailed`. The response
        to a failed protection (flatten / reduce-only) is handled elsewhere.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            command_id (str): Bracket command whose protective OCO is amended.
            params (BracketModify): Partial amend of the protective legs.
        '''

        bracket = runtime.brackets.get(command_id)
        if bracket is None:
            _log.warning(
                'bracket modify rejected: no live bracket for command_id=%s',
                command_id,
            )
            return

        if not bracket.protection_placed or bracket.protection_client_order_id is None:
            _log.warning(
                'bracket modify rejected: no live protective OCO for command_id=%s',
                command_id,
            )
            return

        if bracket.protection_status is not BracketProtectionStatus.ACTIVE:
            _log.warning(
                'bracket modify rejected: protection not ACTIVE (status=%s) '
                'command_id=%s',
                bracket.protection_status.value,
                command_id,
            )
            return

        if bracket.avg_entry_price is None:
            _log.warning(
                'bracket modify rejected: no entry reference for command_id=%s',
                command_id,
            )
            return

        cmd = bracket.command
        resolved = self._resolve_bracket_amend(bracket, params)
        if resolved is None:
            _log.warning(
                'bracket modify rejected: amended legs invalid for entry '
                'command_id=%s',
                command_id,
            )
            return

        tp_price, sl_stop_price, sl_limit_price = resolved
        old_list_client_order_id = bracket.protection_client_order_id
        new_version = bracket.protection_version + 1
        new_list_client_order_id = generate_client_order_id(
            cmd.execution_mode,
            cmd.command_id,
            sequence=_BRACKET_PROTECTION_SEQUENCE,
            retry=new_version,
        )

        requested = ProtectionAmendRequested(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=new_version,
            new_list_client_order_id=new_list_client_order_id,
            old_list_client_order_id=old_list_client_order_id,
            take_profit_price=tp_price,
            stop_loss_price=sl_stop_price,
            stop_loss_limit_price=sl_limit_price,
        )
        await self._event_spine.append(requested, self._epoch_id)
        bracket.protection_version = new_version
        bracket.protection_status = BracketProtectionStatus.AMEND_REQUESTED

        try:
            cancel_result = await self._venue_adapter.cancel_order_list(
                cmd.account_id, cmd.symbol, client_order_id=old_list_client_order_id,
            )
        except VenueError as exc:
            reason = str(exc.args[0]) if exc.args else str(exc)
            await self._append_protection_state_unknown(
                cmd, new_version, reason,
                old_list_client_order_id=old_list_client_order_id,
            )
            bracket.protection_status = BracketProtectionStatus.STATE_UNKNOWN
            bracket.unknown_since = self._clock()
            _log.warning(
                'bracket protective cancel ambiguous; halting amend for '
                'reconcile: command_id=%s version=%d reason=%s',
                cmd.command_id,
                new_version,
                reason,
            )
            return

        cancel_confirmed = ProtectionCancelConfirmed(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=new_version,
        )
        await self._event_spine.append(cancel_confirmed, self._epoch_id)
        bracket.protection_status = BracketProtectionStatus.CANCEL_CONFIRMED

        bracket.amend_new_list_client_order_id = new_list_client_order_id
        bracket.amend_tp_price = tp_price
        bracket.amend_sl_stop_price = sl_stop_price
        bracket.amend_sl_limit_price = sl_limit_price

        await self._drive_bracket_protection_amend(
            runtime, bracket, cancel_result.venue_order_id,
        )

    async def _drive_bracket_protection_amend(  # noqa: PLR0911
        self,
        runtime: _AccountRuntime,
        bracket: _LiveBracket,
        cancel_venue_order_id: str | None,
    ) -> None:
        '''Complete a cancel-confirmed protective-OCO amend once fills reconcile.

        Shared by the live amend and the reconcile scan: with the old OCO
        cancelled, reconcile its authoritative protective fill, then terminalize
        it and place the replacement OCO for the remaining exposure. When the
        fill cannot be reconciled the amend is parked in `CANCEL_CONFIRMED` and
        the scan retries — never `STATE_UNKNOWN`, whose watchdog would remediate
        a merely under-projected position as naked. If the fill is still
        unreconciled when the restore deadline elapses the replacement is placed
        from venue truth anyway: a bounded ledger gap the balance reconciler
        surfaces is preferable to flattening the position over a transient
        trade-query failure.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            bracket (_LiveBracket): The bracket whose amend to complete; carries
                the replacement legs and list id resolved at request time.
            cancel_venue_order_id (str | None): The old OCO's venue id from the
                live cancel, or None on a scan re-drive.
        '''

        cmd = bracket.command
        new_version = bracket.protection_version
        old_list_client_order_id = bracket.protection_client_order_id
        new_list_client_order_id = bracket.amend_new_list_client_order_id
        tp_price = bracket.amend_tp_price
        sl_stop_price = bracket.amend_sl_stop_price
        sl_limit_price = bracket.amend_sl_limit_price
        assert old_list_client_order_id is not None
        assert new_list_client_order_id is not None
        assert tp_price is not None
        assert sl_stop_price is not None

        entry_filled, _ = self._command_fill_totals(runtime, cmd.command_id)
        exit_command_id = bracket_exit_command_id(cmd.command_id)
        exit_projected, _ = self._command_fill_totals(runtime, exit_command_id)
        old_oco_order = self._scheme_child_order(runtime, old_list_client_order_id)
        old_oco_projected = old_oco_order.filled_qty if old_oco_order is not None else _ZERO
        protective_side = (
            OrderSide.SELL if cmd.side is OrderSide.BUY else OrderSide.BUY
        )
        leg_client_order_ids = runtime.trading_state.oco_parent_legs.get(
            old_list_client_order_id, (),
        )

        try:
            oco_filled = await self._cancelled_oco_filled_qty(
                cmd, old_list_client_order_id,
            )
        except VenueError as exc:
            reason = str(exc.args[0]) if exc.args else str(exc)
            await self._append_protection_state_unknown(
                cmd, new_version, reason,
                old_list_client_order_id=old_list_client_order_id,
            )
            bracket.protection_status = BracketProtectionStatus.STATE_UNKNOWN
            bracket.unknown_since = self._clock()
            bracket.amend_backfill_since = None
            _log.warning(
                'bracket protective reconcile query failed; halting amend for '
                'reconcile rather than sizing a replacement from stale local '
                'fills: command_id=%s version=%d reason=%s',
                cmd.command_id,
                new_version,
                reason,
            )
            return

        reconciled = await self._backfill_terminal_order_fills(
            runtime, cmd.account_id, cmd.symbol, exit_command_id, cmd.trade_id,
            protective_side, old_list_client_order_id, leg_client_order_ids,
            old_oco_projected, oco_filled,
        )
        if not reconciled:
            if bracket.amend_backfill_since is None:
                bracket.amend_backfill_since = self._clock()

            elapsed = (self._clock() - bracket.amend_backfill_since).total_seconds()
            if elapsed < self._restore_deadline_seconds:
                bracket.protection_status = BracketProtectionStatus.CANCEL_CONFIRMED
                _log.warning(
                    'bracket protective amend held: protective fills unreconciled '
                    'after cancel; parked for the reconcile scan to retry: '
                    'command_id=%s version=%d',
                    cmd.command_id,
                    new_version,
                )
                return

            _log.warning(
                'bracket protective amend: fills still unreconciled at the '
                'restore deadline; placing the replacement from venue truth '
                'rather than flattening over a trade-query gap: command_id=%s '
                'version=%d',
                cmd.command_id,
                new_version,
            )

        bracket.amend_backfill_since = None

        if runtime.trading_state.orders.get(old_list_client_order_id) is not None:
            terminal_venue_order_id = (
                cancel_venue_order_id
                if cancel_venue_order_id is not None
                else (old_oco_order.venue_order_id if old_oco_order is not None else '')
            )
            canceled = OrderCanceled(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=old_list_client_order_id,
                venue_order_id=terminal_venue_order_id,
                reason='bracket protection amended',
            )
            await self._event_spine.append(canceled, self._epoch_id)
            runtime.trading_state.apply(canceled)

        remaining = entry_filled - (exit_projected - old_oco_projected + oco_filled)

        if remaining <= _ZERO:
            runtime.brackets.pop(cmd.command_id, None)
            _log.info(
                'bracket protective amend: position closed by a protective '
                'fill, no replacement placed: command_id=%s version=%d',
                cmd.command_id,
                new_version,
            )
            return

        filters = self._venue_adapter.cached_filters(cmd.symbol)
        lot_min = filters.lot_min if filters is not None else _ZERO
        min_notional = filters.min_notional if filters is not None else _ZERO

        if remaining < lot_min or remaining * tp_price < min_notional:
            runtime.brackets.pop(cmd.command_id, None)
            _log.info(
                'bracket protective amend: remaining below tradable minimums '
                'after reconcile, position treated as closed dust, no '
                'replacement placed: command_id=%s version=%d remaining=%s',
                cmd.command_id,
                new_version,
                remaining,
            )
            return

        replace_submitted = ProtectionReplaceSubmitted(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=new_version,
            new_list_client_order_id=new_list_client_order_id,
        )
        await self._event_spine.append(replace_submitted, self._epoch_id)
        bracket.protection_status = BracketProtectionStatus.REPLACE_SUBMITTED

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=exit_command_id,
            trade_id=cmd.trade_id,
            client_order_id=new_list_client_order_id,
            symbol=cmd.symbol,
            side=protective_side,
            order_type=OrderType.OCO,
            qty=remaining,
            quote_qty=None,
            price=tp_price,
            stop_price=sl_stop_price,
            stop_limit_price=sl_limit_price,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                protective_side,
                OrderType.OCO,
                remaining,
                price=tp_price,
                stop_price=sl_stop_price,
                stop_limit_price=sl_limit_price,
                client_order_id=new_list_client_order_id,
            )
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError, VenueError) as exc:
            reason = str(exc.args[0]) if exc.args else str(exc)

            try:
                order_list = await self._replacement_oco_is_live(
                    cmd, new_list_client_order_id,
                )
            except VenueError:
                await self._append_protection_state_unknown(
                    cmd, new_version, reason,
                    old_list_client_order_id=old_list_client_order_id,
                    new_list_client_order_id=new_list_client_order_id,
                )
                bracket.protection_status = BracketProtectionStatus.STATE_UNKNOWN
                bracket.unknown_since = self._clock()
                bracket.pending_replacement_client_order_id = new_list_client_order_id
                _log.warning(
                    'bracket protective replacement unconfirmable after venue '
                    'error; halting amend for reconcile: command_id=%s '
                    'version=%d reason=%s',
                    cmd.command_id,
                    new_version,
                    reason,
                )
                return

            if order_list is None:
                await self._remediate_naked_bracket(
                    runtime, bracket, new_version, reason,
                    remaining, (old_list_client_order_id, new_list_client_order_id),
                )

                return

            submitted = OrderSubmitted(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=new_list_client_order_id,
                venue_order_id=order_list.order_list_id,
                leg_client_order_ids=tuple(
                    leg.client_order_id for leg in order_list.legs
                ),
            )
            replacement_terminal = (
                order_list.list_order_status == _OCO_LIST_STATUS_ALL_DONE
            )
            immediate_fills: tuple[ImmediateFill, ...] = ()
        else:
            submitted = OrderSubmitted(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=new_list_client_order_id,
                venue_order_id=result.venue_order_id,
                leg_client_order_ids=result.leg_client_order_ids,
            )
            replacement_terminal = result.status in _TERMINAL_ORDER_STATUSES
            immediate_fills = result.immediate_fills

        runtime.command_to_order[exit_command_id] = new_list_client_order_id
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        bracket.amend_new_list_client_order_id = None
        bracket.amend_tp_price = None
        bracket.amend_sl_stop_price = None
        bracket.amend_sl_limit_price = None

        if replacement_terminal:
            await self._append_protection_state_unknown(
                cmd, new_version,
                'replacement OCO already terminal at placement',
                old_list_client_order_id=old_list_client_order_id,
                new_list_client_order_id=new_list_client_order_id,
            )
            bracket.protection_client_order_id = new_list_client_order_id
            bracket.pending_replacement_client_order_id = new_list_client_order_id
            bracket.protection_status = BracketProtectionStatus.STATE_UNKNOWN
            bracket.unknown_since = self._clock()
            _log.warning(
                'bracket protective replacement already terminal at placement; '
                'holding for reconcile rather than marking a filled or cancelled '
                'OCO active: command_id=%s version=%d',
                cmd.command_id,
                new_version,
            )
            return

        for fill in immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=self._clock(),
                client_order_id=new_list_client_order_id,
                venue_order_id=submitted.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=exit_command_id,
                symbol=cmd.symbol,
                side=protective_side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        active = ProtectionActive(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=new_version,
            new_list_client_order_id=new_list_client_order_id,
        )
        await self._event_spine.append(active, self._epoch_id)
        bracket.protection_client_order_id = new_list_client_order_id
        bracket.current_tp_price = tp_price
        bracket.current_sl_stop_price = sl_stop_price
        bracket.current_sl_limit_price = sl_limit_price
        bracket.protection_status = BracketProtectionStatus.ACTIVE

        _log.info(
            'bracket protection amended: command_id=%s version=%d qty=%s '
            'tp=%s sl=%s new_list=%s',
            cmd.command_id,
            new_version,
            remaining,
            tp_price,
            sl_stop_price,
            new_list_client_order_id,
        )

    async def resolve_held_protection_amends(self, account_id: str) -> None:
        '''Retry each protective-OCO amend held for fill reconciliation.

        A bracket amend parks in `CANCEL_CONFIRMED` with `amend_backfill_since`
        set when the cancelled OCO's protective fill could not be reconciled to
        venue truth. Each reconcile scan re-drives it — re-query, backfill, then
        terminalize and replace once reconciled, or place from venue truth once
        the restore deadline elapses. Never routed through the naked-remediation
        watchdog, so a transient trade-query gap cannot flatten the position.

        Args:
            account_id (str): Account whose held protective amends to retry.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            return

        for bracket in list(runtime.brackets.values()):
            if bracket.amend_backfill_since is None:
                continue

            await self._drive_bracket_protection_amend(runtime, bracket, None)

    def _resolve_bracket_amend(
        self,
        bracket: _LiveBracket,
        params: BracketModify,
    ) -> tuple[Decimal, Decimal, Decimal | None] | None:
        '''Merge a partial bracket amend into a full, validated leg snapshot.

        A leg the amend sets is resolved — an absolute price used as-is, a
        basis-point offset resolved side-aware from the entry average fill and
        snapped to the venue tick; a leg the amend leaves unset keeps the
        bracket's current value. The merged legs are validated on the correct
        side of the entry, mirroring initial placement.

        Args:
            bracket (_LiveBracket): The bracket holding current legs and the
                entry reference.
            params (BracketModify): Partial amend of the protective legs.

        Returns:
            tuple[Decimal, Decimal, Decimal | None] | None: The resolved
                take-profit, stop-loss trigger, and optional stop-limit
                prices, or None when the merged legs are invalid.
        '''

        cmd = bracket.command
        assert bracket.avg_entry_price is not None
        avg_entry_price = bracket.avg_entry_price
        profit_direction = _ONE if cmd.side is OrderSide.BUY else -_ONE

        tp_price: Decimal | None
        sl_stop_price: Decimal | None
        sl_limit_price: Decimal | None

        if params.take_profit_price is not None:
            tp_price = self._snap_price(cmd.symbol, params.take_profit_price)
        elif params.take_profit_offset_bps is not None:
            tp_price = self._snap_price(
                cmd.symbol,
                avg_entry_price
                * (_ONE + profit_direction * params.take_profit_offset_bps / _BPS_MULTIPLIER),
            )
        else:
            tp_price = bracket.current_tp_price

        if params.stop_loss_price is not None:
            sl_stop_price = self._snap_price(cmd.symbol, params.stop_loss_price)
        elif params.stop_loss_offset_bps is not None:
            sl_stop_price = self._snap_price(
                cmd.symbol,
                avg_entry_price
                * (_ONE - profit_direction * params.stop_loss_offset_bps / _BPS_MULTIPLIER),
            )
        else:
            sl_stop_price = bracket.current_sl_stop_price

        if params.stop_loss_limit_price is not None:
            sl_limit_price = self._snap_price(cmd.symbol, params.stop_loss_limit_price)
        else:
            sl_limit_price = bracket.current_sl_limit_price

        if tp_price is None or sl_stop_price is None:
            return None

        if not self._bracket_legs_valid_for_entry(
            cmd, tp_price, sl_stop_price, avg_entry_price,
        ):
            return None

        return tp_price, sl_stop_price, sl_limit_price

    async def _cancelled_oco_filled_qty(
        self,
        cmd: TradeCommand,
        list_client_order_id: str,
    ) -> Decimal:
        '''Return the authoritative filled quantity of a cancelled protective OCO.

        The venue's OCO list query carries only leg identities, not a filled
        quantity, so each leg is queried and its filled quantity summed — a
        one-sided protective OCO fills at most one leg. A query failure leaves
        the cancelled OCO's fill unresolved and raises `VenueError`: the caller
        must halt the amend for reconciliation rather than size a replacement
        from a stale local projection that could under-count a missed fill and
        over-size the replacement.

        Args:
            cmd (TradeCommand): Bracket command carrying account and symbol.
            list_client_order_id (str): Cancelled OCO's list client order id.

        Returns:
            Decimal: The cancelled OCO's authoritative filled quantity.

        Raises:
            VenueError: When the venue query cannot be completed.
        '''

        order_list = await self._venue_adapter.query_order_list(
            cmd.account_id, list_client_order_id=list_client_order_id,
        )

        filled = _ZERO
        for leg in order_list.legs:
            leg_order = await self._venue_adapter.query_order(
                cmd.account_id, cmd.symbol, client_order_id=leg.client_order_id,
            )
            filled += leg_order.filled_qty

        return filled

    async def _replacement_oco_is_live(
        self,
        cmd: TradeCommand,
        list_client_order_id: str,
    ) -> VenueOrderList | None:
        '''Return an ambiguously-submitted replacement OCO if it is resting.

        After an ambiguous submit (timeout, duplicate client id, or a generic
        venue error once the old OCO is already cancelled) the venue is queried
        for the replacement list rather than blindly failing: a list present
        and not rejected is a confirmed idempotent success and is returned so
        its venue identities can be tracked; a list the venue confirms REJECT
        returns None. A query that cannot be completed raises `VenueError` so
        the caller halts for reconciliation (unknown) rather than treating an
        unconfirmable replacement as rejected.

        Args:
            cmd (TradeCommand): Bracket command carrying the account.
            list_client_order_id (str): Replacement OCO's list client order id.

        Returns:
            VenueOrderList | None: The resting replacement list, or None when
                the venue confirms the list is rejected.

        Raises:
            VenueError: When the venue query cannot be completed.
        '''

        order_list = await self._venue_adapter.query_order_list(
            cmd.account_id, list_client_order_id=list_client_order_id,
        )

        if order_list.list_order_status == _OCO_LIST_STATUS_REJECT:
            return None

        return order_list

    async def _append_protection_state_unknown(
        self,
        cmd: TradeCommand,
        protection_version: int,
        reason: str,
        old_list_client_order_id: str | None = None,
        new_list_client_order_id: str | None = None,
    ) -> None:
        '''Persist a `ProtectionStateUnknown` for an ambiguous amend outcome.

        The candidate list client order ids are carried on the event so the
        watchdog can rebuild the bracket and re-query them after a restart,
        where they would otherwise survive only in memory.
        '''

        event = ProtectionStateUnknown(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=protection_version,
            reason=reason,
            old_list_client_order_id=old_list_client_order_id,
            new_list_client_order_id=new_list_client_order_id,
        )
        await self._event_spine.append(event, self._epoch_id)

    async def _append_protection_failed(
        self,
        cmd: TradeCommand,
        protection_version: int,
        reason: str,
        oco_candidates: tuple[str, ...] = (),
    ) -> None:
        '''Persist a `ProtectionFailed` marking no live protective OCO.

        The candidate OCO list ids are carried on the marker so boot flatten
        recovery re-checks each for a live leg before market-flattening, exactly
        as the live flatten did.
        '''

        event = ProtectionFailed(
            account_id=cmd.account_id,
            timestamp=self._clock(),
            command_id=cmd.command_id,
            protection_version=protection_version,
            reason=reason,
            oco_list_client_order_ids=oco_candidates,
        )
        await self._event_spine.append(event, self._epoch_id)

    @staticmethod
    def _bracket_oco_candidates(bracket: _LiveBracket) -> tuple[str, ...]:
        '''Return the OCO list ids a naked bracket's flatten must confirm dead.'''

        return tuple(
            candidate
            for candidate in (
                bracket.protection_client_order_id,
                bracket.pending_replacement_client_order_id,
            )
            if candidate is not None
        )

    async def _process_scheme_modify(
        self,
        runtime: _AccountRuntime,
        scheme: _LiveScheme,
        modify: TradeModify,
    ) -> None:
        '''Amend a running scheme's remaining schedule in place.

        TWAP / Time DCA / Scheduled VWAP fire MARKET slices at an interval and
        rest no orders, so an amend needs no venue cancel-replace: the
        remaining unfilled quantity is re-planned across the remaining slices
        and the cadence rescheduled. A new slice count (TWAP / Time DCA)
        re-plans the not-yet-fired slices for the remaining quantity; a new
        interval reschedules the next slice. Any successful amend resets the
        cadence clock: the next slice fires a full (new) interval from now,
        not from the previous slice. A new total at or below the fired cursor
        is rejected (a scheme is stopped with a TradeAbort, not by shrinking
        it below what has already fired). A successful amend clears
        a freeze, resuming a scheme frozen by a slice failure — but a scheme
        frozen by a protection remediation is not resumable by an amend and
        the modify is rejected. The amend is applied in memory only — a
        restart replays the original schedule (TD-135) — and a Scheduled
        VWAP weight-curve amend is not yet supported.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            scheme (_LiveScheme): The running scheme to amend.
            modify (TradeModify): Amend instruction with a scheme ModifyParams.
        '''

        cmd = scheme.command
        params = modify.modify_params
        assert cmd.qty is not None
        assert isinstance(params, (TwapModify, TimeDcaModify, ScheduledVwapModify))

        if scheme.protection_frozen:
            _log.warning(
                'modify rejected: scheme is frozen by a protection remediation '
                'and cannot be resumed by an amend: command_id=%s',
                cmd.command_id,
            )
            return

        if scheme.pending_terminal is not None:
            _log.warning(
                'modify rejected: scheme has a terminal outcome pending and '
                'cannot be amended while cancellation settles: command_id=%s',
                cmd.command_id,
            )
            return

        if isinstance(params, ScheduledVwapModify) and params.volume_weights is not None:
            _log.warning(
                'modify rejected: Scheduled VWAP weight amend not yet supported: '
                'command_id=%s',
                cmd.command_id,
            )
            return

        current_total = scheme.slices_total
        current_interval = scheme.interval_seconds
        new_total, new_interval = self._resolve_scheme_amend(
            params, current_total, current_interval,
        )

        filled_qty, _ = self._command_fill_totals(runtime, cmd.command_id)
        remaining_qty = cmd.qty - filled_qty
        remaining_slices = new_total - scheme.cursor

        if remaining_qty <= _ZERO:
            _log.info(
                'scheme amend no-op (already filled): command_id=%s', cmd.command_id,
            )
            return

        if remaining_slices <= 0:
            _log.warning(
                'modify rejected: new slice total %d is not beyond the fired '
                'cursor %d; abort to stop a scheme: command_id=%s',
                new_total,
                scheme.cursor,
                cmd.command_id,
            )
            return

        if new_total != current_total:
            filters = self._venue_adapter.cached_filters(cmd.symbol)
            lot_step = filters.lot_step if filters is not None else None
            try:
                remaining_qtys = plan_even_slices(remaining_qty, remaining_slices, lot_step)
            except ValueError as exc:
                _log.warning(
                    'scheme amend replan failed; leaving schedule unchanged: '
                    'command_id=%s reason=%s',
                    cmd.command_id,
                    exc,
                )
                return

            scheme.slice_qtys = scheme.slice_qtys[:scheme.cursor] + remaining_qtys
            scheme.slices_total = new_total

        scheme.interval_seconds = new_interval
        scheme.frozen = False
        scheme.next_run_at = self._clock() + timedelta(seconds=new_interval)
        await self._append_scheme_progress(runtime, scheme, SchemeState.RUNNING)

    def _resolve_scheme_amend(
        self,
        params: TwapModify | TimeDcaModify | ScheduledVwapModify,
        current_total: int,
        current_interval: int,
    ) -> tuple[int, int]:
        '''Resolve a scheme amend's absolute new slice total and interval.

        An unset field keeps the running scheme's current live value, so
        sequential partial amends compose rather than reverting to the
        original command. Scheduled VWAP carries no slice-count field (its
        count is its weight-curve length, which this slice does not amend),
        so its total is unchanged.
        '''

        interval = (
            params.interval_seconds
            if params.interval_seconds is not None
            else current_interval
        )

        if isinstance(params, TwapModify):
            total = params.num_slices if params.num_slices is not None else current_total
            return total, interval

        if isinstance(params, TimeDcaModify):
            total = (
                params.num_iterations
                if params.num_iterations is not None
                else current_total
            )
            return total, interval

        return current_total, interval

    def _resolve_amend(
        self,
        cmd: TradeCommand,
        params: SingleShotModify | IcebergModify,
    ) -> tuple[Decimal | None, Decimal | None]:
        '''Resolve the replacement's absolute price and display quantity.

        Absolute amend values override the original; unset fields keep the
        command's original value. Returns (price, display_qty), with
        display_qty None for a plain limit replacement.
        '''

        if isinstance(params, IcebergModify):
            assert isinstance(cmd.execution_params, IcebergParams)
            price = (
                params.limit_price
                if params.limit_price is not None
                else cmd.execution_params.limit_price
            )
            display = (
                params.display_qty
                if params.display_qty is not None
                else cmd.execution_params.display_qty
            )
            return price, display

        assert isinstance(cmd.execution_params, SingleShotParams)
        resolved_price = (
            params.price if params.price is not None else cmd.execution_params.price
        )
        return resolved_price, None

    def _amended_order_params(
        self,
        cmd: TradeCommand,
        price: Decimal,
        display_qty: Decimal | None,
    ) -> ExecutionParams:
        '''Return the command's execution params with the amend's values applied.

        Adopting the resolved price and display after a successful amend keeps
        `cmd.execution_params` the current effective order, so a later amend
        that leaves a field unset resolves it from the latest values rather
        than reverting to the original command.
        '''

        if isinstance(cmd.execution_params, IcebergParams):
            assert display_qty is not None
            return replace(
                cmd.execution_params, limit_price=price, display_qty=display_qty,
            )

        assert isinstance(cmd.execution_params, SingleShotParams)
        return replace(cmd.execution_params, price=price)

    async def _cancel_and_query(
        self,
        cmd: TradeCommand,
        client_order_id: str,
    ) -> VenueOrder | None:
        '''Cancel the resting order and return its authoritative venue state.

        Fail-closed: a cancel that errors (the order may still be live) or a
        query that errors (the order state cannot be confirmed) returns None,
        and the caller must abort the amend without cancelling locally or
        placing a replacement — otherwise a still-live original plus a
        replacement could double the exposure. A `NotFoundError` on cancel
        means the order is already gone, resolved by the query. The cancel
        response carries no filled quantity, so the venue is queried for the
        authoritative filled and terminal status the replacement is sized
        against.
        '''

        try:
            await self._venue_adapter.cancel_order(
                cmd.account_id, cmd.symbol, client_order_id=client_order_id,
            )
        except NotFoundError:
            pass
        except VenueError as exc:
            _log.warning(
                'amend aborted: cancel failed, order may still be live: '
                'command_id=%s reason=%s',
                cmd.command_id,
                exc.args[0] if exc.args else exc,
            )
            return None

        try:
            return await self._venue_adapter.query_order(
                cmd.account_id, cmd.symbol, client_order_id=client_order_id,
            )
        except (NotFoundError, VenueError) as exc:
            _log.warning(
                'amend aborted: order state could not be confirmed: '
                'command_id=%s reason=%s',
                cmd.command_id,
                exc.args[0] if exc.args else exc,
            )
            return None

    async def _place_amend_replacement(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        new_client_order_id: str,
        price: Decimal,
        display_qty: Decimal | None,
        remainder: Decimal,
    ) -> None:
        '''Place the amend's replacement LIMIT order for the remainder.

        Persist-before-send: `OrderSubmitIntent` then the venue call, with the
        same timeout / duplicate rescue as the initial submit. On success the
        command's live order becomes the replacement; the outcome is emitted
        from the command-total fills so the superseded order's fills carry
        forward. A submit failure leaves the durable `OrderAmendInitiated`
        for boot repair and reports the fills so far.
        '''

        iceberg_qty = display_qty if display_qty is not None and display_qty < remainder else None
        now = self._clock()

        intent = OrderSubmitIntent(
            account_id=cmd.account_id,
            timestamp=now,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            client_order_id=new_client_order_id,
            symbol=cmd.symbol,
            side=cmd.side,
            order_type=OrderType.LIMIT,
            qty=remainder,
            quote_qty=None,
            price=price,
            stop_price=None,
            stop_limit_price=None,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)
        runtime.command_to_order[cmd.command_id] = new_client_order_id

        try:
            result = await self._venue_adapter.submit_order(
                cmd.account_id,
                cmd.symbol,
                cmd.side,
                OrderType.LIMIT,
                remainder,
                price=price,
                client_order_id=new_client_order_id,
                iceberg_qty=iceberg_qty,
            )
            post_venue_ts = self._clock()
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError) as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, cmd, new_client_order_id, exc,
            )
            if rescued is None:
                await self._append_submit_failed(
                    runtime, cmd, new_client_order_id, str(exc.args[0]),
                )
                await self._emit_amend_outcome(runtime, cmd)
                return
            result = rescued
            post_venue_ts = self._clock()
        except (VenueError, ValueError) as exc:
            await self._append_submit_failed(
                runtime, cmd, new_client_order_id, str(exc.args[0]),
            )
            await self._emit_amend_outcome(runtime, cmd)
            return

        submitted = OrderSubmitted(
            account_id=cmd.account_id,
            timestamp=post_venue_ts,
            client_order_id=new_client_order_id,
            venue_order_id=result.venue_order_id,
        )
        await self._event_spine.append(submitted, self._epoch_id)
        runtime.trading_state.apply(submitted)

        self._commands[cmd.command_id] = replace(
            cmd, execution_params=self._amended_order_params(cmd, price, display_qty),
        )

        for fill in result.immediate_fills:
            fill_event = FillReceived(
                account_id=cmd.account_id,
                timestamp=post_venue_ts,
                client_order_id=new_client_order_id,
                venue_order_id=result.venue_order_id,
                venue_trade_id=fill.venue_trade_id,
                trade_id=cmd.trade_id,
                command_id=cmd.command_id,
                symbol=cmd.symbol,
                side=cmd.side,
                qty=fill.qty,
                price=fill.price,
                fee=fill.fee,
                fee_asset=fill.fee_asset,
                is_maker=fill.is_maker,
            )
            seq = await self._event_spine.append(fill_event, self._epoch_id)
            if seq is not None:
                self._project(runtime, fill_event)

        await self._emit_amend_outcome(runtime, cmd)

    async def _emit_amend_outcome(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> None:
        '''Emit an outcome for an amended command from its aggregate fills.

        Status is derived from the command-total filled across the superseded
        and replacement orders: FILLED once the target is reached, PARTIAL
        while some quantity has filled, otherwise PENDING for the resting
        replacement.
        '''

        assert cmd.qty is not None
        filled_qty, cumulative_notional = self._command_fill_totals(
            runtime, cmd.command_id,
        )
        avg_fill_price = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        if filled_qty >= cmd.qty:
            status = TradeStatus.FILLED
        elif filled_qty > _ZERO:
            status = TradeStatus.PARTIAL
        else:
            status = TradeStatus.PENDING

        await self._build_outcome(
            runtime,
            cmd,
            status,
            filled_qty=min(filled_qty, cmd.qty),
            avg_fill_price=avg_fill_price,
            reason=None,
            cumulative_notional=cumulative_notional,
        )

    async def _emit_amend_terminal(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
    ) -> None:
        '''Terminalize an amended command that cancelled with only dust left.

        The resting order was cancelled and the unfilled remainder is sub-lot
        dust that cannot be re-placed, so the command completes FILLED on the
        fills so far — the same economically-negligible shortfall a scheme
        reports FILLED — rather than resting non-terminal forever.
        '''

        assert cmd.qty is not None
        filled_qty, cumulative_notional = self._command_fill_totals(
            runtime, cmd.command_id,
        )
        avg_fill_price = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        await self._build_outcome(
            runtime,
            cmd,
            TradeStatus.FILLED,
            filled_qty=min(filled_qty, cmd.qty),
            avg_fill_price=avg_fill_price,
            reason=None,
            cumulative_notional=cumulative_notional,
        )

    async def _build_abort_outcome(
        self,
        runtime: _AccountRuntime,
        order: Order,
        trade_id: str,
        *,
        filled_qty: Decimal,
        avg_fill_price: Decimal | None,
        reason: str | None,
    ) -> TradeOutcome:
        '''
        Construct CANCELED TradeOutcome from Order data.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            order (Order): Order being aborted.
            trade_id (str): Trade identifier from _command_trade_ids.
            filled_qty (Decimal): Cumulative filled quantity.
            avg_fill_price (Decimal | None): VWAP of fills.
            reason (str | None): Abort reason.

        Returns:
            TradeOutcome: CANCELED outcome.
        '''

        ts = self._clock()

        outcome = TradeOutcome(
            command_id=order.command_id,
            trade_id=trade_id,
            account_id=order.account_id,
            status=TradeStatus.CANCELED,
            target_qty=order.qty,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            slices_completed=1,
            slices_total=1,
            reason=reason,
            created_at=ts,
            cumulative_notional=order.cumulative_notional,
        )

        self._terminal_commands.add(order.command_id)
        self._commands.pop(order.command_id, None)
        self._aborted_commands.pop(order.command_id, None)

        if filled_qty > _ZERO and self._closes_position(
            runtime, order.account_id, trade_id, order.side
        ):
            closed = TradeClosed(
                account_id=order.account_id,
                timestamp=ts,
                trade_id=trade_id,
                command_id=order.command_id,
            )
            await self._event_spine.append(closed, self._epoch_id)
            self._project(runtime, closed)

        produced = TradeOutcomeProduced(
            account_id=order.account_id,
            timestamp=ts,
            command_id=order.command_id,
            trade_id=trade_id,
            status=TradeStatus.CANCELED,
            reason=reason,
            filled_qty=outcome.filled_qty,
            cumulative_notional=outcome.cumulative_notional,
            target_qty=outcome.target_qty,
        )
        await self._event_spine.append(produced, self._epoch_id)
        runtime.trading_state.apply(produced)

        await self._dispatch_outcome_with_retry(outcome, source='ws_emit')

        return outcome

    async def _emit_ws_outcome(
        self,
        runtime: _AccountRuntime,
        event: Event,
    ) -> None:
        '''Emit a `TradeOutcome` for a WS-driven event after `trading_state.apply` runs.

        The `_process_command` path emits outcomes for immediate fills
        (MARKET orders) and the initial PENDING ACK (LIMIT orders). It
        does NOT emit outcomes for subsequent venue WS fills, partial
        cancels, terminal cancels/rejects/expires that arrive via the
        WS user stream. Without this method, those events update only
        `TradingState.orders` / `positions` projections; the launcher's
        `_route_translated` → `OutcomeTranslator.translate` → Nexus
        queue → `OutcomeLoop` → `process_outcome` chain never fires
        for them, so capital stays parked in `working_order_notional`,
        Nexus's `state.positions[trade_id]` keeps the size=0 placeholder,
        and any operator LIMIT strategy silently loses every fill.

        Skips the emission when:
        - The event is not a fill / order-terminal type
        - The command_id is already in `_terminal_commands` (the
          `_process_command` path already emitted a terminal — typical
          for MARKET orders that fill immediately, then the WS echo
          arrives later)
        - The command_id belongs to a live scheme in `runtime.schemes`:
          a multi-slice parent emits exactly one aggregated terminal
          outcome from the scheme path, so a per-child WS echo must not
          synthesize a single-shot outcome for the whole command
        - The originating command or order projection cannot be found
          (defensive — should not happen during normal flow)
        '''

        if not isinstance(event, (FillReceived, OrderCanceled, OrderExpired, OrderRejected)):
            return

        client_order_id = event.client_order_id
        order = (
            runtime.trading_state.orders.get(client_order_id)
            or runtime.trading_state.closed_orders.get(client_order_id)
        )
        if order is None:
            return

        command_id = order.command_id
        if command_id in self._terminal_commands:
            return

        if command_id in runtime.schemes:
            return

        cmd = self._commands.get(command_id)
        if cmd is None:
            return

        if runtime.command_to_order.get(command_id) != client_order_id:
            return

        filled_qty, cumulative_notional = self._command_fill_totals(runtime, command_id)

        avg_fill_price: Decimal | None = (
            cumulative_notional / filled_qty if filled_qty > _ZERO else None
        )

        emitted_filled_qty = filled_qty
        emitted_cumulative_notional = cumulative_notional
        if not cmd.is_quote_native:
            assert cmd.qty is not None
            if emitted_filled_qty > cmd.qty:
                _log.warning(
                    'WS-driven filled_qty exceeds command target_qty; '
                    'clamping to target. Likely cause: duplicate / out-of-order '
                    'venue fills or venue rounding past the order qty',
                    extra={
                        'command_id': command_id,
                        'order_filled_qty': str(order.filled_qty),
                        'target_qty': str(cmd.qty),
                    },
                )
                emitted_filled_qty = cmd.qty

        if isinstance(event, FillReceived):
            fully_filled = (
                emitted_filled_qty >= cmd.qty
                if not cmd.is_quote_native and cmd.qty is not None
                else order.status == OrderStatus.FILLED
            )
            status = TradeStatus.FILLED if fully_filled else TradeStatus.PARTIAL
            reason: str | None = None

        elif isinstance(event, OrderCanceled):
            status = TradeStatus.CANCELED
            reason = event.reason

        elif isinstance(event, OrderExpired):
            status = TradeStatus.EXPIRED
            reason = None

        elif isinstance(event, OrderRejected):
            status = TradeStatus.REJECTED
            reason = event.reason

        else:
            msg = (
                f'_emit_ws_outcome reached unreachable branch: '
                f'event_type={type(event).__name__}; the outer isinstance '
                f'filter and this if/elif chain are out of sync'
            )
            raise RuntimeError(msg)

        await self._build_outcome(
            runtime,
            cmd,
            status,
            filled_qty=emitted_filled_qty,
            avg_fill_price=avg_fill_price,
            reason=reason,
            cumulative_notional=emitted_cumulative_notional,
        )

    async def _build_outcome(
        self,
        runtime: _AccountRuntime,
        cmd: TradeCommand,
        status: TradeStatus,
        *,
        filled_qty: Decimal,
        avg_fill_price: Decimal | None,
        reason: str | None,
        cumulative_notional: Decimal = _ZERO,
    ) -> TradeOutcome:
        '''
        Construct TradeOutcome, emit spine events, and invoke callback.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            cmd (TradeCommand): Originating command.
            status (TradeStatus): Outcome status.
            filled_qty (Decimal): Cumulative filled quantity.
            avg_fill_price (Decimal | None): VWAP of fills.
            reason (str | None): Descriptive reason for status.
            cumulative_notional (Decimal): Venue-side cumulative notional
                (sum of qty * price across fills). Carried verbatim from
                `Order.cumulative_notional` for FINAL-MAJOR-07 so the
                OutcomeTranslator does not have to reverse-derive it.
                Default `_ZERO` for synthetic / no-fill outcomes.

        Returns:
            TradeOutcome: The constructed outcome.
        '''

        ts = self._clock()

        outcome = TradeOutcome(
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            account_id=cmd.account_id,
            status=status,
            target_qty=cmd.qty,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            slices_completed=1,
            slices_total=1,
            reason=reason,
            created_at=ts,
            cumulative_notional=cumulative_notional,
        )

        if outcome.is_terminal:
            self._terminal_commands.add(cmd.command_id)
            self._commands.pop(cmd.command_id, None)
            self._aborted_commands.pop(cmd.command_id, None)

            if filled_qty > _ZERO and self._closes_position(
                runtime, cmd.account_id, cmd.trade_id, cmd.side
            ):
                closed = TradeClosed(
                    account_id=cmd.account_id,
                    timestamp=ts,
                    trade_id=cmd.trade_id,
                    command_id=cmd.command_id,
                )
                await self._event_spine.append(closed, self._epoch_id)
                self._project(runtime, closed)

        produced = TradeOutcomeProduced(
            account_id=cmd.account_id,
            timestamp=ts,
            command_id=cmd.command_id,
            trade_id=cmd.trade_id,
            status=status,
            reason=reason,
            filled_qty=outcome.filled_qty,
            cumulative_notional=outcome.cumulative_notional,
            target_qty=outcome.target_qty,
        )
        await self._event_spine.append(produced, self._epoch_id)
        runtime.trading_state.apply(produced)

        await self._dispatch_outcome_with_retry(outcome, source='process_command')

        return outcome

    def _closes_position(
        self,
        runtime: _AccountRuntime,
        account_id: str,
        trade_id: str,
        side: OrderSide,
    ) -> bool:
        '''Whether a terminal fill on `side` closes the trade's position.

        `TradeClosed` must mean "position lifecycle closed", not merely
        "order terminal". Emitting it for an entry fill is a durability
        bug: on event replay the position is created from the entry
        `FillReceived` and then immediately deleted by the entry's own
        `TradeClosed`, so a restart rebuilds zero open positions and boot
        reconciliation evicts the live position. A position closes only
        on a reducing fill — one whose side is opposite the open
        position's side. An entry fill (same side as the position it
        opens) does not close it; a `trade_id` with no live position
        (already removed by an exact-zero reduction) needs no further
        `TradeClosed`.

        Quantity-aware (TD-096): the fill has already been applied to
        `trading_state`, so `pos.qty` is the post-fill remaining. A
        reducing fill closes the position only when that remainder is
        at or below dust — strictly below the symbol's `LOT_SIZE`
        `lot_step`, the largest quantity the venue cannot trade — so a
        partial reducing fill that leaves a tradeable remainder does NOT
        emit `TradeClosed` (which would close the position projection
        early on replay). A full-close exit that lot-rounds to a sub-step
        residue is still dust and closes. When the symbol's filters are
        not cached, fall back to closing on any reducing fill (the prior
        side-only behaviour), safe for the single-position full-exit
        model.
        '''

        positions = runtime.trading_state.snapshot_positions()
        pos = positions.get((trade_id, account_id))

        if pos is None:
            return False

        if side == pos.side:
            return False

        filters = self._venue_adapter.cached_filters(pos.symbol)

        if filters is None:
            return True

        return pos.qty < filters.lot_step
