'''
Interval-slicing execution mode parameters.

Defines the slice count and interval shared by the modes that split a command
into a fixed number of equal MARKET children submitted a fixed number of
seconds apart. TWAP spreads a position over time; Time DCA accumulates one.
The schedule is the same, so the parameters are.
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['IntervalSliceParams']

_MIN_SLICES = 2


@dataclass(frozen=True)
class IntervalSliceParams:

    '''
    Parameters for an interval-sliced execution mode.

    Args:
        num_slices (int): Number of equal slices, at least 2.
        interval_seconds (int): Seconds between slice submissions, positive.
    '''

    num_slices: int
    interval_seconds: int

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if (
            isinstance(self.num_slices, bool)
            or not isinstance(self.num_slices, int)
            or self.num_slices < _MIN_SLICES
        ):
            msg = f'IntervalSliceParams.num_slices must be an int at least {_MIN_SLICES}'
            raise ValueError(msg)

        if (
            isinstance(self.interval_seconds, bool)
            or not isinstance(self.interval_seconds, int)
            or self.interval_seconds <= 0
        ):
            msg = 'IntervalSliceParams.interval_seconds must be a positive int'
            raise ValueError(msg)
