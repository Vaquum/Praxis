'''
Per-account health-metric collector used by the venue adapter.

HealthTracker keeps rolling samples of REST request latency and success
status per account. Venue-wide measurements (rate-limit utilisation and
clock drift) are held outside and supplied when composing a final
HealthSnapshot.
'''

from __future__ import annotations

import math
from collections import deque
from statistics import quantiles
from threading import Lock

from praxis.core.domain.health_snapshot import HealthSnapshot

__all__ = ['HealthTracker']

_DEFAULT_WINDOW_SIZE = 256
_P99_QUANTILES = 100


class HealthTracker:

    '''
    Collect REST request latency and success/failure samples per account.

    Thread-safe for concurrent `record_request` and `snapshot` calls.

    Args:
        window_size (int): Maximum number of samples retained for rolling
            latency and failure-rate calculations. Must be positive.
    '''

    def __init__(self, window_size: int = _DEFAULT_WINDOW_SIZE) -> None:

        if not isinstance(window_size, int) or window_size <= 0:
            msg = 'HealthTracker.window_size must be a positive int'
            raise ValueError(msg)

        self._window_size = window_size
        self._latencies: deque[float] = deque(maxlen=window_size)
        self._outcomes: deque[bool] = deque(maxlen=window_size)
        self._consecutive_failures = 0
        self._lock = Lock()

    def record_request(self, latency_ms: float, succeeded: bool) -> None:

        '''
        Record the outcome of one REST request.

        Args:
            latency_ms (float): Request round-trip time in milliseconds.
                Must be a finite non-negative number.
            succeeded (bool): True if the request returned a usable response,
                False if it raised an error after all retries.
        '''

        if (
            isinstance(latency_ms, bool)
            or not isinstance(latency_ms, (int, float))
            or not math.isfinite(latency_ms)
            or latency_ms < 0
        ):
            msg = 'HealthTracker.record_request: latency_ms must be a finite non-negative number'
            raise ValueError(msg)

        if not isinstance(succeeded, bool):
            msg = 'HealthTracker.record_request: succeeded must be a bool'
            raise ValueError(msg)

        with self._lock:
            self._latencies.append(float(latency_ms))
            self._outcomes.append(succeeded)
            if succeeded:
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1

    def reset(self) -> None:

        '''Clear all samples. Used only by tests.'''

        with self._lock:
            self._latencies.clear()
            self._outcomes.clear()
            self._consecutive_failures = 0

    def snapshot(
        self,
        rate_limit_utilization: float = 0.0,
        clock_drift_ms: float = 0.0,
    ) -> HealthSnapshot:

        '''
        Build a HealthSnapshot from the current window plus venue-wide inputs.

        Args:
            rate_limit_utilization (float): Current venue-wide rate-limit
                utilisation fraction in [0.0, 1.0]. 0.0 means idle, 1.0
                means at limit.
            clock_drift_ms (float): Current absolute clock drift from the
                exchange in milliseconds.

        Returns:
            HealthSnapshot: Immutable point-in-time metrics.
        '''

        with self._lock:
            latencies = list(self._latencies)
            outcomes = list(self._outcomes)
            consecutive_failures = self._consecutive_failures

        latency_p99_ms = _percentile_99(latencies)
        failure_rate = _failure_rate(outcomes)

        return HealthSnapshot(
            latency_p99_ms=latency_p99_ms,
            consecutive_failures=consecutive_failures,
            failure_rate=failure_rate,
            rate_limit_headroom=rate_limit_utilization,
            clock_drift_ms=clock_drift_ms,
        )


def _percentile_99(samples: list[float]) -> float:

    '''Return the 99th percentile of samples or 0.0 for an empty list.'''

    if not samples:
        return 0.0

    if len(samples) == 1:
        return samples[0]

    return quantiles(samples, n=_P99_QUANTILES, method='inclusive')[-1]


def _failure_rate(outcomes: list[bool]) -> float:

    '''Return the fraction of failing outcomes or 0.0 for an empty list.'''

    if not outcomes:
        return 0.0

    failures = sum(1 for ok in outcomes if not ok)
    return failures / len(outcomes)
