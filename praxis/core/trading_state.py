'''
Represent in-memory projection of the Event Spine.

TradingState is rebuilt by replaying events from genesis. Each
apply() call updates positions and orders in O(1). This is not
an independent store — it is a derived view of the event log.
'''

from __future__ import annotations

import copy
import logging
import threading
from decimal import Decimal

from praxis.core.domain.enums import OrderStatus
from praxis.core.domain.events import (
    CommandAccepted,
    Event,
    FillReceived,
    OrderAcked,
    OrderCanceled,
    OrderExpired,
    OrderQuoteNativeFilled,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    OutcomeAcked,
    OutcomeDeliveryContextRecorded,
    TradeClosed,
    TradeOutcomeProduced,
)
from praxis.core.domain.order import Order
from praxis.core.domain.position import Position

__all__ = ['TradingState']

_log = logging.getLogger(__name__)

_ZERO = Decimal(0)


class TradingState:

    '''
    Represent in-memory projection of positions and orders from event stream.

    Args:
        account_id (str): Account this projection belongs to.
    '''

    def __init__(self, account_id: str) -> None:

        if not account_id:
            msg = 'TradingState.account_id must be a non-empty string'
            raise ValueError(msg)
        self.account_id = account_id
        self.positions: dict[tuple[str, str], Position] = {}
        self.orders: dict[str, Order] = {}
        self.closed_orders: dict[str, Order] = {}
        self.trade_strategy_ids: dict[str, str] = {}
        self._positions_lock = threading.Lock()

    def snapshot_positions(self) -> dict[tuple[str, str], Position]:

        '''Return a thread-safe shallow snapshot of `positions`.

        Iteration of `self.positions` happens under `_positions_lock` so
        a concurrent insert or delete on the loop thread cannot raise
        `RuntimeError: dictionary changed size during iteration`. Each
        value is `copy.copy`'d so the caller can safely read field
        values without observing a mid-update mutation.
        '''

        with self._positions_lock:
            return {
                key: copy.copy(position)
                for key, position in self.positions.items()
            }

    def apply(self, event: Event) -> None:

        '''
        Apply a single event to update projection state.

        Args:
            event (Event): Domain event to project.
        '''

        if isinstance(event, CommandAccepted):
            return

        if isinstance(event, OrderSubmitIntent):
            self._on_order_submit_intent(event)
        elif isinstance(event, OrderSubmitted):
            self._on_order_submitted(event)
        elif isinstance(event, OrderSubmitFailed):
            self._on_order_submit_failed(event)
        elif isinstance(event, OrderAcked):
            self._on_order_acked(event)
        elif isinstance(event, FillReceived):
            self._on_fill_received(event)
        elif isinstance(event, OrderQuoteNativeFilled):
            self._on_order_quote_native_filled(event)
        elif isinstance(event, OrderRejected):
            self._on_order_rejected(event)
        elif isinstance(event, OrderCanceled):
            self._on_order_canceled(event)
        elif isinstance(event, OrderExpired):
            self._on_order_expired(event)
        elif isinstance(event, TradeClosed):
            self._on_trade_closed(event)
        elif isinstance(event, TradeOutcomeProduced):
            _log.debug(
                'trade outcome produced: command_id=%s trade_id=%s account=%s',
                event.command_id,
                event.trade_id,
                self.account_id,
            )
        elif isinstance(event, OutcomeAcked):
            _log.debug(
                'outcome acked: outcome_id=%s account=%s',
                event.outcome_id,
                self.account_id,
            )
        elif isinstance(event, OutcomeDeliveryContextRecorded):
            return
        else:
            _log.warning(
                'unhandled event type in apply: %s account=%s',
                type(event).__name__,
                self.account_id,
            )

    def _get_order(self, event_type: str, client_order_id: str) -> Order | None:

        '''
        Return open order by client_order_id or None with a warning.

        Args:
            event_type (str): Name of the calling event for log context.
            client_order_id (str): Order identifier to look up.

        Returns:
            Order | None: The open order, or None if not found.
        '''

        order = self.orders.get(client_order_id)
        if order is None:
            _log.warning(
                'unknown order in %s: client_order_id=%s account=%s',
                event_type,
                client_order_id,
                self.account_id,
            )

        return order

    def _on_order_submit_intent(self, event: OrderSubmitIntent) -> None:

        '''Create a new order in SUBMITTING state.'''

        self.orders[event.client_order_id] = Order(
            client_order_id=event.client_order_id,
            venue_order_id=None,
            account_id=event.account_id,
            command_id=event.command_id,
            symbol=event.symbol,
            side=event.side,
            order_type=event.order_type,
            qty=event.qty,
            quote_qty=event.quote_qty,
            filled_qty=_ZERO,
            cumulative_notional=_ZERO,
            price=event.price,
            stop_price=event.stop_price,
            status=OrderStatus.SUBMITTING,
            created_at=event.timestamp,
            updated_at=event.timestamp,
        )

    def _on_order_submitted(self, event: OrderSubmitted) -> None:

        '''Update order to OPEN with venue identifier.'''

        order = self._get_order('OrderSubmitted', event.client_order_id)
        if order is None:
            return

        order.venue_order_id = event.venue_order_id
        order.status = OrderStatus.OPEN
        order.updated_at = event.timestamp

    def _on_order_submit_failed(self, event: OrderSubmitFailed) -> None:

        '''Update order to REJECTED and close it.'''

        order = self._get_order('OrderSubmitFailed', event.client_order_id)
        if order is None:
            return

        order.status = OrderStatus.REJECTED
        order.updated_at = event.timestamp
        self._close_order(event.client_order_id)

    def _on_order_acked(self, event: OrderAcked) -> None:

        '''Update order venue identifier, promote to OPEN if still SUBMITTING.'''

        order = self._get_order('OrderAcked', event.client_order_id)
        if order is None:
            return

        order.venue_order_id = event.venue_order_id
        if order.status == OrderStatus.SUBMITTING:
            order.status = OrderStatus.OPEN
        order.updated_at = event.timestamp

    def _on_fill_received(self, event: FillReceived) -> None:

        '''Apply fill to order and position.'''

        self._update_order_on_fill(event)
        self._update_position_on_fill(event)

    def _update_order_on_fill(self, event: FillReceived) -> None:

        '''Update order filled quantity and status.'''

        order = self._get_order('FillReceived', event.client_order_id)
        if order is None:
            return

        order.filled_qty += event.qty
        order.cumulative_notional += event.qty * event.price
        order.updated_at = event.timestamp

        if order.qty is None:
            order.status = OrderStatus.PARTIALLY_FILLED
        elif order.filled_qty >= order.qty:
            order.status = OrderStatus.FILLED
            self._close_order(event.client_order_id)
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

    def _update_position_on_fill(self, event: FillReceived) -> None:

        '''Update or create position from fill.'''

        key = (event.trade_id, event.account_id)

        with self._positions_lock:
            pos = self.positions.get(key)

            if pos is None:
                self.positions[key] = Position(
                    account_id=event.account_id,
                    trade_id=event.trade_id,
                    symbol=event.symbol,
                    side=event.side,
                    qty=event.qty,
                    avg_entry_price=event.price,
                    strategy_id=self.trade_strategy_ids.get(event.trade_id),
                )
                return

            if event.side == pos.side:
                new_qty = pos.qty + event.qty
                pos.avg_entry_price = (
                    (pos.qty * pos.avg_entry_price + event.qty * event.price) / new_qty
                )
                pos.qty = new_qty
            else:
                new_qty = pos.qty - event.qty
                if new_qty < _ZERO:
                    _log.warning(
                        'position qty went negative: trade_id=%s account=%s qty=%s',
                        event.trade_id,
                        event.account_id,
                        new_qty,
                    )
                    new_qty = _ZERO
                pos.qty = new_qty
                if new_qty == _ZERO:
                    del self.positions[key]
                    self.trade_strategy_ids.pop(event.trade_id, None)

    def _on_order_rejected(self, event: OrderRejected) -> None:

        '''Update order to REJECTED and close it.'''

        order = self._get_order('OrderRejected', event.client_order_id)
        if order is None:
            return

        if event.venue_order_id is not None:
            order.venue_order_id = event.venue_order_id
        order.status = OrderStatus.REJECTED
        order.updated_at = event.timestamp
        self._close_order(event.client_order_id)

    def _on_order_canceled(self, event: OrderCanceled) -> None:

        '''Update order to CANCELED and close it.'''

        order = self._get_order('OrderCanceled', event.client_order_id)
        if order is None:
            return

        if event.venue_order_id is not None:
            order.venue_order_id = event.venue_order_id
        order.status = OrderStatus.CANCELED
        order.updated_at = event.timestamp
        self._close_order(event.client_order_id)

    def _on_order_expired(self, event: OrderExpired) -> None:

        '''Update order to EXPIRED and close it.'''

        order = self._get_order('OrderExpired', event.client_order_id)
        if order is None:
            return

        if event.venue_order_id is not None:
            order.venue_order_id = event.venue_order_id
        order.status = OrderStatus.EXPIRED
        order.updated_at = event.timestamp
        self._close_order(event.client_order_id)

    def _on_trade_closed(self, event: TradeClosed) -> None:

        '''Remove position for the closed trade.'''

        key = (event.trade_id, self.account_id)
        with self._positions_lock:
            pos = self.positions.pop(key, None)
        self.trade_strategy_ids.pop(event.trade_id, None)
        if pos is None:
            _log.debug(
                'no position for TradeClosed (already cleaned up by '
                'prior fill in same batch — expected on the WS-driven '
                'LIMIT EXIT happy path): trade_id=%s account=%s',
                event.trade_id,
                self.account_id,
            )

    def _on_order_quote_native_filled(
        self,
        event: OrderQuoteNativeFilled,
    ) -> None:

        '''Promote a quote-native order to FILLED.

        Qty-native orders self-terminate in `_update_order_on_fill`
        when cumulative `filled_qty` reaches the requested base `qty`.
        Quote-native orders have no base target, so the venue's
        per-response `status == FILLED` flag is the terminal signal
        — `ExecutionManager` appends this event after the last
        immediate fill so spine replay reconstructs the terminal
        state instead of leaving the order stranded
        `PARTIALLY_FILLED`.
        '''

        if event.client_order_id in self.closed_orders:
            return

        order = self._get_order(
            'OrderQuoteNativeFilled', event.client_order_id,
        )
        if order is None:
            return

        order.status = OrderStatus.FILLED
        order.updated_at = event.timestamp
        self._close_order(event.client_order_id)

    def _close_order(self, client_order_id: str) -> None:

        '''Move order from active to closed.'''

        order = self.orders.pop(client_order_id, None)
        if order is None:
            _log.warning(
                'close_order called for unknown order: client_order_id=%s account=%s',
                client_order_id,
                self.account_id,
            )
            return

        self.closed_orders[client_order_id] = order
