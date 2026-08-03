'''
Bracket amend parameters.

Absolute new values for a bracket's protective take-profit and stop-loss
legs. Each leg may be amended as an absolute price or a basis-point offset,
never both at once. Every field is optional; at least one must be set.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['BracketModify']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class BracketModify:

    '''
    Amend parameters for a bracket's protective legs.

    Args:
        take_profit_price (Decimal | None): New absolute take-profit price.
            Mutually exclusive with take_profit_offset_bps.
        take_profit_offset_bps (Decimal | None): New take-profit offset in
            basis points. Mutually exclusive with take_profit_price.
        stop_loss_price (Decimal | None): New absolute stop-loss trigger price.
            Mutually exclusive with stop_loss_offset_bps.
        stop_loss_offset_bps (Decimal | None): New stop-loss offset in basis
            points. Mutually exclusive with stop_loss_price.
        stop_loss_limit_price (Decimal | None): New stop-loss limit price.
    '''

    take_profit_price: Decimal | None = None
    take_profit_offset_bps: Decimal | None = None
    stop_loss_price: Decimal | None = None
    stop_loss_offset_bps: Decimal | None = None
    stop_loss_limit_price: Decimal | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        fields = (
            'take_profit_price',
            'take_profit_offset_bps',
            'stop_loss_price',
            'stop_loss_offset_bps',
            'stop_loss_limit_price',
        )

        if all(getattr(self, field) is None for field in fields):
            msg = 'BracketModify requires at least one field to amend'
            raise ValueError(msg)

        if self.take_profit_price is not None and self.take_profit_offset_bps is not None:
            msg = 'BracketModify take-profit accepts a price or an offset, not both'
            raise ValueError(msg)

        if self.stop_loss_price is not None and self.stop_loss_offset_bps is not None:
            msg = 'BracketModify stop-loss accepts a price or an offset, not both'
            raise ValueError(msg)

        for field in fields:
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value <= _ZERO
            ):
                msg = f'BracketModify.{field} must be a positive, finite Decimal'
                raise ValueError(msg)
