'''
Iceberg amend parameters.

Absolute new values for a resting iceberg order's display quantity and
limit price. Every field is optional; at least one must be set.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['IcebergModify']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class IcebergModify:

    '''
    Amend parameters for a resting iceberg order.

    Args:
        display_qty (Decimal | None): New visible tranche quantity, or None.
        limit_price (Decimal | None): New resting limit price, or None.
    '''

    display_qty: Decimal | None = None
    limit_price: Decimal | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        fields = ('display_qty', 'limit_price')

        if all(getattr(self, field) is None for field in fields):
            msg = 'IcebergModify requires at least one field to amend'
            raise ValueError(msg)

        for field in fields:
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value <= _ZERO
            ):
                msg = f'IcebergModify.{field} must be a positive, finite Decimal'
                raise ValueError(msg)
