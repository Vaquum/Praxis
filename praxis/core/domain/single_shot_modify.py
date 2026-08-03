'''
SingleShot amend parameters.

Absolute new values for a resting single-shot order's price legs. Every
field is optional; a modify amends only the fields it sets, and at least
one must be set.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['SingleShotModify']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class SingleShotModify:

    '''
    Amend parameters for a resting SingleShot order.

    Args:
        price (Decimal | None): New limit price, or None to leave unchanged.
        stop_price (Decimal | None): New stop trigger price, or None.
        stop_limit_price (Decimal | None): New stop leg price, or None.
    '''

    price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_limit_price: Decimal | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        fields = ('price', 'stop_price', 'stop_limit_price')

        if all(getattr(self, field) is None for field in fields):
            msg = 'SingleShotModify requires at least one field to amend'
            raise ValueError(msg)

        for field in fields:
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value <= _ZERO
            ):
                msg = f'SingleShotModify.{field} must be a positive, finite Decimal'
                raise ValueError(msg)
