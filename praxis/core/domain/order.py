'''
Order dataclass representing a trading order through its lifecycle.

Orders are mutable: status and filled_qty change as the venue reports
events. Mutation logic belongs in Trading State, not here.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType


__all__ = ['Order']

_TERMINAL_STATUSES: frozenset[OrderStatus] = frozenset({
    OrderStatus.FILLED,
    OrderStatus.CANCELED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
})


@dataclass
class Order:
    '''
    A trading order tracked from submission through terminal state.

    Args:
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str | None): Venue-assigned identifier, None until acknowledged.
        account_id (str): Account that owns the order.
        command_id (str): Originating command identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Order direction.
        order_type (OrderType): Order type.
        qty (Decimal): Requested quantity.
        filled_qty (Decimal): Cumulative filled quantity.
        price (Decimal | None): Limit price, None for market orders.
        stop_price (Decimal | None): Stop trigger price, None when not applicable.
        status (OrderStatus): Current lifecycle state.
        created_at (datetime): Order creation time.
        updated_at (datetime): Last state change time.
    '''

    client_order_id: str
    venue_order_id: str | None
    account_id: str
    command_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    filled_qty: Decimal
    price: Decimal | None
    stop_price: Decimal | None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    @property
    def is_terminal(self) -> bool:
        '''Return True if the order is in a terminal lifecycle state.'''

        return self.status in _TERMINAL_STATUSES

    @property
    def remaining_qty(self) -> Decimal:
        '''Return the unfilled quantity.'''

        return self.qty - self.filled_qty
