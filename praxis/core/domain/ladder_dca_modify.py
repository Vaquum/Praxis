'''
Ladder DCA amend parameters.

Absolute new values for a ladder's resting limit price levels and optional
per-level weights. Every field is optional; at least one must be set. A set
of price_levels stays subject to the same shape rules as LadderDcaParams.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['LadderDcaModify']

_ZERO = Decimal(0)
_ONE = Decimal(1)
_MIN_LEVELS = 2


@dataclass(frozen=True)
class LadderDcaModify:

    '''
    Amend parameters for a resting ladder.

    Args:
        price_levels (tuple[Decimal, ...] | None): New resting limit prices,
            at least 2, each positive, strictly monotonic. None leaves the
            levels unchanged.
        level_weights (tuple[Decimal, ...] | None): New per-level weights,
            at least 2, each positive, summing to exactly 1. None leaves the
            weights unchanged. When both are set the lengths must match.
    '''

    price_levels: tuple[Decimal, ...] | None = None
    level_weights: tuple[Decimal, ...] | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if self.price_levels is None and self.level_weights is None:
            msg = 'LadderDcaModify requires at least one field to amend'
            raise ValueError(msg)

        if self.price_levels is not None:
            if not isinstance(self.price_levels, tuple) or len(self.price_levels) < _MIN_LEVELS:
                msg = f'LadderDcaModify.price_levels must be a tuple of at least {_MIN_LEVELS}'
                raise ValueError(msg)

            for level in self.price_levels:
                if not isinstance(level, Decimal) or not level.is_finite() or level <= _ZERO:
                    msg = 'LadderDcaModify.price_levels entries must be positive, finite Decimals'
                    raise ValueError(msg)

            pairs = list(zip(self.price_levels, self.price_levels[1:], strict=False))
            increasing = all(low < high for low, high in pairs)
            decreasing = all(low > high for low, high in pairs)
            if not (increasing or decreasing):
                msg = 'LadderDcaModify.price_levels must be strictly monotonic and unique'
                raise ValueError(msg)

        if self.level_weights is not None:
            if not isinstance(self.level_weights, tuple) or len(self.level_weights) < _MIN_LEVELS:
                msg = f'LadderDcaModify.level_weights must be a tuple of at least {_MIN_LEVELS}'
                raise ValueError(msg)

            for weight in self.level_weights:
                if not isinstance(weight, Decimal) or not weight.is_finite() or weight <= _ZERO:
                    msg = 'LadderDcaModify.level_weights entries must be positive, finite Decimals'
                    raise ValueError(msg)

            if sum(self.level_weights) != _ONE:
                msg = 'LadderDcaModify.level_weights must sum to 1'
                raise ValueError(msg)

        if (
            self.price_levels is not None
            and self.level_weights is not None
            and len(self.price_levels) != len(self.level_weights)
        ):
            msg = 'LadderDcaModify.level_weights must match price_levels in length'
            raise ValueError(msg)
