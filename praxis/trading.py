from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import queue
import threading
from collections import defaultdict
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from collections.abc import Awaitable, Callable
from typing import Any, cast

from praxis.core.execution_manager import AccountNotRegisteredError, ExecutionManager
from praxis.core.generate_client_order_id import praxis_command_fragment
from praxis.core.domain.enums import (
    ExecutionMode,
    ExecutionType,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
)
from praxis.core.domain.health_snapshot import HealthSnapshot
from praxis.core.domain.position import Position
from praxis.core.domain.execution_params import ExecutionParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_modify import TradeModify
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.events import (
    Event,
    FillReceived,
    FundTransaction,
    OrderCanceled,
    OrderExpired,
    OrderRejected,
    ReconciliationMismatch,
)
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.binance_ws import BinanceUserStream
from praxis.infrastructure.mytrades_backfill import paginate_my_trades, venue_trade_id_int
from praxis.infrastructure.venue_adapter import NotFoundError, VenueAdapter, VenueError
from praxis.trading_config import TradingConfig
from praxis.trading_inbound import TradingInbound

__all__ = ['Trading']

_log = logging.getLogger(__name__)
_BACKFILL_BOOTSTRAP_LOOKBACK = timedelta(hours=24)
_QUOTE_ASSET = 'USDT'
_ZERO = Decimal(0)
_BALANCE_TOLERANCE: dict[str, Decimal] = {
    'USDT': Decimal('0.01'),
    'BTC': Decimal('0.00000001'),
}
_TERMINAL_ORDER_STATUSES = frozenset({
    OrderStatus.FILLED,
    OrderStatus.CANCELED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
})


def _utc_now() -> datetime:
    '''Return the current UTC time.'''

    return datetime.now(UTC)


def _wrap_event_callback[E](
    cb: Callable[[E], None] | Callable[[E], Awaitable[None]] | None,
) -> Callable[[E], Awaitable[None]]:
    '''Adapt a sync-or-async event callback into an always-async adapter.

    Mirrors `set_on_trade_outcome`'s adapter: the returned coroutine
    awaits the result when it is awaitable and treats it as a plain
    return otherwise, covering coroutine functions, sync callables,
    `AsyncMock`, and `functools.partial` wrappers. A `None` callback
    yields a no-op adapter so callers can fire unconditionally.

    Args:
        cb: The sync or async callback, or `None` for a no-op.

    Returns:
        An async adapter that never raises on a `None` callback.
    '''

    async def _adapter(event: E) -> None:
        if cb is None:
            return

        result = cb(event)

        if inspect.isawaitable(result):
            await result

    return _adapter


