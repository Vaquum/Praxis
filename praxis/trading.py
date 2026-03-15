from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from praxis.core.execution_manager import ExecutionManager
from praxis.core.domain.enums import (
    ExecutionMode,
    ExecutionType,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
)
from praxis.core.domain.position import Position
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.events import (
    FillReceived,
    OrderCanceled,
    OrderExpired,
    OrderRejected,
)
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.binance_ws import BinanceUserStream
from praxis.infrastructure.venue_adapter import NotFoundError, VenueAdapter, VenueError
from praxis.trading_config import TradingConfig
from praxis.trading_inbound import TradingInbound

__all__ = ['Trading']

_log = logging.getLogger(__name__)
_TERMINAL_ORDER_STATUSES = frozenset({
    OrderStatus.FILLED,
    OrderStatus.CANCELED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
})

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
    '''

    def __init__(
        self,
        *,
        config: TradingConfig,
        event_spine: EventSpine,
        venue_adapter: VenueAdapter | None = None,
    ) -> None:
        '''Compose core trading dependencies and manager-facing facade.'''

        self._config = config
        self._event_spine = event_spine
        if venue_adapter is None:
            self._venue_adapter = cast(
                VenueAdapter,
                BinanceAdapter(
                    base_url=config.venue_rest_url,
                    ws_base_url=config.venue_ws_url,
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
        )
        self._inbound = TradingInbound(
            execution_manager=self._execution_manager,
            venue_adapter=self._venue_adapter,
            account_credentials=config.account_credentials,
        )
        self._started = False
        self._managed_accounts: set[str] = set()
        self._user_streams: dict[str, BinanceUserStream] = {}

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

    async def start(self) -> None:
        '''Initialize runtime and execute per-account startup sequence.'''

        if self._started:
            return

        await self._event_spine.ensure_schema()

        for account_id in self._config.account_credentials:
            self._inbound.register_account(account_id)
            self._managed_accounts.add(account_id)
            await self._startup_account(account_id)

        self._started = True

    async def _startup_account(self, account_id: str) -> None:
        '''
        Execute per-account startup phases in required order.

        Args:
            account_id (str): Account identifier to start up.
        '''

        all_events = await self._event_spine.read(self._config.epoch_id)
        account_events = [
            (seq, event) for seq, event in all_events
            if event.account_id == account_id
        ]
        self._execution_manager.replay_events(account_id, account_events)

        symbols = self._execution_manager.active_symbols(account_id)
        if symbols:
            await self._venue_adapter.load_filters(sorted(symbols))

        if isinstance(self._venue_adapter, BinanceAdapter):
            adapter = self._venue_adapter

            async def on_message(data: dict[str, Any]) -> None:
                await self._on_execution_report(account_id, data)

            stream = BinanceUserStream(
                adapter=adapter,
                account_id=account_id,
                on_message=on_message,
            )
            await stream.initiate_connection()
            self._user_streams[account_id] = stream

        await self._reconcile_account(account_id)

    async def stop(self) -> None:
        '''Stop runtime and cleanup managed account registrations.'''

        if not self._started:
            return

        for account_id, stream in list(self._user_streams.items()):
            try:
                await stream.close()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                _log.exception('error closing user stream: %s', account_id)
            self._user_streams.pop(account_id, None)

        first_error: Exception | None = None
        for account_id in sorted(self._managed_accounts):
            try:
                await self._inbound.unregister_account(account_id)
                self._managed_accounts.discard(account_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                if first_error is None:
                    first_error = exc

        if first_error is not None:
            raise first_error

        self._started = False

    def _require_started(self) -> None:
        if not self._started:
            msg = 'Trading.start() must be awaited before using trading operations'
            raise RuntimeError(msg)

    async def _reconcile_account(self, account_id: str) -> None:
        '''
        Reconcile projected state against venue for open orders.

        Args:
            account_id (str): Account identifier to reconcile.
        '''

        runtime = self._execution_manager._accounts.get(account_id)
        if runtime is None:
            return

        for client_order_id, order in list(runtime.trading_state.orders.items()):
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

        runtime = self._execution_manager._accounts.get(account_id)
        if runtime is None:
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
        trade_id = self._execution_manager._command_trade_ids.get(
            command_id, command_id,
        )

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
                runtime.trading_state.apply(fill_event)
                _log.info(
                    'reconciled fill: %s %s',
                    order.client_order_id,
                    trade.venue_trade_id,
                )

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

        runtime = self._execution_manager._accounts.get(account_id)
        if runtime is None:
            return

        ts = order.updated_at
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
            runtime.trading_state.apply(event)
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

        report = self._venue_adapter._parse_execution_report(data)
        runtime = self._execution_manager._accounts.get(account_id)
        if runtime is None:
            _log.warning('execution report for unknown account: %s', account_id)
            return

        order = runtime.trading_state.orders.get(report.client_order_id)
        if order is None:
            order = runtime.trading_state.closed_orders.get(report.client_order_id)
        if order is None:
            _log.debug(
                'execution report for unknown order: %s', report.client_order_id,
            )
            return

        event = self._convert_execution_report(account_id, report, order)
        if event is None:
            return

        seq = await self._event_spine.append(event, self._config.epoch_id)
        if seq is not None:
            runtime.trading_state.apply(event)

    def _convert_execution_report(
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
            return FillReceived(
                account_id=account_id,
                timestamp=ts,
                client_order_id=report.client_order_id,
                venue_order_id=report.venue_order_id,
                venue_trade_id=report.venue_trade_id,
                trade_id=self._execution_manager._command_trade_ids.get(order.command_id, order.command_id),
                command_id=order.command_id,
                symbol=report.symbol,
                side=report.side,
                qty=report.last_filled_qty,
                price=report.last_filled_price,
                fee=report.commission,
                fee_asset=report.commission_asset or '',
                is_maker=report.is_maker,
            )

        if report.execution_type == ExecutionType.CANCELED:
            return OrderCanceled(
                account_id=account_id,
                timestamp=ts,
                client_order_id=report.client_order_id,
                venue_order_id=report.venue_order_id,
                reason='canceled via WebSocket',
            )

        if report.execution_type == ExecutionType.REJECTED:
            return OrderRejected(
                account_id=account_id,
                timestamp=ts,
                client_order_id=report.client_order_id,
                venue_order_id=report.venue_order_id,
                reason=report.reject_reason or 'rejected via WebSocket',
            )

        if report.execution_type == ExecutionType.EXPIRED:
            return OrderExpired(
                account_id=account_id,
                timestamp=ts,
                client_order_id=report.client_order_id,
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
        await self._inbound.unregister_account(account_id)
        self._managed_accounts.discard(account_id)

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
        '''Submit trade command through inbound facade.'''

        self._require_started()
        return await self._inbound.submit_command(
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

    def submit_abort(self, abort: TradeAbort) -> None:
        '''Submit trade abort through inbound facade.'''

        self._require_started()
        self._inbound.submit_abort(abort)

    def pull_positions(self, account_id: str) -> dict[tuple[str, str], Position]:
        '''Pull detached positions snapshot through inbound facade.'''

        self._require_started()
        return self._inbound.pull_positions(account_id)
