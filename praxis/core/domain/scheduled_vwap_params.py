'''
Scheduled VWAP execution mode parameters.

Defines the interval and the strategy-supplied volume-weight curve for a
scheduled volume-weighted average price order. The command quantity is
split across the weights, one market slice per weight, submitted
interval_seconds apart. The curve is supplied by the strategy; Praxis does
not source live volume.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['ScheduledVwapParams']

_ZERO = Decimal(0)
_ONE = Decimal(1)
_MIN_SLICES = 2


@dataclass(frozen=True)
class ScheduledVwapParams:

    '''
    Parameters for Scheduled VWAP execution mode.

    Args:
        interval_seconds (int): Seconds between slice submissions, positive.
        volume_weights (tuple[Decimal, ...]): Per-slice weights, at least 2,
            each positive, summing to exactly 1.
    '''

    interval_seconds: int
    volume_weights: tuple[Decimal, ...]

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if not isinstance(self.interval_seconds, int) or self.interval_seconds <= 0:
            msg = 'ScheduledVwapParams.interval_seconds must be a positive int'
            raise ValueError(msg)

        if not isinstance(self.volume_weights, tuple) or len(self.volume_weights) < _MIN_SLICES:
            msg = f'ScheduledVwapParams.volume_weights must be a tuple of at least {_MIN_SLICES}'
            raise ValueError(msg)

        for weight in self.volume_weights:
            if not isinstance(weight, Decimal) or not weight.is_finite() or weight <= _ZERO:
                msg = (
                    'ScheduledVwapParams.volume_weights entries must be '
                    'positive, finite Decimals'
                )
                raise ValueError(msg)

        if sum(self.volume_weights) != _ONE:
            msg = 'ScheduledVwapParams.volume_weights must sum to 1'
            raise ValueError(msg)
