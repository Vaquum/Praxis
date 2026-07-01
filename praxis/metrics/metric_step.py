'''Per-step input record for backtest metric computation.

A run (replay or paper) is reduced to a sequence of these steps — one per
bar (replay) or per mark tick (paper). The metrics module derives every
Limen-parity distribution metric from this sequence, so replay and paper
share one metric core regardless of how they sourced the returns.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ['MetricStep']


@dataclass(frozen=True)
class MetricStep:

    '''One step of a run's return series.

    Args:
        timestamp: Step time, timezone-aware; used for clock-window
            bucketing and drawdown duration.
        in_position: Whether a position is held over this step.
        gross_return: Fractional return over the step before costs (0 when
            flat).
        net_return: Fractional return over the step after fees and costs
            (0 when flat).
    '''

    timestamp: datetime
    in_position: bool
    gross_return: float
    net_return: float
