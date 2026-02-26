'''
Fill dataclass representing a single execution event from a venue.

Fills are immutable facts: once received from the exchange, no field
changes. The dedup_key property supports fill deduplication per RFC.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.enums import OrderSide


__all__ = ['Fill']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class Fill:

    '''
    A single order execution (partial or full) reported by the venue.

    Args:
        venue_trade_id (str): Venue-assigned unique trade identifier.
        venue_order_id (str): Venue-assigned order identifier.
        client_order_id (str): Deterministic client order identifier.
        account_id (str): Account that owns the order.
        trade_id (str): Manager correlation identifier.
        command_id (str): Originating command identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Fill direction.
        qty (Decimal): Filled quantity, must be positive.
        price (Decimal): Execution price, must be positive.
        fee (Decimal): Transaction fee charged, must be non-negative.
        fee_asset (str): Asset in which the fee is denominated.
        is_maker (bool): Whether the fill was a maker trade.
        timestamp (datetime): Venue-reported execution time, must be timezone-aware.
    '''

    venue_trade_id: str
    venue_order_id: str
    client_order_id: str
    account_id: str
    trade_id: str
    command_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    fee: Decimal
    fee_asset: str
    is_maker: bool
    timestamp: datetime

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in (
            'venue_order_id', 'client_order_id',
            'account_id', 'trade_id', 'command_id', 'symbol', 'fee_asset',
        ):
            _require_str('Fill', field, getattr(self, field))

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            msg = 'Fill.timestamp must be timezone-aware'
            raise ValueError(msg)
        if self.qty <= _ZERO:
            msg = 'Fill.qty must be positive'
            raise ValueError(msg)
        if self.price <= _ZERO:
            msg = 'Fill.price must be positive'
            raise ValueError(msg)
        if self.fee < _ZERO:
            msg = 'Fill.fee must be non-negative'
            raise ValueError(msg)

    @property
    def dedup_key(self) -> str | tuple[str, Decimal, Decimal, datetime]:

        '''
        Return the deduplication key for this fill.

        Primary key is venue_trade_id when available. Falls back to
        the composite (venue_order_id, price, qty, timestamp) per RFC.
        '''

        if self.venue_trade_id:
            return self.venue_trade_id
        return (self.venue_order_id, self.price, self.qty, self.timestamp)
