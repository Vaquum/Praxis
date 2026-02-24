'''
Position dataclass representing an open position per trade per account.

Positions are mutable: qty and avg_entry_price change as fills arrive.
Mutation logic belongs in Trading State, not here.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from praxis.core.domain.enums import OrderSide


__all__ = ['Position']


@dataclass
class Position:
    '''
    An open position tracked per trade_id per account_id.

    Args:
        account_id (str): Account that holds the position.
        trade_id (str): Manager correlation identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Position direction.
        qty (Decimal): Current position size.
        avg_entry_price (Decimal): Volume-weighted average entry price.
    '''

    account_id: str
    trade_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    avg_entry_price: Decimal

    @property
    def is_closed(self) -> bool:
        '''Return True if position quantity has reached zero.'''

        return self.qty == Decimal(0)
