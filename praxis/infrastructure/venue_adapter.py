'''
Venue adapter protocol and response types for exchange interaction.

Define the venue-agnostic interface consumed by Execution Manager,
Reconciliation Engine, and Health Monitor. Response dataclasses
normalize venue-specific data into internal domain types.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType


__all__ = [
    'AuthenticationError',
    'BalanceEntry',
    'CancelResult',
    'ImmediateFill',
    'NotFoundError',
    'OrderRejectedError',
    'RateLimitError',
    'SubmitResult',
    'SymbolFilters',
    'TransientError',
    'VenueAdapter',
    'VenueError',
    'VenueOrder',
    'VenueTrade',
]


@dataclass(frozen=True)
class ImmediateFill:

    '''
    Represent a fill returned inline with an order submission response.

    Args:
        venue_trade_id (str): Venue-assigned unique trade identifier
        qty (Decimal): Filled quantity
        price (Decimal): Execution price
        fee (Decimal): Transaction fee charged
        fee_asset (str): Asset in which the fee is denominated
        is_maker (bool): Whether the fill was a maker trade
    '''

    venue_trade_id: str
    qty: Decimal
    price: Decimal
    fee: Decimal
    fee_asset: str
    is_maker: bool


@dataclass(frozen=True)
class SubmitResult:

    '''
    Represent the venue response to an order submission.

    Args:
        venue_order_id (str): Venue-assigned order identifier
        status (OrderStatus): Order status after submission
        immediate_fills (list[ImmediateFill]): Fills returned inline with the submission response
    '''

    venue_order_id: str
    status: OrderStatus
    immediate_fills: list[ImmediateFill]


@dataclass(frozen=True)
class CancelResult:

    '''
    Represent the venue response to an order cancellation.

    Args:
        venue_order_id (str): Venue-assigned order identifier
        status (OrderStatus): Order status after cancellation
    '''

    venue_order_id: str
    status: OrderStatus


@dataclass(frozen=True)
class VenueOrder:

    '''
    Represent an order as reported by the venue on query.

    Args:
        venue_order_id (str): Venue-assigned order identifier
        client_order_id (str): Deterministic client order identifier
        status (OrderStatus): Current order lifecycle status
        symbol (str): Trading pair symbol
        side (OrderSide): Order direction
        order_type (OrderType): Order type
        qty (Decimal): Original order quantity
        filled_qty (Decimal): Cumulative filled quantity
        price (Decimal | None): Limit price, None for market orders
    '''

    venue_order_id: str
    client_order_id: str
    status: OrderStatus
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    filled_qty: Decimal
    price: Decimal | None


@dataclass(frozen=True)
class VenueTrade:

    '''
    Represent a historical trade record from the venue.

    Args:
        venue_trade_id (str): Venue-assigned unique trade identifier
        venue_order_id (str): Venue-assigned order identifier
        client_order_id (str): Deterministic client order identifier
        symbol (str): Trading pair symbol
        side (OrderSide): Trade direction
        qty (Decimal): Traded quantity
        price (Decimal): Execution price
        fee (Decimal): Transaction fee charged
        fee_asset (str): Asset in which the fee is denominated
        is_maker (bool): Whether the trade was a maker trade
        timestamp (datetime): Venue-reported execution time
    '''

    venue_trade_id: str
    venue_order_id: str
    client_order_id: str
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

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            msg = 'VenueTrade.timestamp must be timezone-aware'
            raise ValueError(msg)


@dataclass(frozen=True)
class BalanceEntry:

    '''
    Represent a single asset balance from the venue account.

    Args:
        asset (str): Asset symbol
        free (Decimal): Available balance
        locked (Decimal): Balance locked in open orders
    '''

    asset: str
    free: Decimal
    locked: Decimal


@dataclass(frozen=True)
class SymbolFilters:

    '''
    Represent venue-imposed trading filters for a symbol.

    Args:
        symbol (str): Trading pair symbol
        tick_size (Decimal): Minimum price increment
        lot_step (Decimal): Minimum quantity increment
        lot_min (Decimal): Minimum order quantity
        lot_max (Decimal): Maximum order quantity
        min_notional (Decimal): Minimum order value (price * qty)
    '''

    symbol: str
    tick_size: Decimal
    lot_step: Decimal
    lot_min: Decimal
    lot_max: Decimal
    min_notional: Decimal


class VenueError(Exception):

    '''
    Base exception for all venue adapter failures.

    Args:
        message (str): Human-readable error description
    '''

    def __init__(self, message: str) -> None:

        '''
        Store the error message.

        Args:
            message (str): Human-readable error description
        '''

        self.message = message
        super().__init__(message)


class OrderRejectedError(VenueError):

    '''
    Raised when the venue rejects an order submission.

    Args:
        message (str): Human-readable error description
        venue_code (int): Venue-specific error code
        reason (str): Venue-provided rejection reason
    '''

    def __init__(self, message: str, venue_code: int, reason: str) -> None:

        '''
        Store the venue rejection details.

        Args:
            message (str): Human-readable error description
            venue_code (int): Venue-specific error code
            reason (str): Venue-provided rejection reason
        '''

        self.venue_code = venue_code
        self.reason = reason
        super().__init__(message)


class RateLimitError(VenueError):

    '''Raised when retries are exhausted after HTTP 429 responses.'''


class AuthenticationError(VenueError):

    '''Raised when the venue rejects API key or signature.'''


class TransientError(VenueError):

    '''Raised when retries are exhausted on HTTP 5xx or timeout.'''


class NotFoundError(VenueError):

    '''Raised when the requested order or resource does not exist on the venue.'''


@runtime_checkable
class VenueAdapter(Protocol):

    '''
    Venue-agnostic interface for exchange interaction.

    Consumed by Execution Manager, Reconciliation Engine, and Health Monitor.
    Implementations handle authentication, retries, rate limiting, and
    response normalization internally.
    '''

    async def submit_order(
        self,
        account_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: Decimal,
        *,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
        time_in_force: str | None = None,
    ) -> SubmitResult:

        '''
        Submit an order to the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            side (OrderSide): Order direction
            order_type (OrderType): Order type
            qty (Decimal): Order quantity
            price (Decimal | None): Limit price, required for limit orders
            stop_price (Decimal | None): Stop trigger price
            client_order_id (str | None): Deterministic client order identifier
            time_in_force (str | None): Time-in-force policy

        Returns:
            SubmitResult: Venue response with order ID, status, and immediate fills
        '''

        ...

    async def cancel_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:

        '''
        Cancel an open order on the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            venue_order_id (str | None): Venue-assigned order identifier
            client_order_id (str | None): Deterministic client order identifier

        Note:
            At least one of venue_order_id or client_order_id must be provided.

        Returns:
            CancelResult: Venue response with order ID and terminal status
        '''

        ...

    async def query_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> VenueOrder:

        '''
        Query the current state of an order on the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            venue_order_id (str | None): Venue-assigned order identifier
            client_order_id (str | None): Deterministic client order identifier

        Note:
            At least one of venue_order_id or client_order_id must be provided.

        Returns:
            VenueOrder: Current order state from the venue
        '''

        ...

    async def query_open_orders(
        self,
        account_id: str,
        symbol: str,
    ) -> list[VenueOrder]:

        '''
        Query all open orders for a symbol on the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol

        Returns:
            list[VenueOrder]: Open orders from the venue
        '''

        ...

    async def query_balance(
        self,
        account_id: str,
    ) -> list[BalanceEntry]:

        '''
        Query account balances from the venue.

        Args:
            account_id (str): Account identifier for API key routing

        Returns:
            list[BalanceEntry]: Per-asset balance entries
        '''

        ...

    async def query_trades(
        self,
        account_id: str,
        symbol: str,
        *,
        start_time: datetime | None = None,
    ) -> list[VenueTrade]:

        '''
        Query historical trade records from the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            start_time (datetime | None): Return trades after this time

        Returns:
            list[VenueTrade]: Trade records from the venue
        '''

        ...


    async def get_exchange_info(
        self,
        symbol: str,
    ) -> SymbolFilters:

        '''
        Query trading filters for a symbol from the venue.

        Args:
            symbol (str): Trading pair symbol

        Returns:
            SymbolFilters: Venue-imposed trading constraints
        '''

        ...

    async def get_server_time(self) -> int:

        '''
        Query the venue server time.

        Returns:
            int: Server time in milliseconds since epoch
        '''

        ...
