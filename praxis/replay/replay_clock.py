'''Monotonic simulated UTC clock for replay runs.

A replay run constructs one `ReplayClock` and injects its `now` bound
method wherever live code reads the wall clock (the `clock` /
`now_fn` seams on `Trading`, `ExecutionManager`, `CapitalController`,
and the validator intake hooks). The driver calls `advance_to` as it
walks settle-ordered bars, so every component sees the same simulated
instant and time only moves forward.
'''

from __future__ import annotations

import threading
from datetime import datetime

__all__ = ['ReplayClock']


class ReplayClock:
    '''Cursor-driven UTC clock advanced per replayed bar settle.

    Args:
        start: Initial simulated UTC time; must be timezone-aware.
    '''

    def __init__(self, start: datetime) -> None:
        '''Store the initial instant, rejecting a naive datetime.'''

        if start.tzinfo is None:
            msg = 'start must be timezone-aware'
            raise ValueError(msg)

        self._now = start
        self._lock = threading.Lock()

    def now(self) -> datetime:
        '''Return the current simulated UTC time.'''

        with self._lock:
            return self._now

    def advance_to(self, ts: datetime) -> None:
        '''Advance the cursor to `ts`, rejecting backward movement.

        Args:
            ts: New simulated UTC time; must be timezone-aware and at
                or after the current instant.
        '''

        if ts.tzinfo is None:
            msg = 'ts must be timezone-aware'
            raise ValueError(msg)

        with self._lock:

            if ts < self._now:
                msg = f'replay clock cannot move backward: {ts} < {self._now}'
                raise ValueError(msg)

            self._now = ts
