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
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from praxis.core.account_ledger import AccountLedger
from praxis.core.domain.chart_of_accounts import Account
from praxis.core.domain.enums import (
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
    SchemeInitialized,
    SchemeStateChanged,
    CommandAccepted,
    Event,
    FillReceived,
    FundTransaction,
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
from praxis.core.domain.order import Order
from praxis.core.domain.position import Position
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.trade_pnl import TradePnL
from praxis.core.bracket_exit_command_id import bracket_exit_command_id
from praxis.core.domain.bracket_params import BracketParams
from praxis.core.domain.execution_params import ExecutionParams
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.scheduled_vwap_params import ScheduledVwapParams
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.time_dca_params import TimeDcaParams
from praxis.core.domain.twap_params import TwapParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.estimate_slippage import (
    SlippageEstimate,
    estimate_slippage,
    estimate_slippage_for_quote,
)
from praxis.core.generate_client_order_id import (
    generate_client_order_id,
    validate_command_id_for_client_order_id,
)
from praxis.core.plan_even_slices import plan_even_slices
from praxis.core.plan_weighted_slices import plan_weighted_slices
from praxis.core.trading_state import TradingState
from praxis.core.validate_trade_abort import validate_trade_abort
from praxis.core.validate_trade_command import validate_trade_command
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    DuplicateClientOrderIdError,
    NotFoundError,
    OrderSubmitTimeoutError,
    SubmitResult,
    VenueAdapter,
    VenueError,
    VenueOrderList,
)

__all__ = ['AccountNotRegisteredError', 'CommandQueueFullError', 'ExecutionManager']

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
    state: SchemeState = SchemeState.RUNNING