class Trading:
    '''
    Main trading composition root for MMVP wiring.

    Wires venue adapter, execution manager, and inbound facade into a single
    manager-facing object with MMVP lifecycle supervision (`start`/`stop`).

    Args:
        config (TradingConfig): Runtime wiring configuration.
        event_spine (EventSpine): Event Spine instance to use.
        venue_adapter (VenueAdapter | None): Optional injected venue adapter.
            If omitted, a BinanceAdapter is created from config URLs.
        bootstrap_filter_symbols (frozenset[str]): Trading symbols whose
            venue filters must be cached before any orders submit,
            regardless of whether the account has open orders or
            positions at boot. Merged with the per-account
            `ExecutionManager.active_symbols` set inside
            `_startup_account` so a fresh paper-trade boot still
            primes `BinanceAdapter._filters` for the launcher's
            default symbol. Defaults to `frozenset()` (preserves
            historical behaviour).
    '''

    def __init__(
        self,
        *,
        config: TradingConfig,
        event_spine: EventSpine,
        venue_adapter: VenueAdapter | None = None,
        bootstrap_filter_symbols: frozenset[str] = frozenset(),
        clock: Callable[[], datetime] = _utc_now,
        max_slippage_bps: Decimal | None = None,
    ) -> None:
        '''Compose core trading dependencies and manager-facing facade.

        `bootstrap_filter_symbols` is the set of trading symbols the
        adapter must have cached venue filters for *before any orders
        are submitted*, regardless of whether the account has open
        orders or positions at boot. On a fresh paper-trade boot the
        `ExecutionManager.active_symbols(account_id)` set is empty —
        the launcher's `_DEFAULT_SYMBOL='BTCUSDT'` is discovered only
        when the first strategy emits an ENTER action, which is after
        `_startup_account` has already completed. Without this
        bootstrap set, `BinanceAdapter._validate_order` falls through
        on the "No cached filters for X, skipping validation" warning
        path and the first venue submission fails with Binance error
        code -1100 (`Illegal characters found in parameter 'quantity'`).
        '''

        self._config = config
        self._on_fund_transaction = _wrap_event_callback(config.on_fund_transaction)
        self._on_reconciliation_mismatch = _wrap_event_callback(
            config.on_reconciliation_mismatch,
        )
        self._event_spine = event_spine
        self._clock = clock
        self._bootstrap_filter_symbols = frozenset(bootstrap_filter_symbols)
        if venue_adapter is None:
            self._venue_adapter = cast(
                VenueAdapter,
                BinanceAdapter(
                    base_url=config.venue_rest_url,
                    ws_base_url=config.venue_ws_url,
                    ws_api_url=config.venue_ws_api_url,
                    credentials=dict(config.account_credentials),
                ),
            )
        else:
            self._venue_adapter = venue_adapter
        self._execution_manager = ExecutionManager(
            event_spine=event_spine,
            epoch_id=config.epoch_id,
            venue_adapter=self._venue_adapter,
            on_trade_outcome=config.on_trade_outcome,
            clock=clock,
            max_slippage_bps=max_slippage_bps,
            enabled_modes=config.enabled_execution_modes,
        )
        self._inbound = TradingInbound(
            execution_manager=self._execution_manager,
            venue_adapter=self._venue_adapter,
            account_credentials=config.account_credentials,
        )
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._outcome_queues: dict[str, queue.Queue[TradeOutcome]] = {}
        self._outcome_lock = threading.Lock()
        self._managed_accounts: set[str] = set()
        self._user_streams: dict[str, BinanceUserStream] = {}
        self._ready_accounts: set[str] = set()
        self._reconciling_accounts: set[str] = set()
        self._reconcile_rerun_pending: set[str] = set()
        self._fund_reconcile_cursor: dict[str, datetime] = {}
        self._balance_mismatch_seen: dict[tuple[str, str], Decimal] = {}
        self._reconcile_task: asyncio.Task[None] | None = None
        self._stopping = False

    @property
    def config(self) -> TradingConfig:
        '''Runtime wiring configuration for this trading instance.'''

        return self._config

    @property
    def event_spine(self) -> EventSpine:
        '''Event Spine used by this trading instance.'''

        return self._event_spine

    @property
    def venue_adapter(self) -> VenueAdapter:
        '''Venue adapter wired for this trading instance.'''

        return self._venue_adapter

    @property
    def execution_manager(self) -> ExecutionManager:
        '''Execution manager wired for this trading instance.'''

        return self._execution_manager

    @property
    def started(self) -> bool:
        '''Whether the trading runtime has been started.'''

        return self._started

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        '''Return the asyncio event loop running this Trading instance.

        Raises:
            RuntimeError: If Trading.start() has not been awaited.
        '''

        if self._loop is None:
            msg = 'Trading.start() must be awaited before accessing loop'
            raise RuntimeError(msg)

        return self._loop

    def register_outcome_queue(
        self,
        account_id: str,
        q: queue.Queue[TradeOutcome],
    ) -> None:
        '''Register a thread-safe queue for routing TradeOutcomes to a Nexus instance.

        Args:
            account_id: Account identifier.
            q: Thread-safe queue that Nexus instance reads from.
        '''

        with self._outcome_lock:
            self._outcome_queues[account_id] = q

    def unregister_outcome_queue(self, account_id: str) -> None:
        '''Remove outcome queue for an account.

        Args:
            account_id: Account identifier.
        '''

        with self._outcome_lock:
            self._outcome_queues.pop(account_id, None)

    def route_outcome(self, outcome: TradeOutcome) -> None:
        '''Route a TradeOutcome to the correct account's queue.

        Called by the on_trade_outcome callback. Drops outcomes
        for accounts without a registered queue.

        Args:
            outcome: TradeOutcome to route.
        '''

        with self._outcome_lock:
            q = self._outcome_queues.get(outcome.account_id)

        if q is None:
            _log.warning(
                'no outcome queue for account, dropping outcome',
                extra={'account_id': outcome.account_id, 'command_id': outcome.command_id},
            )
            return

        q.put_nowait(outcome)

    def set_on_trade_outcome(
        self,
        cb: Callable[[TradeOutcome], None] | Callable[[TradeOutcome], Awaitable[None]] | None,
    ) -> None:
        '''Install the on_trade_outcome callback after `Trading()` construction.

        Closes the chicken-and-egg gap where `TradingConfig.on_trade_outcome`
        cannot reference the not-yet-built `Trading` instance. The launcher
        calls this immediately after `Trading()` returns, typically with
        `trading.route_outcome` so per-account `TradeOutcome`s land on the
        registered queues.

        Callbacks are always wrapped in an `async` adapter that awaits
        the result when it is awaitable and treats it as a plain return
        value otherwise. This covers coroutine functions, plain sync
        callables, `functools.partial` around coroutine functions,
        `AsyncMock`, and callables whose `__call__` is `async` — all
        cases where `asyncio.iscoroutinefunction` would misclassify
        and drop the returned coroutine without awaiting it.

        Args:
            cb: Sync `(TradeOutcome) -> None`, async
                `(TradeOutcome) -> Awaitable[None]`, any callable that
                returns an awaitable, or `None` to clear.

        Raises:
            RuntimeError: If called once `start()` has begun — the
                replay loop and in-flight order coroutines rely on a
                stable callback identity, so swapping it once startup
                is in progress would race with outcome production.
                The guard fires both during startup (after
                `start()` sets `self._loop` but before
                `self._started`) and after start completes.
        '''

        if self._started or self._loop is not None:
            msg = (
                'set_on_trade_outcome must not be called once '
                'Trading.start() has begun'
            )
            raise RuntimeError(msg)

        if cb is None:
            self._execution_manager.set_on_trade_outcome(None)
            return

        user_cb = cb

        async def _async_adapter(outcome: TradeOutcome) -> None:
            result = user_cb(outcome)

            if inspect.isawaitable(result):
                await result

        self._execution_manager.set_on_trade_outcome(_async_adapter)

    def set_on_fund_transaction(
        self,
        cb: Callable[[FundTransaction], None]
        | Callable[[FundTransaction], Awaitable[None]]
        | None,
    ) -> None:
        '''Install the on_fund_transaction callback after construction.

        The launcher wires this to a per-account dispatcher that only
        exists once its Nexus runtimes are built, so it cannot be
        referenced by the frozen `TradingConfig`. Called before
        `start()`, alongside `set_on_trade_outcome`.

        Args:
            cb: Sync `(FundTransaction) -> None`, async equivalent, any
                callable returning an awaitable, or `None` to clear.

        Raises:
            RuntimeError: If called once `start()` has begun.
        '''

        if self._started or self._loop is not None:
            msg = (
                'set_on_fund_transaction must not be called once '
                'Trading.start() has begun'
            )
            raise RuntimeError(msg)

        self._on_fund_transaction = _wrap_event_callback(cb)

    def set_on_reconciliation_mismatch(
        self,
        cb: Callable[[ReconciliationMismatch], None]
        | Callable[[ReconciliationMismatch], Awaitable[None]]
        | None,
    ) -> None:
        '''Install the on_reconciliation_mismatch callback after construction.

        The launcher wires this to a per-account dispatcher that only
        exists once its Nexus runtimes are built, so it cannot be
        referenced by the frozen `TradingConfig`. Called before
        `start()`, alongside `set_on_trade_outcome`.

        Args:
            cb: Sync `(ReconciliationMismatch) -> None`, async
                equivalent, any callable returning an awaitable, or
                `None` to clear.

        Raises:
            RuntimeError: If called once `start()` has begun.
        '''

        if self._started or self._loop is not None:
            msg = (
                'set_on_reconciliation_mismatch must not be called once '
                'Trading.start() has begun'
            )
            raise RuntimeError(msg)

        self._on_reconciliation_mismatch = _wrap_event_callback(cb)

    async def start(self) -> None:
        '''Initialize runtime and execute per-account startup sequence.'''

        if self._started:
            return

        self._loop = asyncio.get_running_loop()

        try:
            await self._event_spine.ensure_schema()
            await self._event_spine.verify_chain()

            all_events = await self._event_spine.read(self._config.epoch_id)

            events_by_account: defaultdict[str, list[tuple[int, Event]]] = defaultdict(list)
            for seq, event in all_events:
                events_by_account[event.account_id].append((seq, event))

            for account_id in self._config.account_credentials:
                self._inbound.register_account(account_id)
                self._managed_accounts.add(account_id)
                await self._startup_account(account_id, events_by_account[account_id])
        except Exception:
            self._loop = None
            await self._cleanup_partial_startup()
            raise

        self._reconcile_task = asyncio.create_task(self._reconciliation_loop())
        self._started = True

    async def _startup_account(
        self,
        account_id: str,
        account_events: list[tuple[int, Event]],
    ) -> None:
        '''
        Execute per-account startup phases in required order.

        Args:
            account_id (str): Account identifier to start up.
            account_events: Pre-filtered events for this account.
        '''

        self._execution_manager.replay_events(account_id, account_events)
        await self._execution_manager.register_account_on_spine(account_id)
        await self._execution_manager.reconcile_orphan_commands(
            account_id, account_events,
        )

        symbols = set(self._execution_manager.active_symbols(account_id))
        symbols |= self._bootstrap_filter_symbols
        if symbols:
            await self._venue_adapter.load_filters(sorted(symbols))

        account_ready = await self._sweep_orphan_venue_orders(account_id)

        if isinstance(self._venue_adapter, BinanceAdapter):
            adapter = self._venue_adapter

            async def on_message(data: dict[str, Any]) -> None:
                await self._on_execution_report(account_id, data)

            async def on_disconnect() -> None:
                self._execution_manager.set_reconciling(account_id, True)

            async def on_reconnect() -> None:
                await self._reconcile_on_reconnect(account_id)

            stream = BinanceUserStream(
                adapter=adapter,
                account_id=account_id,
                on_message=on_message,
                on_disconnect=on_disconnect,
                on_reconnect=on_reconnect,
            )
            await stream.initiate_connection()
            self._user_streams[account_id] = stream
            await self._reconcile_on_reconnect(account_id)
        else:
            await self._reconcile_account(account_id)

        if account_ready:
            self._ready_accounts.add(account_id)
        else:
            _log.error(
                'account %s not marked ready: an orphan venue open order could '
                'not be cancelled during the boot sweep (fail closed)',
                account_id,
            )

    async def stop(self) -> None:
        '''Stop runtime and cleanup managed account registrations.'''

        if not self._started:
            return

        self._stopping = True

        if self._reconcile_task is not None:
            self._reconcile_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconcile_task
            self._reconcile_task = None

        try:
            in_flight_by_account: dict[str, set[str]] = {}
            for account_id in sorted(self._managed_accounts):
                command_ids = self._execution_manager.in_flight_command_ids(account_id)
                in_flight_by_account[account_id] = set(command_ids)
                for command_id in command_ids:
                    try:
                        self._execution_manager.submit_abort(
                            TradeAbort(
                                command_id=command_id,
                                account_id=account_id,
                                reason='shutdown',
                                created_at=self._clock(),
                            ),
                        )
                    except (AccountNotRegisteredError, ValueError):
                        # The abort did not enqueue, so this command's orders
                        # will not be cancelled by the abort path; drop it
                        # from the skip set so the orphan pass cancels them.
                        in_flight_by_account[account_id].discard(command_id)
                        continue

            # The abort path cancels each in-flight command's orders as the
            # account loop drains it; this pass only cancels orphan orders —
            # open orders with no in-flight command (e.g. reconcile-adopted) —
            # so a tracked order is not cancelled twice.
            for account_id in sorted(self._managed_accounts):
                try:
                    open_orders = self._execution_manager.get_open_orders(account_id)
                except AccountNotRegisteredError:
                    continue
                in_flight = in_flight_by_account.get(account_id, set())
                for order in open_orders.values():
                    if order.command_id in in_flight:
                        continue
                    try:
                        if order.order_type == OrderType.OCO:
                            await self._venue_adapter.cancel_order_list(
                                account_id,
                                order.symbol,
                                client_order_id=order.client_order_id,
                            )
                        else:
                            await self._venue_adapter.cancel_order(
                                account_id,
                                order.symbol,
                                client_order_id=order.client_order_id,
                            )
                    except asyncio.CancelledError:
                        raise
                    except Exception:  # noqa: BLE001
                        _log.warning(
                            'shutdown cancel failed: account=%s order=%s',
                            account_id,
                            order.client_order_id,
                        )

            loop = asyncio.get_running_loop()
            deadline = loop.time() + self._config.shutdown_timeout
            poll_interval = 0.1
            while loop.time() < deadline:
                has_open = False
                for account_id in list(self._managed_accounts):
                    try:
                        if self._execution_manager.get_open_orders(account_id):
                            has_open = True
                            break
                    except AccountNotRegisteredError:
                        continue
                    if self._execution_manager.in_flight_command_ids(account_id):
                        has_open = True
                        break
                if not has_open:
                    break
                remaining = deadline - loop.time()
                await asyncio.sleep(min(poll_interval, max(0.0, remaining)))
            else:
                _log.warning('shutdown timeout: orders or modes may still be open')

            for account_id, stream in list(self._user_streams.items()):
                try:
                    await stream.close()
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001
                    _log.exception('error closing user stream: %s', account_id)
                self._user_streams.pop(account_id, None)

            try:
                await self._venue_adapter.close()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - shutdown teardown must not raise
                _log.exception('error closing venue adapter')

            first_error: Exception | None = None
            for account_id in sorted(self._managed_accounts):
                try:
                    await self._inbound.unregister_account(account_id)
                    self._managed_accounts.discard(account_id)
                    self._ready_accounts.discard(account_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    if first_error is None:
                        first_error = exc

            if first_error is not None:
                raise first_error

            self._started = False
            self._loop = None
        finally:
            self._stopping = False

    async def _cleanup_partial_startup(self) -> None:
        '''Clean up resources from failed startup.'''

        for account_id in list(self._user_streams):
            try:
                await self._user_streams[account_id].close()
            except Exception:  # noqa: BLE001
                _log.exception('error closing user stream during cleanup: %s', account_id)
            self._user_streams.pop(account_id, None)

        for account_id in list(self._managed_accounts):
            try:
                await self._inbound.unregister_account(account_id)
            except Exception:  # noqa: BLE001
                _log.exception('error unregistering account during cleanup: %s', account_id)
            self._managed_accounts.discard(account_id)
            self._ready_accounts.discard(account_id)

    def _require_started(self) -> None:
        if not self._started:
            msg = 'Trading.start() must be awaited before using trading operations'
            raise RuntimeError(msg)

    def _require_account_ready(self, account_id: str) -> None:
        '''
        Raise if account startup has not completed.

        Args:
            account_id (str): Account identifier to check.
        '''

        self._require_started()
        if account_id not in self._ready_accounts:
            msg = f'account {account_id} startup not complete'
            raise RuntimeError(msg)

    async def _reconcile_account(self, account_id: str) -> None:
        '''
        Reconcile projected state against venue for open orders.

        Args:
            account_id (str): Account identifier to reconcile.
        '''

        trading_state = self._execution_manager.get_trading_state(account_id)
        if trading_state is None:
            return

        for client_order_id, order in list(trading_state.orders.items()):
            if order.is_terminal:
                continue

            try:
                venue_order = await self._venue_adapter.query_order(
                    account_id,
                    order.symbol,
                    client_order_id=client_order_id,
                )
            except NotFoundError:
                _log.warning(
                    'order not found on venue during reconciliation: %s',
                    client_order_id,
                )
                continue
            except VenueError as exc:
                _log.warning(
                    'venue error during reconciliation: %s %s',
                    client_order_id,
                    exc.args[0] if exc.args else str(exc),
                )
                continue

            if venue_order.filled_qty > order.filled_qty:
                await self._reconcile_fills(account_id, order)

            venue_terminal = venue_order.status in _TERMINAL_ORDER_STATUSES
            if venue_terminal and not order.is_terminal:
                await self._reconcile_terminal(
                    account_id, order, venue_order,
                )

    async def _sweep_orphan_venue_orders(self, account_id: str) -> bool:
        '''Cancel venue open orders with no local record.

        A venue order whose `OrderSubmitIntent` never reached the spine
        (a SIGKILL between the REST acknowledgement and the spine append)
        is invisible to local replay, leaving orphaned exposure. This runs
        after event replay populates the local record but before the venue
        user stream opens, so an orphan is cancelled before the stream
        could deliver — and `_on_execution_report` silently drop — its
        fill report. The sweep queries the venue's open orders for every
        managed symbol; an open order that is unknown locally yet embeds
        the command fragment (`praxis_command_fragment`) of a command
        this account has accepted (`owned_command_fragments`) is a
        self-inflicted orphan and is cancelled — never adopted, because
        Praxis cannot reconstruct its `trade_id` / Nexus capital lineage
        from a venue order alone — with a high-severity log. The accepted
        command set is the authoritative ownership signal: an order whose
        id merely imitates the minting shape but ties to no accepted
        command, and an order placed manually or by another system, are
        both foreign — Praxis does not manage what it did not create, so
        they are left untouched and do not gate readiness. An OCO leg is
        cancelled via `cancel_order_list`, since the venue rejects
        single-leg OCO cancellation (mirroring `stop`).

        Args:
            account_id (str): Account identifier to sweep.

        Returns:
            bool: `True` when the account is safe to mark ready (no
            orphan, or every orphan cancelled); `False` when an orphan
            could not be cancelled or a sweep query failed (so orphans
            cannot be confirmed), in which case the caller leaves the
            account not-ready (fail closed — never trade alongside a
            possible live, untracked venue order).
        '''

        trading_state = self._execution_manager.get_trading_state(account_id)
        if trading_state is None:
            return True

        known = set(trading_state.orders) | set(trading_state.closed_orders)
        owned_fragments = self._execution_manager.owned_command_fragments(account_id)
        symbols = (
            set(self._execution_manager.active_symbols(account_id))
            | self._bootstrap_filter_symbols
        )
        safe = True

        for symbol in sorted(symbols):
            try:
                venue_orders = await self._venue_adapter.query_open_orders(account_id, symbol)
            except VenueError as exc:
                _log.error(
                    'open-orders sweep query failed; cannot confirm orphans, account '
                    'stays not-ready (fail closed): symbol=%s error=%s',
                    symbol,
                    exc.args[0] if exc.args else str(exc),
                )
                safe = False
                continue

            for venue_order in venue_orders:
                if venue_order.client_order_id in known:
                    continue

                fragment = praxis_command_fragment(venue_order.client_order_id)
                if fragment is None or fragment not in owned_fragments:
                    _log.info(
                        'foreign venue open order left untouched (no Praxis '
                        'lineage): symbol=%s client_order_id=%s',
                        symbol,
                        venue_order.client_order_id,
                    )
                    continue

                _log.error(
                    'orphan venue open order with no local record — cancelling, '
                    'not adopting: symbol=%s client_order_id=%s venue_order_id=%s status=%s',
                    symbol,
                    venue_order.client_order_id,
                    venue_order.venue_order_id,
                    venue_order.status.value,
                )

                try:
                    if venue_order.order_type == OrderType.OCO:
                        await self._venue_adapter.cancel_order_list(
                            account_id,
                            symbol,
                            client_order_id=venue_order.client_order_id,
                        )
                    else:
                        await self._venue_adapter.cancel_order(
                            account_id,
                            symbol,
                            client_order_id=venue_order.client_order_id,
                        )
                except VenueError as exc:
                    _log.error(
                        'failed to cancel orphan venue order; account stays '
                        'not-ready (fail closed): symbol=%s client_order_id=%s error=%s',
                        symbol,
                        venue_order.client_order_id,
                        exc.args[0] if exc.args else str(exc),
                    )
                    safe = False

        return safe

    async def _reconcile_fills(
        self,
        account_id: str,
        order: Any,
    ) -> None:
        '''
        Query and emit missing fills for an order.

        Args:
            account_id (str): Account identifier.
            order: Local order projection.
        '''

        trading_state = self._execution_manager.get_trading_state(account_id)
        if trading_state is None:
            return

        try:
            trades = await self._venue_adapter.query_trades(
                account_id,
                order.symbol,
                start_time=order.created_at,
            )
        except VenueError as exc:
            _log.warning(
                'failed to query trades for reconciliation: %s %s',
                order.client_order_id,
                exc.args[0] if exc.args else str(exc),
            )
            return

        command_id = order.command_id
        trade_id = self._execution_manager.trade_id_for_command(command_id)
        if trade_id is None:
            _log.warning(
                'cannot reconcile fills: no trade_id mapping for command_id=%s order=%s',
                command_id,
                order.client_order_id,
            )
            return

        for trade in trades:
            if trade.client_order_id != order.client_order_id:
                continue

            fill_event = FillReceived(
                account_id=account_id,
                timestamp=trade.timestamp,
                client_order_id=trade.client_order_id,
                venue_order_id=trade.venue_order_id,
                venue_trade_id=trade.venue_trade_id,
                trade_id=trade_id,
                command_id=command_id,
                symbol=trade.symbol,
                side=trade.side,
                qty=trade.qty,
                price=trade.price,
                fee=trade.fee,
                fee_asset=trade.fee_asset,
                is_maker=trade.is_maker,
            )

            seq = await self._event_spine.append(fill_event, self._config.epoch_id)
            if seq is not None:
                self._execution_manager.enqueue_ws_event(account_id, fill_event)
                _log.info(
                    'reconciled fill: %s %s',
                    order.client_order_id,
                    trade.venue_trade_id,
                )

    async def _reconcile_fund_transactions(self, account_id: str) -> None:
        '''
        Detect quote-asset deposits/withdrawals and record them for the account.

        The Reconciliation Engine role: poll the venue for settled fund
        transactions since the last-seen cursor, and for each new quote-asset
        (USDT) transaction append a `FundTransaction` to the spine and hand it
        to the account coroutine to project into the ledger. As with fill
        reconciliation the spine deduplicates on `fund_transaction_id`, so a
        re-detected transaction is a silent no-op and the cursor is only an
        efficiency bound, not the durability guarantee. Base-asset movements
        are not modelled by `FundTransaction`; they surface instead as a
        balance mismatch in the balance-reconciliation pass.

        Args:
            account_id (str): Account identifier to reconcile.
        '''

        since = self._fund_reconcile_cursor.get(account_id)

        try:
            transactions = await self._venue_adapter.query_fund_transactions(
                account_id, start_time=since,
            )
        except VenueError as exc:
            _log.warning(
                'failed to query fund transactions for reconciliation: %s',
                exc.args[0] if exc.args else str(exc),
            )
            return

        all_delivered = True

        for transaction in transactions:
            if transaction.asset != _QUOTE_ASSET:
                continue

            fund = FundTransaction(
                account_id=account_id,
                timestamp=transaction.timestamp,
                fund_transaction_id=transaction.fund_transaction_id,
                amount=transaction.amount,
                direction=transaction.direction,
            )

            seq = await self._event_spine.append(fund, self._config.epoch_id)
            if seq is not None:
                self._execution_manager.enqueue_ws_event(account_id, fund)
                _log.info(
                    'reconciled fund transaction: %s %s %s',
                    transaction.direction,
                    transaction.amount,
                    transaction.fund_transaction_id,
                )

            try:
                await self._on_fund_transaction(fund)
            except Exception:  # noqa: BLE001 - hold the cursor to retry delivery next cycle
                _log.exception(
                    'failed to deliver fund transaction to Nexus; will retry '
                    'next cycle: %s',
                    fund.fund_transaction_id,
                )
                all_delivered = False
                break

        if transactions and all_delivered:
            self._fund_reconcile_cursor[account_id] = max(
                transaction.timestamp for transaction in transactions
            )

    async def _reconcile_balances(self, account_id: str) -> None:
        '''
        Compare the account's projected per-asset balances against the venue.

        The Reconciliation Engine role: read the ledger's raw per-asset
        balances (the projection derived from fills and fund transactions) and
        the venue's reported balances (`free + locked`, since locked funds are
        still held), and append a `ReconciliationMismatch` to the spine for any
        asset where the venue holds LESS than the ledger expects beyond its
        tolerance. Only a shortfall is a mismatch: Praxis's own funds are
        missing or a fill was double-counted, and it is never silently dropped.
        An excess (the venue holds more than the ledger expects) is untracked
        capital Praxis never created — a manual deposit or another system's
        position on a commingled asset — which Praxis does not manage and does
        not flag; the trade backfill on reconnect, not this floor check, is the
        path that catches a missed Praxis buy fill. The same divergence is
        reported once until it changes or clears, so a persistent mismatch does
        not append an event every cycle; the seen-marker is set only after a
        durable append, so a transient spine failure retries next cycle rather
        than silently suppressing the alert. Base-asset (BTC) raw quantity is
        summed from the ledger's cost-basis lots; the venue reports it
        directly.

        The pass is skipped while events are queued for projection: the ledger
        lags the spine until the account coroutine drains its queue, so a
        just-detected deposit or an unprojected fill would otherwise read as a
        false mismatch. The next cycle, once caught up, reconciles cleanly.

        Args:
            account_id (str): Account identifier to reconcile.
        '''

        if self._execution_manager.has_pending_ws_events(account_id):
            return

        expected_balances = self._execution_manager.get_asset_balances(account_id)

        try:
            entries = await self._venue_adapter.query_balance(
                account_id, frozenset(expected_balances),
            )
        except VenueError as exc:
            _log.warning(
                'failed to query balances for reconciliation: %s',
                exc.args[0] if exc.args else str(exc),
            )
            return

        venue_totals = {entry.asset: entry.free + entry.locked for entry in entries}

        for asset, expected in expected_balances.items():
            actual = venue_totals.get(asset, _ZERO)
            delta = actual - expected
            key = (account_id, asset)

            if delta >= -_BALANCE_TOLERANCE.get(asset, _ZERO):
                self._balance_mismatch_seen.pop(key, None)
                continue

            if self._balance_mismatch_seen.get(key) == delta:
                continue

            now = self._clock()
            mismatch = ReconciliationMismatch(
                account_id=account_id,
                timestamp=now,
                reconciliation_mismatch_id=f'balance-{account_id}-{asset}-{now.isoformat()}',
                asset=asset,
                expected=expected,
                actual=actual,
            )

            await self._event_spine.append(mismatch, self._config.epoch_id)
            _log.warning(
                'balance mismatch: account=%s asset=%s expected=%s actual=%s',
                account_id, asset, expected, actual,
            )

            try:
                await self._on_reconciliation_mismatch(mismatch)
            except Exception:  # noqa: BLE001 - leave unseen to retry delivery next cycle
                _log.exception(
                    'failed to deliver reconciliation mismatch to Nexus; '
                    'will retry next cycle: account=%s asset=%s',
                    account_id, asset,
                )
                continue

            self._balance_mismatch_seen[key] = delta

    async def _reconciliation_loop(self) -> None:
        '''
        Run the detector-style reconciliation passes periodically, off the
        critical path.

        Sleeps `reconcile_interval_seconds` between cycles, then for each ready
        account polls fund transactions and reconciles balances against the
        venue. A per-account failure is logged and never propagated, so one
        account's venue error cannot stop the loop or affect another account.
        Started by `start` and cancelled by `stop`; because it runs as its own
        background task, a slow venue call delays only the next cycle and never
        blocks account startup or order reconciliation.
        '''

        while not self._stopping:
            try:
                await asyncio.sleep(self._config.reconcile_interval_seconds)
            except asyncio.CancelledError:
                return

            for account_id in sorted(self._ready_accounts):
                if self._stopping:
                    return

                try:
                    await self._reconcile_fund_transactions(account_id)
                    await self._reconcile_balances(account_id)
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001 - a detector must not stop the loop
                    _log.exception(
                        'reconciliation cycle failed for account: %s', account_id,
                    )

    async def _reconcile_on_reconnect(self, account_id: str) -> None:
        '''
        Backfill missed fills and reconcile orders, submission-gated.

        Runs at boot (after the stream opens) and on every WS reconnect
        edge. Holds the account's submission gate while it backfills
        myTrades from the durable cursor and reconciles open orders, then
        releases the gate only when the backfill fully drained. A truncated
        backfill (page cap) or a venue failure leaves the account gated
        (fail-closed) until a later reconcile drains it or a restart. A
        reconnect arriving mid-pass schedules exactly one rerun.

        Args:
            account_id (str): Account identifier.
        '''

        if account_id in self._reconciling_accounts:
            self._reconcile_rerun_pending.add(account_id)
            return

        self._reconciling_accounts.add(account_id)
        try:
            while True:
                self._execution_manager.set_reconciling(account_id, True)
                try:
                    complete = await self._backfill_account(account_id)
                    await self._reconcile_account(account_id)
                except VenueError as exc:
                    _log.error(
                        'reconcile failed; account stays gated (fail closed): %s %s',
                        account_id,
                        exc.args[0] if exc.args else str(exc),
                    )
                    return

                if not complete:
                    _log.warning(
                        'backfill incomplete; account stays gated until a later '
                        'reconcile drains it: %s',
                        account_id,
                    )
                    return

                if account_id not in self._reconcile_rerun_pending:
                    self._execution_manager.set_reconciling(account_id, False)
                    return
                self._reconcile_rerun_pending.discard(account_id)
        finally:
            self._reconciling_accounts.discard(account_id)
            self._reconcile_rerun_pending.discard(account_id)

    async def _backfill_account(self, account_id: str) -> bool:
        '''
        Paginate myTrades from the durable cursor and apply missed fills per symbol.

        For each symbol in the account's universe, backfills from the
        per-(account, symbol) cursor, mapping each trade to its local order
        to reconstruct the fill lineage; a trade for an order unknown
        locally is skipped (out of scope). The cursor advances only when a
        pass fully drains the stream.

        Args:
            account_id (str): Account identifier.

        Returns:
            bool: True when every symbol's myTrades stream fully drained;
            False when any symbol was truncated (page cap or non-numeric
            boundary), so backfill is incomplete.
        '''

        trading_state = self._execution_manager.get_trading_state(account_id)
        if trading_state is None:
            return True

        all_complete = True
        symbols = (
            set(self._execution_manager.active_symbols(account_id))
            | self._bootstrap_filter_symbols
        )
        for symbol in sorted(symbols):
            cursor = await self._event_spine.get_reconcile_cursor(account_id, symbol)
            start_time = (
                None if cursor is not None
                else self._clock() - _BACKFILL_BOOTSTRAP_LOOKBACK
            )
            trades, complete = await paginate_my_trades(
                self._venue_adapter,
                account_id,
                symbol,
                from_id=cursor,
                start_time=start_time,
            )
            if not complete:
                all_complete = False

            max_id: int | None = None
            max_trade: Any = None
            for trade in trades:
                trade_id_num = venue_trade_id_int(trade.venue_trade_id)
                if trade_id_num is None:
                    _log.warning(
                        'skipping fill with non-numeric trade id: %s %s',
                        account_id,
                        trade.venue_trade_id,
                    )
                    continue

                order = trading_state.orders.get(trade.client_order_id)
                if order is None:
                    order = trading_state.closed_orders.get(trade.client_order_id)
                if order is not None:
                    await self._apply_backfilled_fill(account_id, trade, order)

                if max_id is None or trade_id_num > max_id:
                    max_id = trade_id_num
                    max_trade = trade

            if complete and max_id is not None and max_trade is not None:
                now = self._clock()
                await self._event_spine.set_reconcile_cursor(
                    account_id,
                    symbol,
                    last_confirmed_trade_id=max_id,
                    last_confirmed_ts=max_trade.timestamp.isoformat(),
                    epoch_id=self._config.epoch_id,
                    updated_at=now.isoformat(),
                )

        return all_complete

    async def _apply_backfilled_fill(self, account_id: str, trade: Any, order: Any) -> None:
        '''
        Reconstruct a FillReceived from a backfilled trade and its local order.

        Appends through the Event Spine dedup gate and enqueues to the
        account writer only when the append is new; a duplicate append
        (already recorded) is silently skipped.

        Args:
            account_id (str): Account identifier.
            trade: Venue trade record.
            order: Local order projection carrying the command lineage.
        '''

        command_id = order.command_id
        trade_id = self._execution_manager.trade_id_for_command(command_id)
        if trade_id is None:
            return

        fill_event = FillReceived(
            account_id=account_id,
            timestamp=trade.timestamp,
            client_order_id=trade.client_order_id,
            venue_order_id=trade.venue_order_id,
            venue_trade_id=trade.venue_trade_id,
            trade_id=trade_id,
            command_id=command_id,
            symbol=trade.symbol,
            side=trade.side,
            qty=trade.qty,
            price=trade.price,
            fee=trade.fee,
            fee_asset=trade.fee_asset,
            is_maker=trade.is_maker,
        )

        seq = await self._event_spine.append(fill_event, self._config.epoch_id)
        if seq is not None:
            self._execution_manager.enqueue_ws_event(account_id, fill_event)

    async def _reconcile_terminal(
        self,
        account_id: str,
        order: Any,
        venue_order: Any,
    ) -> None:
        '''
        Emit terminal event for order that is terminal on venue but not locally.

        Args:
            account_id (str): Account identifier.
            order: Local order projection.
            venue_order: Venue order state.
        '''

        trading_state = self._execution_manager.get_trading_state(account_id)
        if trading_state is None:
            return

        ts = self._clock()
        event: OrderCanceled | OrderExpired | OrderRejected | None = None

        if venue_order.status == OrderStatus.CANCELED:
            event = OrderCanceled(
                account_id=account_id,
                timestamp=ts,
                client_order_id=order.client_order_id,
                venue_order_id=venue_order.venue_order_id,
                reason='reconciled from venue',
            )
        elif venue_order.status == OrderStatus.EXPIRED:
            event = OrderExpired(
                account_id=account_id,
                timestamp=ts,
                client_order_id=order.client_order_id,
                venue_order_id=venue_order.venue_order_id,
            )
        elif venue_order.status == OrderStatus.REJECTED:
            event = OrderRejected(
                account_id=account_id,
                timestamp=ts,
                client_order_id=order.client_order_id,
                venue_order_id=venue_order.venue_order_id,
                reason='reconciled from venue',
            )

        if event is not None:
            await self._event_spine.append(event, self._config.epoch_id)
            self._execution_manager.enqueue_ws_event(account_id, event)
            _log.info(
                'reconciled terminal state: %s %s',
                order.client_order_id,
                venue_order.status.value,
            )

    async def _on_execution_report(self, account_id: str, data: dict[str, Any]) -> None:
        '''
        Process incoming WebSocket execution report.

        Args:
            account_id (str): Account that received the report.
            data (dict[str, Any]): Raw JSON payload from WebSocket.
        '''

        if data.get('e') != 'executionReport':
            return

        if not isinstance(self._venue_adapter, BinanceAdapter):
            return

        report = self._venue_adapter.parse_execution_report(data)
        trading_state = self._execution_manager.get_trading_state(account_id)
        if trading_state is None:
            _log.warning('execution report for unknown account: %s', account_id)
            return

        parent_client_order_id = trading_state.oco_leg_parent.get(
            report.client_order_id, report.client_order_id,
        )

        order = trading_state.orders.get(parent_client_order_id)
        order_is_closed = False
        if order is None:
            order = trading_state.closed_orders.get(parent_client_order_id)
            order_is_closed = order is not None
        if order is None:
            _log.debug(
                'execution report for unknown order: %s', report.client_order_id,
            )
            return

        if order_is_closed and report.execution_type != ExecutionType.TRADE:
            _log.debug(
                'skipping terminal event for already-closed order: %s',
                report.client_order_id,
            )
            return

        event = self._convert_execution_report(account_id, report, order)
        if event is None:
            return

        seq = await self._event_spine.append(event, self._config.epoch_id)
        if seq is not None:
            self._execution_manager.enqueue_ws_event(account_id, event)

    def _convert_execution_report(  # noqa: PLR0911
        self,
        account_id: str,
        report: Any,
        order: Any,
    ) -> FillReceived | OrderCanceled | OrderRejected | OrderExpired | None:
        '''
        Convert ExecutionReport to domain event.

        Args:
            account_id (str): Account identifier.
            report: Parsed ExecutionReport.
            order: Order from TradingState.

        Returns:
            Domain event or None if no event needed.
        '''

        ts = report.transaction_time

        if report.execution_type == ExecutionType.TRADE:
            if report.venue_trade_id is None:
                _log.warning('TRADE report missing venue_trade_id')
                return None
            if not report.commission_asset:
                _log.warning('TRADE report missing commission_asset')
                return None
            trade_id = self._execution_manager.trade_id_for_command(order.command_id)
            if trade_id is None:
                _log.warning(
                    'TRADE report has no trade_id mapping for command_id=%s',
                    order.command_id,
                )
                return None
            return FillReceived(
                account_id=account_id,
                timestamp=ts,
                client_order_id=order.client_order_id,
                venue_order_id=report.venue_order_id,
                venue_trade_id=report.venue_trade_id,
                trade_id=trade_id,
                command_id=order.command_id,
                symbol=report.symbol,
                side=report.side,
                qty=report.last_filled_qty,
                price=report.last_filled_price,
                fee=report.commission,
                fee_asset=report.commission_asset,
                is_maker=report.is_maker,
            )

        if report.execution_type == ExecutionType.CANCELED:
            return OrderCanceled(
                account_id=account_id,
                timestamp=ts,
                client_order_id=order.client_order_id,
                venue_order_id=report.venue_order_id,
                reason='canceled via WebSocket',
            )

        if report.execution_type == ExecutionType.REJECTED:
            return OrderRejected(
                account_id=account_id,
                timestamp=ts,
                client_order_id=order.client_order_id,
                venue_order_id=report.venue_order_id,
                reason=report.reject_reason or 'rejected via WebSocket',
            )

        if report.execution_type == ExecutionType.EXPIRED:
            return OrderExpired(
                account_id=account_id,
                timestamp=ts,
                client_order_id=order.client_order_id,
                venue_order_id=report.venue_order_id,
            )

        return None

    def register_account(self, account_id: str) -> None:
        '''Register account in venue + execution via inbound facade.'''

        self._require_started()
        self._inbound.register_account(account_id)
        self._managed_accounts.add(account_id)

    async def unregister_account(self, account_id: str) -> None:
        '''Unregister account in execution + venue via inbound facade.'''

        self._require_started()

        stream = self._user_streams.pop(account_id, None)
        if stream is not None:
            try:
                await stream.close()
            except Exception:  # noqa: BLE001
                _log.exception('error closing user stream: %s', account_id)

        await self._inbound.unregister_account(account_id)
        self._managed_accounts.discard(account_id)
        self._ready_accounts.discard(account_id)

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
        '''Submit trade command through inbound facade.'''

        if self._stopping:
            msg = 'Trading is shutting down, new commands rejected'
            raise RuntimeError(msg)
        self._require_account_ready(account_id)
        return await self._inbound.submit_command(
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
            strategy_id=strategy_id,
            command_id=command_id,
        )

    def submit_abort(self, abort: TradeAbort) -> None:
        '''Submit trade abort through inbound facade.'''

        if self._stopping:
            msg = 'Trading is shutting down, new aborts rejected'
            raise RuntimeError(msg)
        self._require_account_ready(abort.account_id)
        self._inbound.submit_abort(abort)

    def submit_modify(self, modify: TradeModify) -> None:
        '''Submit trade amend through inbound facade.'''

        if self._stopping:
            msg = 'Trading is shutting down, new modifies rejected'
            raise RuntimeError(msg)
        self._require_account_ready(modify.account_id)
        self._inbound.submit_modify(modify)

    async def quiesce(self, account_id: str) -> None:
        '''Wait until an account's queued commands are fully processed.

        Delegates to `ExecutionManager.quiesce`; used by deterministic
        replay to settle a bar's submissions, fills, and outcome
        dispatch before the clock advances.

        Args:
            account_id: Account whose command queue to drain.
        '''

        await self._execution_manager.quiesce(account_id)

    async def get_health_snapshot(self, account_id: str) -> HealthSnapshot:
        '''Return a HealthSnapshot for an account.

        Body is synchronous (snapshot composition is in-memory). The method
        is declared `async` so a Manager thread can dispatch the call
        across the asyncio loop boundary via
        asyncio.run_coroutine_threadsafe(trading.get_health_snapshot(...),
        trading.loop) without blocking the loop.

        Unlike submit_command, submit_abort, and submit_modify, this does not
        require the account to be ready: health is intentionally pollable across the
        whole lifecycle (the underlying adapter returns a default zeroed
        snapshot for unknown accounts) so a Manager can observe degradation
        before the account is fully wired.

        Args:
            account_id: Account whose snapshot is requested.

        Returns:
            HealthSnapshot: Latest known metrics. Returns default (zero)
                values when no samples have been recorded yet.

        Raises:
            RuntimeError: If Trading.start() has not been awaited.
        '''

        self._require_started()
        return self._venue_adapter.get_health_snapshot(account_id)

    def get_health_snapshot_sync(self, account_id: str) -> HealthSnapshot:
        '''Return a HealthSnapshot without crossing the asyncio loop.

        The async `get_health_snapshot` exists so a Manager thread can
        dispatch via `asyncio.run_coroutine_threadsafe`. The body is
        already synchronous — `BinanceAdapter.get_health_snapshot` reads
        its trackers under a `threading.Lock` so direct cross-thread
        reads are safe. Callers on the per-account `HealthLoop` thread
        use this entry point to avoid scheduling a coroutine on a busy
        loop only to consume an in-memory snapshot.

        Args:
            account_id: Account whose snapshot is requested.

        Returns:
            HealthSnapshot: Latest known metrics.

        Raises:
            RuntimeError: If `Trading.start()` has not been awaited.
        '''

        self._require_started()
        return self._venue_adapter.get_health_snapshot(account_id)

    def pull_positions(self, account_id: str) -> dict[tuple[str, str], Position]:
        '''Pull detached positions snapshot through inbound facade.'''

        self._require_started()
        return self._inbound.pull_positions(account_id)
