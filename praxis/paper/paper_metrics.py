'''Compute backtest metrics for a paper-trading run.

A paper run's return series is the mark timeline the MtmLoop samples —
`(timestamp, mark_price)` pairs — against which the account equity and
per-step returns are built from the run's spine `FillReceived` events. The
portfolio-basis metrics come from the same shared core replay uses. A paper
run has no Limen bar backtest (there are no bars, only live marks), so its
Limen-parity `snapshot` is empty; it reports `snapshot_portfolio` only.
'''

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from praxis.core.domain.events import FillReceived
from praxis.replay.build_replay_report import build_metrics_from_timeline
from praxis.replay.replay_report import ReplayMetrics, Trade

__all__ = ['build_paper_metrics']

_ZERO = Decimal(0)
_MIN_MARKS_FOR_INTERVAL = 2


def build_paper_metrics(
    capital_pool: Decimal,
    interval_seconds: int,
    fills: Sequence[FillReceived],
    marks: Sequence[tuple[datetime, Decimal]],
) -> tuple[tuple[Trade, ...], ReplayMetrics]:

    '''Summarise a paper run's fills against its MtmLoop mark timeline.

    Args:
        capital_pool: Starting quote capital.
        interval_seconds: Nominal mark sampling spacing; used to annualize
            Sharpe only as a fallback when fewer than two marks exist. With
            two or more marks the observed mean cadence is used instead, so
            a timeline made irregular by skipped samples is not mis-scaled.
        fills: The run's `FillReceived` events in any order.
        marks: Time-ordered `(timestamp, mark_price)` samples; timestamps
            must be timezone-aware and strictly increasing, prices
            positive and finite.

    Returns:
        The closed trades in entry order and the run's metrics.

    Raises:
        ValueError: `interval_seconds` is not positive, or a mark has a
            naive timestamp, a non-increasing timestamp, or a non-positive
            or non-finite price.
    '''

    if interval_seconds <= 0:
        msg = f'interval_seconds must be positive, got {interval_seconds}'
        raise ValueError(msg)

    previous: datetime | None = None

    for timestamp, price in marks:

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            msg = f'mark timestamp must be timezone-aware, got {timestamp}'
            raise ValueError(msg)

        if previous is not None and timestamp <= previous:
            msg = f'mark timestamps must strictly increase, got {timestamp} after {previous}'
            raise ValueError(msg)

        if not price.is_finite() or price <= _ZERO:
            msg = f'mark price must be positive and finite, got {price}'
            raise ValueError(msg)

        previous = timestamp

    effective = _effective_interval_seconds(marks, interval_seconds)

    return build_metrics_from_timeline(capital_pool, effective, fills, marks, {})


def _effective_interval_seconds(
    marks: Sequence[tuple[datetime, Decimal]],
    fallback: int,
) -> int:

    '''Return the mean seconds between consecutive marks, or `fallback`.

    A paper mark timeline is irregular when the sampler skips ticks, so the
    Sharpe annualization uses the observed mean cadence (total span over the
    number of intervals) rather than the nominal one. Falls back to
    `fallback` when fewer than two marks exist.
    '''

    if len(marks) < _MIN_MARKS_FOR_INTERVAL:
        return fallback

    span_seconds = (marks[-1][0] - marks[0][0]).total_seconds()

    return max(round(span_seconds / (len(marks) - 1)), 1)
