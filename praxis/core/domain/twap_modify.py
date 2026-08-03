'''
TWAP amend parameters.

Absolute new values for a running TWAP scheme's slice count and interval.
Every field is optional; at least one must be set. Whether the new count is
consistent with the scheme's progress is checked when the amend is applied.
'''

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['TwapModify']

_MIN_SLICES = 2


@dataclass(frozen=True)
class TwapModify:

    '''
    Amend parameters for a running TWAP scheme.

    Args:
        num_slices (int | None): New total slice count, at least 2, or None.
        interval_seconds (int | None): New seconds between slices, positive,
            or None.
    '''

    num_slices: int | None = None
    interval_seconds: int | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        if self.num_slices is None and self.interval_seconds is None:
            msg = 'TwapModify requires at least one field to amend'
            raise ValueError(msg)

        if self.num_slices is not None and (
            not isinstance(self.num_slices, int) or self.num_slices < _MIN_SLICES
        ):
            msg = f'TwapModify.num_slices must be an int at least {_MIN_SLICES}'
            raise ValueError(msg)

        if self.interval_seconds is not None and (
            not isinstance(self.interval_seconds, int) or self.interval_seconds <= 0
        ):
            msg = 'TwapModify.interval_seconds must be a positive int'
            raise ValueError(msg)
