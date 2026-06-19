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
from datetime import datetime, timedelta, UTC
from decimal import Decimal

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
    Event,
    FillReceived,
    OrderCanceled,
    OrderExpired,
    OrderQuoteNativeFilled,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    TradeClosed,
    TradeOutcomeProduced,
)
from praxis.core.domain.order import Order
from praxis.core.domain.position import Position
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.estimate_slippage import estimate_slippage
from praxis.core.generate_client_order_id import (
    generate_client_order_id,
    validate_command_id_for_client_order_id,
)
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
)

__all__ = ['AccountNotRegisteredError', 'ExecutionManager']

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
_BOOT_ORPHAN_REASON = 'boot_orphan_command'
_ORPHAN_SENTINEL_QTY = Decimal(1)
_REPLAY_COMMAND_TIMEOUT_SECONDS = 60


class AccountNotRegisteredError(Exception):
    '''Raised when a command targets an unregistered account_id.'''


class _AccountRuntime:
    '''
    Per-account runtime state owned by ExecutionManager.

    Args:
        account_id (str): Account identifier.
        command_queue (asyncio.Queue[TradeCommand]): Unbounded queue for commands.
        priority_queue (asyncio.Queue[TradeAbort]): Unbounded queue for aborts.
        ws_event_queue (asyncio.Queue[Event]): Unbounded queue for WS events.
        trading_state (TradingState): Per-account state projection.
    '''

    def __init__(
        self,
        account_id: str,
        command_queue: asyncio.Queue[TradeCommand],
        priority_queue: asyncio.Queue[TradeAbort],
        ws_event_queue: asyncio.Queue[Event],
        trading_state: TradingState,
    ) -> None:
        '''Store per-account queues and projection.'''

        self.account_id = account_id
        self.command_queue = command_queue
        self.priority_queue = priority_queue
        self.ws_event_queue = ws_event_queue
        self.trading_state = trading_state
        self.task: asyncio.Task[None] | None = None
        self.command_to_order: dict[str, str] = {}


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
    '''

    def __init__(
        self,
        event_spine: EventSpine,
        epoch_id: int,
        venue_adapter: VenueAdapter,
        on_trade_outcome: Callable[[TradeOutcome], Awaitable[None]] | None = None,
    ) -> None:
        '''Store dependencies and initialize empty account registry.'''

        self._event_spine = event_spine
        self._epoch_id = epoch_id
        self._venue_adapter = venue_adapter
        self._on_trade_outcome = on_trade_outcome
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
            command_queue=asyncio.Queue(),
            priority_queue=asyncio.Queue(),
            ws_event_queue=asyncio.Queue(),
            trading_state=TradingState(account_id),
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

        for _seq, event in events:
            runtime.trading_state.apply(event)

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

                if event.command_id not in self._terminal_commands:
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

        Both classes synthesize `TradeOutcome(REJECTED,
        reason='boot_orphan_command')`, written to the spine as
        `TradeOutcomeProduced` and routed through
        `self._on_trade_outcome` so the launcher's
        `OutcomeProcessor` releases Nexus's reservation via
        `order_reject` lookup of the same `command_id`.

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

        for _seq, event in events:
            if isinstance(event, CommandAccepted):
                accepted_trade_ids[event.command_id] = event.trade_id
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

        class_a_orphans = [
            cid for cid in accepted_trade_ids
            if cid not in intent_command_ids and cid not in completed
        ]
        class_b_orphans = [
            cid for cid in intent_command_ids
            if cid not in completed
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

    async def _emit_orphan_rejection(
        self,
        runtime: _AccountRuntime,
        command_id: str,
        trade_id: str,
    ) -> None:
        ts = datetime.now(UTC)
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
        execution_params: SingleShotParams,
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
            execution_params (SingleShotParams): Mode-specific parameters.
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

        event = CommandAccepted(
            account_id=account_id,
            timestamp=datetime.now(UTC),
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

        runtime.command_queue.put_nowait(cmd)
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
                    try:
                        runtime.trading_state.apply(event)
                    except asyncio.CancelledError:
                        raise
                    except Exception:  # noqa: BLE001
                        _log.exception(
                            'unhandled exception while applying event: '
                            'event_type=%s account_id=%s',
                            type(event).__name__,
                            runtime.account_id,
                        )
                        continue
                    try:
                        await self._emit_ws_outcome(runtime, event)
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
        except asyncio.CancelledError:
            _log.info('account loop cancelled: %s', runtime.account_id)
            raise
        finally:
            _log.info('account loop exited: %s', runtime.account_id)

    async def _process_command(
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

        estimate = None
        if not cmd.is_quote_native:
            assert cmd.qty is not None
            try:
                book = await self._venue_adapter.query_order_book(
                    cmd.symbol,
                    limit=_SLIPPAGE_BOOK_LIMIT,
                )
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

        client_order_id = generate_client_order_id(
            cmd.execution_mode,
            cmd.command_id,
            sequence=0,
        )
        now = datetime.now(UTC)

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
            post_venue_ts = datetime.now(UTC)
        except (OrderSubmitTimeoutError, DuplicateClientOrderIdError) as exc:
            rescued = await self._rescue_by_client_order_id(
                runtime, cmd, client_order_id, exc,
            )
            if rescued is None:
                return await self._record_submit_failed(
                    runtime, cmd, client_order_id, str(exc.args[0]),
                )
            result = rescued
            post_venue_ts = datetime.now(UTC)
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
                runtime.trading_state.apply(fill_event)

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

        failed = OrderSubmitFailed(
            account_id=cmd.account_id,
            timestamp=datetime.now(UTC),
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
        return await self._build_outcome(
            runtime,
            cmd,
            TradeStatus.REJECTED,
            filled_qty=_ZERO,
            avg_fill_price=None,
            reason=reason,
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
                timestamp=datetime.now(UTC),
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

        ts = datetime.now(UTC)

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
            runtime.trading_state.apply(closed)

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

        ts = datetime.now(UTC)

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
                runtime.trading_state.apply(closed)

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
