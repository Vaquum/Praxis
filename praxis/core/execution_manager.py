'''
TradeCommand intake with per-account queues.

Route commands to per-account coroutines via unbounded asyncio queues.
Each registered account owns an independent command queue, priority
queue, and asyncio task.
'''

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.events import (
    CommandAccepted,
    FillReceived,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.core.trading_state import TradingState
from praxis.core.validate_trade_abort import validate_trade_abort
from praxis.core.validate_trade_command import validate_trade_command
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import VenueAdapter, VenueError

__all__ = ['AccountNotRegisteredError', 'ExecutionManager']

_log = logging.getLogger(__name__)

_QUEUE_POLL_INTERVAL = 0.1


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
    '''

    def __init__(
        self,
        event_spine: EventSpine,
        epoch_id: int,
        venue_adapter: VenueAdapter,
    ) -> None:
        '''Store dependencies and initialize empty account registry.'''

        self._event_spine = event_spine
        self._epoch_id = epoch_id
        self._venue_adapter = venue_adapter
        self._accounts: dict[str, _AccountRuntime] = {}
        self._accepted_commands: dict[str, str] = {}
        self._terminal_commands: set[str] = set()

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
    ) -> None:
        '''
        Submit a single order to the venue and emit resulting events.

        Persist an OrderSubmitIntent before the venue call for crash
        durability, then append OrderSubmitted + FillReceived events
        on success or OrderSubmitFailed on venue error.

        Args:
            runtime (_AccountRuntime): Per-account state to update.
            cmd (TradeCommand): Command to execute.
        '''

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
                client_order_id=client_order_id,
            )
            post_venue_ts = datetime.now(timezone.utc)
        except VenueError as exc:
            failed = OrderSubmitFailed(
                account_id=cmd.account_id,
                timestamp=datetime.now(timezone.utc),
                client_order_id=client_order_id,
                reason=str(exc),
            )
            await self._event_spine.append(failed, self._epoch_id)
            runtime.trading_state.apply(failed)
            _log.warning(
                'order submit failed: client_order_id=%s reason=%s',
                client_order_id,
                str(exc),
            )
            return

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
