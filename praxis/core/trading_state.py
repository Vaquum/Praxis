'''
Represent in-memory projection of the Event Spine.

TradingState is rebuilt by replaying events from genesis. Each
apply() call updates positions and orders in O(1). This is not
an independent store — it is a derived view of the event log.
'''

from __future__ import annotations

import logging
from decimal import Decimal

from praxis.core.domain.enums import OrderStatus
from praxis.core.domain.events import (
    CommandAccepted,
    Event,
    FillReceived,
    OrderAcked,
    OrderCanceled,
    OrderExpired,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    TradeClosed,
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
        elif isinstance(event, OrderRejected):
            self._on_order_rejected(event)
        elif isinstance(event, OrderCanceled):
            self._on_order_canceled(event)
        elif isinstance(event, OrderExpired):
            self._on_order_expired(event)
        elif isinstance(event, TradeClosed):
            self._on_trade_closed(event)
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
            filled_qty=_ZERO,
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
        order.updated_at = event.timestamp

        if order.filled_qty >= order.qty:
            order.status = OrderStatus.FILLED
            self._close_order(event.client_order_id)
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

    def _update_position_on_fill(self, event: FillReceived) -> None:

        '''Update or create position from fill.'''

        key = (event.trade_id, event.account_id)
        pos = self.positions.get(key)

        if pos is None:
            self.positions[key] = Position(
                account_id=event.account_id,
                trade_id=event.trade_id,
                symbol=event.symbol,
                side=event.side,
                qty=event.qty,
                avg_entry_price=event.price,
            )
            return

        if event.side == pos.side:
            new_qty = pos.qty + event.qty
            pos.avg_entry_price = (
                (pos.qty * pos.avg_entry_price + event.qty * event.price) / new_qty
            )
            pos.qty = new_qty
        else:
            pos.qty -= event.qty
            if pos.qty < _ZERO:
                _log.warning(
                    'position qty went negative: trade_id=%s account=%s qty=%s',
                    event.trade_id,
                    event.account_id,
                    pos.qty,
                )

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
        pos = self.positions.pop(key, None)
        if pos is None:
            _log.warning(
                'no position for TradeClosed: trade_id=%s account=%s',
                event.trade_id,
                self.account_id,
            )

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
