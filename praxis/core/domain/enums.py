'''
Enumerated types for the Praxis trading domain.

Defines order side, order type, and order lifecycle status enums
used across Position, Order, and Fill dataclasses.
'''

from __future__ import annotations

from enum import Enum


__all__ = ['OrderSide', 'OrderStatus', 'OrderType']


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
