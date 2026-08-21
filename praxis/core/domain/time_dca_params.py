'''
Time DCA execution mode parameters.

Defines the iteration count and interval for a fixed-interval accumulation
order. The command quantity is spread across num_iterations market buys
submitted interval_seconds apart.
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['TimeDcaParams']

_MIN_ITERATIONS = 2


@dataclass(frozen=True)
class TimeDcaParams:

    '''
    Parameters for Time DCA execution mode.

    Args:
        num_iterations (int): Number of accumulation buys, at least 2.
        interval_seconds (int): Seconds between iterations, positive.
    '''

    num_iterations: int
    interval_seconds: int

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if (
            isinstance(self.num_iterations, bool)
            or not isinstance(self.num_iterations, int)
            or self.num_iterations < _MIN_ITERATIONS
        ):
            msg = f'TimeDcaParams.num_iterations must be an int at least {_MIN_ITERATIONS}'
            raise ValueError(msg)

        if (
            isinstance(self.interval_seconds, bool)
            or not isinstance(self.interval_seconds, int)
            or self.interval_seconds <= 0
        ):
            msg = 'TimeDcaParams.interval_seconds must be a positive int'
            raise ValueError(msg)
