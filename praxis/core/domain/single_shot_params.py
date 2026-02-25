'''
SingleShot execution mode parameters.

Defines price fields for single-unit order submission. Other
execution modes (TWAP, DCA, etc.) have separate param types.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['SingleShotParams']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class SingleShotParams:

    '''
    Parameters for SingleShot execution mode.

    Args:
        price (Decimal | None): Limit price, None for market orders.
        stop_price (Decimal | None): Stop trigger price, None when not applicable.
        stop_limit_price (Decimal | None): Stop leg price for OCO orders, None when not applicable.
    '''

    price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_limit_price: Decimal | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('price', 'stop_price', 'stop_limit_price'):
            value = getattr(self, field)
            if value is not None and value <= _ZERO:
                msg = f'SingleShotParams.{field} must be positive'
                raise ValueError(msg)