@dataclass
class _LiveBracket:
    '''In-memory state for a bracket awaiting or holding its protection.

    A bracket submits a MARKET entry, then a protective OCO once the entry
    fills. When the entry fills asynchronously (no immediate fill) the
    account coroutine places the protection from the WebSocket fill via
    `_on_bracket_event`; `protection_placed` guards against a double
    placement across the immediate and asynchronous paths.
    '''

    command: TradeCommand
    entry_client_order_id: str
    protection_placed: bool = False


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
        priority_queue (asyncio.Queue[TradeAbort]): Unbounded queue for aborts.
        ws_event_queue (asyncio.Queue[Event]): Unbounded queue for WS events.
        trading_state (TradingState): Per-account state projection.
        account_ledger (AccountLedger): Per-account double-entry projection.
    '''

    def __init__(
        self,
        account_id: str,
        command_queue: asyncio.Queue[TradeCommand],
        priority_queue: asyncio.Queue[TradeAbort],
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
        self.queue_reservations = 0
        self.reconciling = False
        self.poisoned = False


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
    ) -> None:
        '''Store dependencies and initialize empty account registry.'''

        self._event_spine = event_spine
        self._epoch_id = epoch_id
        self._venue_adapter = venue_adapter
        self._max_slippage_bps = max_slippage_bps
        self._on_trade_outcome = on_trade_outcome
        self._clock = clock
        self._accounts: dict[str, _AccountRuntime] = {}
        self._accepted_commands: dict[str, str] = {}
        self._terminal_commands: set[str] = set()
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
        self._resume_brackets(runtime, events)

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
        the OCO rescue. A REJECTED protective OCO (venue rejection or a wrong-
        side-of-fill skip) is a definitive failure and is not retried on boot
        (TD-130); its filled entry stays unprotected pending operator repair.
        A malformed init that cannot rebuild valid params is skipped.
        '''

        inits: dict[str, BracketInitialized] = {}
        for _seq, event in events:
            if isinstance(event, BracketInitialized):
                inits[event.command_id] = event

        for command_id, init in inits.items():
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

        for _seq, event in events:
            if isinstance(event, SchemeInitialized):
                inits.setdefault(event.command_id, event)
            elif isinstance(event, SchemeStateChanged):
                latest_state[event.command_id] = event
            elif isinstance(event, SliceFailed):
                frozen_ids.add(event.command_id)
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
        `FillReceived` and `TradeClosed` book into both; every other event
        advances the trading state alone. The ledger is a secondary
        projection, so a projection failure is logged and never propagated
        into the trading path.
        '''

        if isinstance(event, RegisterAccount | FundTransaction):
            self._project_to_ledger(runtime, event)

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

    def _scheme_fill_totals(
        self,
        runtime: _AccountRuntime,
        command_id: str,
    ) -> tuple[Decimal, Decimal]:
        '''Sum filled qty and notional across a scheme's child orders.

        Reads the rebuilt order projections (active and closed) for every
        child whose `command_id` matches the scheme parent, so the boot
        terminalization reports the fills that actually settled rather than
        an in-memory aggregate that a crash discarded.
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
        filled_qty, cumulative_notional = self._scheme_fill_totals(runtime, command_id)
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
                    abort = runtime.priority_queue.get_nowait()
                    _log.info(
                        'abort received: command_id=%s account_id=%s',
                        abort.command_id,
                        runtime.account_id,
                    )
                    try:
                        await self._process_abort(runtime, abort)
                    except asyncio.CancelledError:
                        raise
                    except Exception:  # noqa: BLE001
                        _log.exception(
                            'unhandled exception while processing abort: '
                            'command_id=%s account_id=%s',
                            abort.command_id,
                            runtime.account_id,
                        )

                if runtime.reconciling or runtime.poisoned:
                    await asyncio.sleep(_QUEUE_POLL_INTERVAL)
                    continue

                await self._advance_due_schemes(runtime)
                await self._place_pending_bracket_protection(runtime)

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
                f"execution mode {cmd.execution_mode.value} is not yet supported"
            )
            _log.warning(
                'unsupported execution mode: command_id=%s mode=%s',
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
        '''Place protection for a settled bracket entry and report its outcome.

        Runs on the command path when the entry filled immediately (no
        WebSocket round trip): places the protective OCO for the filled
        quantity and reports the entry outcome. A terminal entry with no
        fill leaves nothing to protect and reports the venue's terminal
        state.

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
        await self._place_bracket_protection(
            runtime, bracket, filled_qty, avg_entry_price,
        )

        status = (
            TradeStatus.FILLED if filled_qty >= cmd.qty else TradeStatus.PARTIAL
        )

        return await self._build_outcome(
            runtime,
            cmd,
            status,
            filled_qty=filled_qty,
            avg_fill_price=avg_entry_price,
            reason=None,
            cumulative_notional=cumulative_notional,
        )

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
            await self._place_bracket_protection(
                runtime, bracket, entry_order.filled_qty, avg_entry_price,
            )
            await self._recover_bracket_entry_outcome(runtime, bracket, entry_order)

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
        leaves the entry position unprotected (TD-130), logged for repair
        rather than unwinding the filled entry.

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
                'skipping protection (position unprotected): command_id=%s side=%s '
                'avg_entry=%s tp=%s sl=%s',
                cmd.command_id,
                cmd.side.value,
                avg_entry_price,
                tp_price,
                sl_stop_price,
            )
            await self._append_submit_failed(
                runtime,
                exit_cmd,
                client_order_id,
                'bracket protective legs on the wrong side of the entry fill',
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
                    'bracket protective OCO failed; entry position unprotected: '
                    'command_id=%s exit_command_id=%s',
                    cmd.command_id,
                    exit_command_id,
                )
                await self._append_submit_failed(
                    runtime, exit_cmd, client_order_id, str(exc.args[0]),
                )

                return

            result = rescued
        except VenueError as exc:
            _log.exception(
                'bracket protective OCO failed; entry position unprotected: '
                'command_id=%s exit_command_id=%s reason=%s',
                cmd.command_id,
                exit_command_id,
                str(exc.args[0]) if exc.args else str(exc),
            )
            await self._append_submit_failed(
                runtime,
                exit_cmd,
                client_order_id,
                f'bracket protective OCO failed: {exc}',
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
        filled_qty, _ = self._scheme_fill_totals(runtime, cmd.command_id)

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
        '''

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

        filled_qty, cumulative_notional = self._scheme_fill_totals(runtime, cmd.command_id)

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
        filled_qty, cumulative_notional = self._scheme_fill_totals(runtime, cmd.command_id)

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

        avg_fill_price: Decimal | None = (
            order.cumulative_notional / order.filled_qty
            if order.filled_qty > _ZERO else None
        )

        emitted_filled_qty = order.filled_qty
        emitted_cumulative_notional = order.cumulative_notional
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
            status = (
                TradeStatus.FILLED
                if order.status == OrderStatus.FILLED else TradeStatus.PARTIAL
            )
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
