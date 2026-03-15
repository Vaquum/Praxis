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
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
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
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.core.trading_state import TradingState
from praxis.core.validate_trade_abort import validate_trade_abort
from praxis.core.validate_trade_command import validate_trade_command
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import NotFoundError, VenueAdapter, VenueError

__all__ = ['AccountNotRegisteredError', 'ExecutionManager']

_log = logging.getLogger(__name__)

_QUEUE_POLL_INTERVAL = 0.1
_ZERO = Decimal(0)
_BPS_MULTIPLIER = Decimal('10000')
_SLIPPAGE_BOOK_LIMIT = 20
_TERMINAL_STATUSES = frozenset({
    TradeStatus.FILLED,
    TradeStatus.CANCELED,
    TradeStatus.REJECTED,
    TradeStatus.EXPIRED,
})


class AccountNotRegisteredError(Exception):
    '''Raised when a command targets an unregistered account_id.'''


class _AccountRuntime:
    '''
    Per-account runtime state owned by ExecutionManager.

    Args:
        account_id (str): Account identifier.
        command_queue (asyncio.Queue[TradeCommand]): Unbounded queue for commands.
        priority_queue (asyncio.Queue[TradeAbort]): Unbounded queue for aborts.
        trading_state (TradingState): Per-account state projection.
    '''

    def __init__(
        self,
        account_id: str,
        command_queue: asyncio.Queue[TradeCommand],
        priority_queue: asyncio.Queue[TradeAbort],
        trading_state: TradingState,
    ) -> None:
        '''Store per-account queues and projection.'''

        self.account_id = account_id
        self.command_queue = command_queue
        self.priority_queue = priority_queue
        self.trading_state = trading_state
        self.task: asyncio.Task[None] | None = None


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

        runtime = _AccountRuntime(
            account_id=account_id,
            command_queue=asyncio.Queue(),
            priority_queue=asyncio.Queue(),
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
        for pos in runtime.trading_state.positions.values():
            symbols.add(pos.symbol)
        return symbols

    def replay_events(
        self,
        account_id: str,
        events: list[tuple[int, Event]],
    ) -> None:
        '''
        Rebuild per-account state and runtime indices from event history.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        for _seq, event in events:
            runtime.trading_state.apply(event)

            if isinstance(event, CommandAccepted):
                self._accepted_commands[event.command_id] = account_id

            if isinstance(event, TradeOutcomeProduced) and event.status in _TERMINAL_STATUSES:
                self._terminal_commands.add(event.command_id)

            if isinstance(event, OrderSubmitIntent):
                self._command_trade_ids[event.command_id] = event.trade_id

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

        return {
            key: copy.copy(position)
            for key, position in runtime.trading_state.positions.items()
        }

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

    async def submit_command(
        self,
        *,
        trade_id: str,
        account_id: str,
        symbol: str,
        side: OrderSide,
        qty: Decimal,
        order_type: OrderType,
        execution_mode: ExecutionMode,
        execution_params: SingleShotParams,
        timeout: int,
        reference_price: Decimal | None,
        maker_preference: MakerPreference,
        stp_mode: STPMode,
        created_at: datetime,
    ) -> str:
        '''
        Accept a command, assign command_id, persist, and enqueue.

        Args:
            trade_id (str): Manager correlation identifier.
            account_id (str): Target account identifier.
            symbol (str): Trading pair symbol.
            side (OrderSide): Order direction.
            qty (Decimal): Total quantity to execute.
            order_type (OrderType): Order type.
            execution_mode (ExecutionMode): Execution strategy.
            execution_params (SingleShotParams): Mode-specific parameters.
            timeout (int): Execution deadline in seconds.
            reference_price (Decimal | None): Optional reference price.
            maker_preference (MakerPreference): Maker/taker preference.
            stp_mode (STPMode): Self-trade prevention mode.
            created_at (datetime): Command creation time.

        Returns:
            str: Assigned command_id (UUID).

        Raises:
            AccountNotRegisteredError: If account_id is not registered.
            ValueError: If command fails inbound validation.
        '''

        runtime = self._accounts.get(account_id)
        if runtime is None:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)

        command_id = str(uuid.uuid4())

        cmd = TradeCommand(
            command_id=command_id,
            trade_id=trade_id,
            account_id=account_id,
            symbol=symbol,
            side=side,
            qty=qty,
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
            timestamp=datetime.now(timezone.utc),
            command_id=command_id,
            trade_id=trade_id,
        )
        await self._event_spine.append(event, self._epoch_id)

        runtime.command_queue.put_nowait(cmd)
        self._accepted_commands[command_id] = account_id
        self._commands[command_id] = cmd
        self._command_trade_ids[command_id] = trade_id

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
        now = datetime.now(timezone.utc)

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
            price=cmd.execution_params.price,
            stop_price=cmd.execution_params.stop_price,
            stop_limit_price=cmd.execution_params.stop_limit_price,
        )
        await self._event_spine.append(intent, self._epoch_id)
        runtime.trading_state.apply(intent)

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
            )
            post_venue_ts = datetime.now(timezone.utc)
        except VenueError as exc:
            failed = OrderSubmitFailed(
                account_id=cmd.account_id,
                timestamp=datetime.now(timezone.utc),
                client_order_id=client_order_id,
                reason=str(exc.args[0]),
            )
            await self._event_spine.append(failed, self._epoch_id)
            runtime.trading_state.apply(failed)
            _log.warning(
                'order submit failed: client_order_id=%s reason=%s',
                client_order_id,
                str(exc.args[0]),
            )
            return await self._build_outcome(
                runtime,
                cmd,
                TradeStatus.REJECTED,
                filled_qty=_ZERO,
                avg_fill_price=None,
                reason=str(exc.args[0]),
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

        if filled_qty > _ZERO:
            total_notional = sum(
                (f.qty * f.price for f in result.immediate_fills),
                _ZERO,
            )
            avg_fill_price: Decimal | None = total_notional / filled_qty
        else:
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

        if filled_qty > cmd.qty:
            _log.warning(
                'overfill detected: command_id=%s filled_qty=%s target_qty=%s; clamping',
                cmd.command_id,
                filled_qty,
                cmd.qty,
            )
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

        cmd = self._commands.get(abort.command_id)
        if cmd is None:
            _log.warning(
                'abort for unknown command: command_id=%s',
                abort.command_id,
            )
            return None

        order: Order | None = None
        client_order_id: str | None = None
        for coid, o in runtime.trading_state.orders.items():
            if o.command_id == abort.command_id:
                order = o
                client_order_id = coid
                break

        if order is None or client_order_id is None:
            self._aborted_commands[abort.command_id] = abort.reason
            _log.info(
                'abort marked for pre-submission: command_id=%s',
                abort.command_id,
            )
            return None

        filled_qty = order.filled_qty
        venue_order_id = order.venue_order_id

        reason = abort.reason
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
            reason = f"{abort.reason}; cancel failed: {exc.args[0]}"
            cancel_confirmed = False

        if cancel_confirmed:
            canceled = OrderCanceled(
                account_id=cmd.account_id,
                timestamp=datetime.now(timezone.utc),
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                reason=abort.reason,
            )
            await self._event_spine.append(canceled, self._epoch_id)
            runtime.trading_state.apply(canceled)

        avg_fill_price: Decimal | None = None
        if filled_qty > _ZERO:
            events = await self._event_spine.read(self._epoch_id, after_seq=0)
            fills = [
                e
                for _, e in events
                if isinstance(e, FillReceived) and e.client_order_id == client_order_id
            ]
            total_notional = sum((f.qty * f.price for f in fills), _ZERO)
            avg_fill_price = total_notional / filled_qty

        return await self._build_outcome(
            runtime,
            cmd,
            TradeStatus.CANCELED,
            filled_qty=filled_qty,
            avg_fill_price=avg_fill_price,
            reason=reason,
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

        Returns:
            TradeOutcome: The constructed outcome.
        '''

        ts = datetime.now(timezone.utc)

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
        )

        if outcome.is_terminal:
            self._terminal_commands.add(cmd.command_id)
            self._commands.pop(cmd.command_id, None)
            self._aborted_commands.pop(cmd.command_id, None)

            if filled_qty > _ZERO:
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
        )
        await self._event_spine.append(produced, self._epoch_id)
        runtime.trading_state.apply(produced)

        if self._on_trade_outcome is not None:
            try:
                await self._on_trade_outcome(outcome)
            except Exception:  # noqa: BLE001
                _log.exception(
                    'on_trade_outcome callback failed: command_id=%s',
                    cmd.command_id,
                )

        return outcome
