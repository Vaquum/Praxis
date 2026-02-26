'''
Position dataclass representing an open position per trade per account.

Positions are mutable: qty and avg_entry_price change as fills arrive.
Mutation logic belongs in Trading State, not here.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.enums import OrderSide


__all__ = ['Position']

_ZERO = Decimal(0)


@dataclass
class Position:

    '''
    An open position tracked per trade_id per account_id.

    Args:
        account_id (str): Account that holds the position.
        trade_id (str): Manager correlation identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Position direction.
        qty (Decimal): Current position size, must be non-negative.
        avg_entry_price (Decimal): Volume-weighted average entry price.
    '''

    account_id: str
    trade_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    avg_entry_price: Decimal

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('account_id', 'trade_id', 'symbol'):
            _require_str('Position', field, getattr(self, field))

        if self.qty < _ZERO:
            msg = 'Position.qty must be non-negative'
            raise ValueError(msg)

        if self.avg_entry_price < _ZERO:
            msg = 'Position.avg_entry_price must be non-negative'
            raise ValueError(msg)

    @property
    def is_closed(self) -> bool:

        '''Return True if position quantity has reached zero.'''

        return self.qty == _ZERO
