'''
Enumerated types for the Praxis trading domain.

Defines order side, order type, and order lifecycle status enums
used across Position, Order, Fill, TradeCommand, TradeAbort, and TradeOutcome dataclasses.
'''

from __future__ import annotations

from enum import Enum


__all__ = ['ExecutionMode', 'MakerPreference', 'OrderSide', 'OrderStatus', 'OrderType', 'STPMode', 'TradeStatus']


class OrderSide(Enum):

    '''Buy or sell direction for orders and positions.'''

    BUY = 'BUY'
    SELL = 'SELL'


class OrderType(Enum):

    '''
    Supported order types per venue adapter specification.

    Covers market, limit, stop, and composite order types
    accepted by the Binance venue adapter.
    '''

    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    LIMIT_IOC = 'LIMIT_IOC'
    STOP = 'STOP'
    STOP_LIMIT = 'STOP_LIMIT'
    TAKE_PROFIT = 'TAKE_PROFIT'
    TP_LIMIT = 'TP_LIMIT'
    OCO = 'OCO'


class OrderStatus(Enum):

    '''
    Order lifecycle states per RFC order submission protocol.

    Terminal states: FILLED, CANCELED, REJECTED, EXPIRED.
    '''

    SUBMITTING = 'SUBMITTING'
    OPEN = 'OPEN'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    FILLED = 'FILLED'
    CANCELED = 'CANCELED'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'


class ExecutionMode(Enum):

    '''
    Define execution modes per RFC.
    SingleShot submits as a single unit. Other modes slice
    or schedule orders across time or price levels.
    '''

    SINGLE_SHOT = 'SINGLE_SHOT'
    BRACKET = 'BRACKET'
    TWAP = 'TWAP'
    SCHEDULED_VWAP = 'SCHEDULED_VWAP'
    ICEBERG = 'ICEBERG'
    TIME_DCA = 'TIME_DCA'
    LADDER_DCA = 'LADDER_DCA'


class MakerPreference(Enum):

    '''Define maker/taker preference for order placement.'''

    MAKER_ONLY = 'MAKER_ONLY'
    MAKER_PREFERRED = 'MAKER_PREFERRED'
    NO_PREFERENCE = 'NO_PREFERENCE'


class STPMode(Enum):

    '''Define self-trade prevention mode per venue specification.'''

    EXPIRE_TAKER = 'EXPIRE_TAKER'
    EXPIRE_MAKER = 'EXPIRE_MAKER'
    EXPIRE_BOTH = 'EXPIRE_BOTH'
    NONE = 'NONE'


class TradeStatus(Enum):

    '''
    Define trade-level execution status per Consensus #22.

    Non-terminal: PENDING, PARTIAL, PAUSED.
    Terminal: FILLED, CANCELED, REJECTED, EXPIRED.
    '''

    PENDING = 'PENDING'
    PARTIAL = 'PARTIAL'
    PAUSED = 'PAUSED'
    FILLED = 'FILLED'
    CANCELED = 'CANCELED'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'
