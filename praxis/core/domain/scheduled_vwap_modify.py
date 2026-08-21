'''
Scheduled VWAP amend parameters.

Absolute new values for a running Scheduled VWAP scheme's volume-weight
curve and interval. Every field is optional; at least one must be set.
Whether the new curve is consistent with the scheme's progress is checked
when the amend is applied.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['ScheduledVwapModify']

_ZERO = Decimal(0)
_ONE = Decimal(1)
_MIN_SLICES = 2


@dataclass(frozen=True)
class ScheduledVwapModify:

    '''
    Amend parameters for a running Scheduled VWAP scheme.

    Args:
        volume_weights (tuple[Decimal, ...] | None): New per-slice weights,
            at least 2, each positive, summing to exactly 1. None leaves the
            curve unchanged.
        interval_seconds (int | None): New seconds between slices, positive,
            or None.
    '''

    volume_weights: tuple[Decimal, ...] | None = None
    interval_seconds: int | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if self.volume_weights is None and self.interval_seconds is None:
            msg = 'ScheduledVwapModify requires at least one field to amend'
            raise ValueError(msg)

        if self.volume_weights is not None:
            if not isinstance(self.volume_weights, tuple) or len(self.volume_weights) < _MIN_SLICES:
                msg = f'ScheduledVwapModify.volume_weights must be a tuple of at least {_MIN_SLICES}'
                raise ValueError(msg)

            for weight in self.volume_weights:
                if not isinstance(weight, Decimal) or not weight.is_finite() or weight <= _ZERO:
                    msg = (
                        'ScheduledVwapModify.volume_weights entries must be '
                        'positive, finite Decimals'
                    )
                    raise ValueError(msg)

            if sum(self.volume_weights) != _ONE:
                msg = 'ScheduledVwapModify.volume_weights must sum to 1'
                raise ValueError(msg)

        if self.interval_seconds is not None and (
            isinstance(self.interval_seconds, bool)
            or not isinstance(self.interval_seconds, int)
            or self.interval_seconds <= 0
        ):
            msg = 'ScheduledVwapModify.interval_seconds must be a positive int'
            raise ValueError(msg)
