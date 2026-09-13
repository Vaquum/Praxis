'''Units the metric engines report in.

Both the portfolio-basis and the Limen bar-basis engine scale returns to
basis points and express drawdown duration in days. The conversions live
here so the two cannot drift to different units while claiming to report
the same metric.
'''

from __future__ import annotations

__all__ = ['BPS_PER_UNIT', 'SECONDS_PER_DAY']

BPS_PER_UNIT = 10_000.0

SECONDS_PER_DAY = 86_400.0
