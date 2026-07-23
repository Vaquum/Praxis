'''
Ladder DCA execution mode parameters.

Defines the explicit resting limit price levels and optional per-level
weights for a ladder order. The command quantity is placed as one resting
limit order per level, split by level_weights or equally when omitted.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['LadderDcaParams']

_ZERO = Decimal(0)
_ONE = Decimal(1)
_MIN_LEVELS = 2


@dataclass(frozen=True)
class LadderDcaParams:

    '''
    Parameters for Ladder DCA execution mode.

    Args:
        price_levels (tuple[Decimal, ...]): Resting limit prices, at least 2,
            each positive, strictly monotonic (so levels are unique and
            ordered).
        level_weights (tuple[Decimal, ...] | None): Per-level quantity weights.
            None splits the quantity equally. When set, the length must match
            price_levels, each entry positive, summing to exactly 1.
    '''

    price_levels: tuple[Decimal, ...]
    level_weights: tuple[Decimal, ...] | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if not isinstance(self.price_levels, tuple) or len(self.price_levels) < _MIN_LEVELS:
            msg = f'LadderDcaParams.price_levels must be a tuple of at least {_MIN_LEVELS}'
            raise ValueError(msg)

        for level in self.price_levels:
            if not isinstance(level, Decimal) or not level.is_finite() or level <= _ZERO:
                msg = 'LadderDcaParams.price_levels entries must be positive, finite Decimals'
                raise ValueError(msg)

        pairs = list(zip(self.price_levels, self.price_levels[1:], strict=False))
        increasing = all(low < high for low, high in pairs)
        decreasing = all(low > high for low, high in pairs)
        if not (increasing or decreasing):
            msg = 'LadderDcaParams.price_levels must be strictly monotonic and unique'
            raise ValueError(msg)

        if self.level_weights is None:
            return

        if (
            not isinstance(self.level_weights, tuple)
            or len(self.level_weights) != len(self.price_levels)
        ):
            msg = 'LadderDcaParams.level_weights must match price_levels in length'
            raise ValueError(msg)

        for weight in self.level_weights:
            if not isinstance(weight, Decimal) or not weight.is_finite() or weight <= _ZERO:
                msg = 'LadderDcaParams.level_weights entries must be positive, finite Decimals'
                raise ValueError(msg)

        if sum(self.level_weights) != _ONE:
            msg = 'LadderDcaParams.level_weights must sum to 1'
            raise ValueError(msg)
