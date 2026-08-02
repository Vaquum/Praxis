'''
Bracket execution mode parameters.

Defines the protective take-profit and stop-loss legs placed as a native
OCO once the bracket entry fills. Each leg is given either as an absolute
price or as an offset in basis points from the entry average fill price;
exactly one form is required per leg.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['BracketParams']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class BracketParams:

    '''
    Parameters for Bracket execution mode.

    Args:
        take_profit_price (Decimal | None): Absolute take-profit limit price.
            Mutually exclusive with take_profit_offset_bps.
        take_profit_offset_bps (Decimal | None): Take-profit distance in basis
            points from the entry average fill price. Mutually exclusive with
            take_profit_price.
        stop_loss_price (Decimal | None): Absolute stop-loss trigger price.
            Mutually exclusive with stop_loss_offset_bps.
        stop_loss_offset_bps (Decimal | None): Stop-loss distance in basis
            points from the entry average fill price. Mutually exclusive with
            stop_loss_price.
        stop_loss_limit_price (Decimal | None): Stop-loss limit price. None
            submits a stop-market stop-loss leg.
    '''

    take_profit_price: Decimal | None = None
    take_profit_offset_bps: Decimal | None = None
    stop_loss_price: Decimal | None = None
    stop_loss_offset_bps: Decimal | None = None
    stop_loss_limit_price: Decimal | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if (self.take_profit_price is None) == (self.take_profit_offset_bps is None):
            msg = 'BracketParams requires exactly one of take_profit_price or take_profit_offset_bps'
            raise ValueError(msg)

        if (self.stop_loss_price is None) == (self.stop_loss_offset_bps is None):
            msg = 'BracketParams requires exactly one of stop_loss_price or stop_loss_offset_bps'
            raise ValueError(msg)

        for field in (
            'take_profit_price',
            'take_profit_offset_bps',
            'stop_loss_price',
            'stop_loss_offset_bps',
            'stop_loss_limit_price',
        ):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value <= _ZERO
            ):
                msg = f'BracketParams.{field} must be a positive, finite Decimal'
                raise ValueError(msg)
