'''
Enumerated types for the Praxis trading domain.

Defines order side, order type, and order lifecycle status enums
used across Position, Order, Fill, TradeCommand, TradeAbort, and TradeOutcome dataclasses.
'''

from __future__ import annotations

from enum import Enum


__all__ = ['BracketProtectionStatus', 'CostBasisMethod', 'ExecutionMode', 'ExecutionType', 'FundDirection', 'MakerPreference', 'OrderSide', 'OrderStatus', 'OrderType', 'STPMode', 'SchemeState', 'TradeStatus']


class OrderSide(Enum):

    '''Buy or sell direction for orders and positions.'''

    BUY = 'BUY'
    SELL = 'SELL'


class CostBasisMethod(Enum):

    '''Cost-basis method for realizing P&L on a sell.'''

    FIFO = 'FIFO'
    AVERAGE = 'AVERAGE'


class FundDirection(Enum):

    '''Direction of a fund transaction on an account.'''

    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'


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


class ExecutionType(Enum):

    '''
    Execution type reported by venue WebSocket executionReport.

    Describes what triggered the report: order acceptance, fill,
    cancellation, rejection, expiry, or self-trade prevention.
    '''

    NEW = 'NEW'
    TRADE = 'TRADE'
    CANCELED = 'CANCELED'
    REPLACED = 'REPLACED'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'
    TRADE_PREVENTION = 'TRADE_PREVENTION'


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


class SchemeState(Enum):

    '''
    Lifecycle state of a multi-slice execution scheme.

    Non-terminal: RUNNING (scheduling and executing children).
    Terminal: COMPLETED, CANCELED, FAILED.
    '''

    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    CANCELED = 'CANCELED'
    FAILED = 'FAILED'


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

    Non-terminal: PENDING, PARTIAL.
    Terminal: FILLED, CANCELED, REJECTED, EXPIRED.
    '''

    PENDING = 'PENDING'
    PARTIAL = 'PARTIAL'
    FILLED = 'FILLED'
    CANCELED = 'CANCELED'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'


class BracketProtectionStatus(Enum):

    '''
    Per-bracket protective-OCO amend state.

    Tracks a single bracket's protective OCO through a durable, versioned
    amend: from ACTIVE, an amend moves through AMEND_REQUESTED,
    CANCEL_CONFIRMED, and REPLACE_SUBMITTED back to ACTIVE. STATE_UNKNOWN
    marks an ambiguous cancel/replace outcome pending reconciliation. FAILED
    is the durable protection-failed marker meaning no valid protection is
    live for the bracket, distinct from the account operational mode.
    '''

    ACTIVE = 'ACTIVE'
    AMEND_REQUESTED = 'AMEND_REQUESTED'
    CANCEL_CONFIRMED = 'CANCEL_CONFIRMED'
    STATE_UNKNOWN = 'STATE_UNKNOWN'
    REPLACE_SUBMITTED = 'REPLACE_SUBMITTED'
    FAILED = 'FAILED'
