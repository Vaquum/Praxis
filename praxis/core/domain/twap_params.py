'''
TWAP execution mode parameters.

Defines the slice count and interval for a time-weighted average price
order. The command quantity is split into num_slices equal market slices
submitted interval_seconds apart.
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['TwapParams']

_MIN_SLICES = 2


@dataclass(frozen=True)
class TwapParams:

    '''
    Parameters for TWAP execution mode.

    Args:
        num_slices (int): Number of equal slices, at least 2.
        interval_seconds (int): Seconds between slice submissions, positive.
    '''

    num_slices: int
    interval_seconds: int

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if not isinstance(self.num_slices, int) or self.num_slices < _MIN_SLICES:
            msg = f'TwapParams.num_slices must be an int at least {_MIN_SLICES}'
            raise ValueError(msg)

        if not isinstance(self.interval_seconds, int) or self.interval_seconds <= 0:
            msg = 'TwapParams.interval_seconds must be a positive int'
            raise ValueError(msg)
