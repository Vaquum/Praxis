'''
Iceberg execution mode parameters.

Defines the visible display quantity and the resting limit price for an
iceberg order. The command quantity is worked as application-level tranches
of display_qty at limit_price, replenished as each tranche fills.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['IcebergParams']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class IcebergParams:

    '''
    Parameters for Iceberg execution mode.

    Args:
        display_qty (Decimal): Visible tranche quantity, positive.
        limit_price (Decimal): Resting limit price, positive.
    '''

    display_qty: Decimal
    limit_price: Decimal

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('display_qty', 'limit_price'):
            value = getattr(self, field)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= _ZERO:
                msg = f'IcebergParams.{field} must be a positive, finite Decimal'
                raise ValueError(msg)
