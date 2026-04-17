'''
HealthSnapshot dataclass: point-in-time Trading sub-system health metrics.

Exposed to Manager so the Manager-side HealthEvaluator can drive
operational-mode transitions (ACTIVE / REDUCE_ONLY / HALTED) per
RFC-4001 §Health.
'''

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ['HealthSnapshot']


@dataclass(frozen=True)
class HealthSnapshot:

    '''
    Point-in-time health metrics for one trading account.

    Args:
        latency_p99_ms (float): Ack latency p99 over the rolling window, in milliseconds.
        consecutive_failures (int): Number of consecutive request failures since the
            last success, non-negative.
        failure_rate (float): Failure rate over the rolling window in the range [0.0, 1.0].
        rate_limit_headroom (float): Rate limit utilisation fraction in the range [0.0, 1.0].
            0.0 means idle, 1.0 means at limit. Higher is worse.
        clock_drift_ms (float): Absolute clock drift from the exchange in milliseconds.
    '''

    latency_p99_ms: float = 0.0
    consecutive_failures: int = 0
    failure_rate: float = 0.0
    rate_limit_headroom: float = 0.0
    clock_drift_ms: float = 0.0

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in (
            'latency_p99_ms',
            'failure_rate',
            'rate_limit_headroom',
            'clock_drift_ms',
        ):
            value = getattr(self, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                msg = f'HealthSnapshot.{field} must be a finite non-negative number'
                raise ValueError(msg)

        for ratio_field in ('failure_rate', 'rate_limit_headroom'):
            value = getattr(self, ratio_field)
            if value > 1.0:
                msg = f'HealthSnapshot.{ratio_field} must be <= 1.0, got {value}'
                raise ValueError(msg)

        if isinstance(self.consecutive_failures, bool) or not isinstance(
            self.consecutive_failures,
            int,
        ):
            msg = 'HealthSnapshot.consecutive_failures must be an int'
            raise ValueError(msg)

        if self.consecutive_failures < 0:
            msg = 'HealthSnapshot.consecutive_failures must be non-negative'
            raise ValueError(msg)
