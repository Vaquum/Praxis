'''
Time DCA amend parameters.

Absolute new values for a running Time DCA scheme's iteration count and
interval. Every field is optional; at least one must be set. Whether the
new count is consistent with the scheme's progress is checked when the
amend is applied.
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['TimeDcaModify']

_MIN_ITERATIONS = 2


@dataclass(frozen=True)
class TimeDcaModify:

    '''
    Amend parameters for a running Time DCA scheme.

    Args:
        num_iterations (int | None): New total iteration count, at least 2,
            or None.
        interval_seconds (int | None): New seconds between iterations,
            positive, or None.
    '''

    num_iterations: int | None = None
    interval_seconds: int | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if self.num_iterations is None and self.interval_seconds is None:
            msg = 'TimeDcaModify requires at least one field to amend'
            raise ValueError(msg)

        if self.num_iterations is not None and (
            isinstance(self.num_iterations, bool)
            or not isinstance(self.num_iterations, int)
            or self.num_iterations < _MIN_ITERATIONS
        ):
            msg = f'TimeDcaModify.num_iterations must be an int at least {_MIN_ITERATIONS}'
            raise ValueError(msg)

        if self.interval_seconds is not None and (
            isinstance(self.interval_seconds, bool)
            or not isinstance(self.interval_seconds, int)
            or self.interval_seconds <= 0
        ):
            msg = 'TimeDcaModify.interval_seconds must be a positive int'
            raise ValueError(msg)
