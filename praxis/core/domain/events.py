'''
Event type dataclasses for the Praxis Trading sub-system.

Represent domain events consumed by TradingState.apply(). Each event
is an immutable fact produced by the execution pipeline and projected
onto in-memory state. Only event types needed for position and order
tracking are defined here; later WPs add remaining types.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TypeAlias

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.enums import OrderSide, OrderType

__all__ = [
    'CommandAccepted',
    'Event',
    'FillReceived',
    'OrderAcked',
    'OrderCanceled',
    'OrderExpired',
    'OrderRejected',
    'OrderSubmitFailed',
    'OrderSubmitIntent',
    'OrderSubmitted',
    'TradeClosed',
]

_ZERO = Decimal(0)


@dataclass(frozen=True)
class _EventBase:

    '''
    Represent shared fields for all domain events.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
    '''

    account_id: str
    timestamp: datetime

    def __post_init__(self) -> None:

        name = type(self).__name__
        _require_str(name, 'account_id', self.account_id)

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            msg = f'{name}.timestamp must be timezone-aware'
            raise ValueError(msg)


@dataclass(frozen=True)
class CommandAccepted(_EventBase):

    '''
    Represent acceptance of a TradeCommand into the execution pipeline.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Originating TradeCommand identifier.
        trade_id (str): Trade correlation identifier.
    '''

    command_id: str
    trade_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'trade_id', self.trade_id)


@dataclass(frozen=True)
class OrderSubmitIntent(_EventBase):

    '''
    Represent intent to submit an order before venue acknowledgement.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Originating TradeCommand identifier.
        trade_id (str): Trade correlation identifier.
        client_order_id (str): Deterministic client order identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Order direction.
        order_type (OrderType): Order type.
        qty (Decimal): Order quantity, must be positive.
        price (Decimal | None): Limit price, must be positive when set.
        stop_price (Decimal | None): Stop trigger price, must be positive when set.
    '''

    command_id: str
    trade_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'symbol', self.symbol)

        if self.qty <= _ZERO:
            msg = 'OrderSubmitIntent.qty must be positive'
            raise ValueError(msg)

        if self.price is not None and self.price <= _ZERO:
            msg = 'OrderSubmitIntent.price must be positive'
            raise ValueError(msg)

        if self.stop_price is not None and self.stop_price <= _ZERO:
            msg = 'OrderSubmitIntent.stop_price must be positive'
            raise ValueError(msg)


@dataclass(frozen=True)
class OrderSubmitted(_EventBase):

    '''
    Represent successful order submission to the venue.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str): Venue-assigned order identifier.
    '''

    client_order_id: str
    venue_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id)


@dataclass(frozen=True)
class OrderSubmitFailed(_EventBase):

    '''
    Represent a failed order submission attempt.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        reason (str): Failure reason from venue or internal logic.
    '''

    client_order_id: str
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'reason', self.reason)


@dataclass(frozen=True)
class OrderAcked(_EventBase):

    '''
    Represent venue acknowledgement of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str): Venue-assigned order identifier.
    '''

    client_order_id: str
    venue_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id)


@dataclass(frozen=True)
class FillReceived(_EventBase):

    '''
    Represent a fill execution reported by the venue.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str): Venue-assigned order identifier.
        venue_trade_id (str): Venue-assigned unique trade identifier.
        trade_id (str): Trade correlation identifier.
        command_id (str): Originating TradeCommand identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Fill direction.
        qty (Decimal): Filled quantity, must be positive.
        price (Decimal): Execution price, must be positive.
        fee (Decimal): Transaction fee, must be non-negative.
        fee_asset (str): Asset in which the fee is denominated.
        is_maker (bool): Whether the fill was a maker trade.
    '''

    client_order_id: str
    venue_order_id: str
    venue_trade_id: str
    trade_id: str
    command_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    fee: Decimal
    fee_asset: str
    is_maker: bool

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id)
        _require_str(name, 'venue_trade_id', self.venue_trade_id)
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'symbol', self.symbol)
        _require_str(name, 'fee_asset', self.fee_asset)

        if self.qty <= _ZERO:
            msg = 'FillReceived.qty must be positive'
            raise ValueError(msg)

        if self.price <= _ZERO:
            msg = 'FillReceived.price must be positive'
            raise ValueError(msg)

        if self.fee < _ZERO:
            msg = 'FillReceived.fee must be non-negative'
            raise ValueError(msg)


@dataclass(frozen=True)
class OrderRejected(_EventBase):

    '''
    Represent a venue rejection of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str | None): Venue-assigned order identifier, if available.
        reason (str): Rejection reason from venue.
    '''

    client_order_id: str
    venue_order_id: str | None
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id, optional=True)
        _require_str(name, 'reason', self.reason)


@dataclass(frozen=True)
class OrderCanceled(_EventBase):

    '''
    Represent cancellation of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str | None): Venue-assigned order identifier, if available.
        reason (str | None): Cancellation reason, if available.
    '''

    client_order_id: str
    venue_order_id: str | None
    reason: str | None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id, optional=True)
        _require_str(name, 'reason', self.reason, optional=True)


@dataclass(frozen=True)
class OrderExpired(_EventBase):

    '''
    Represent expiration of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str | None): Venue-assigned order identifier, if available.
    '''

    client_order_id: str
    venue_order_id: str | None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id, optional=True)


@dataclass(frozen=True)
class TradeClosed(_EventBase):

    '''
    Represent closure of a trade lifecycle.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        trade_id (str): Trade correlation identifier.
        command_id (str): Originating TradeCommand identifier.
    '''

    trade_id: str
    command_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'command_id', self.command_id)


Event: TypeAlias = (
    CommandAccepted
    | OrderSubmitIntent
    | OrderSubmitted
    | OrderSubmitFailed
    | OrderAcked
    | FillReceived
    | OrderRejected
    | OrderCanceled
    | OrderExpired
    | TradeClosed
)
