'''Compute backtest metrics for a paper-trading run.

A paper run's return series is the mark timeline the MtmLoop samples —
`(timestamp, mark_price)` pairs — against which the account equity and
per-step returns are built from the run's spine `FillReceived` events. The
metrics themselves come from the same shared core replay uses, so a paper
run and a replay are directly comparable.
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


def build_paper_metrics(
    capital_pool: Decimal,
    interval_seconds: int,
    fills: Sequence[FillReceived],
    marks: Sequence[tuple[datetime, Decimal]],
) -> tuple[tuple[Trade, ...], ReplayMetrics]:

    '''Summarise a paper run's fills against its MtmLoop mark timeline.

    Args:
        capital_pool: Starting quote capital.
        interval_seconds: Mark sampling spacing, used to annualize Sharpe.
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

        if timestamp.tzinfo is None:
            msg = f'mark timestamp must be timezone-aware, got {timestamp}'
            raise ValueError(msg)

        if previous is not None and timestamp <= previous:
            msg = f'mark timestamps must strictly increase, got {timestamp} after {previous}'
            raise ValueError(msg)

        if not price.is_finite() or price <= _ZERO:
            msg = f'mark price must be positive and finite, got {price}'
            raise ValueError(msg)

        previous = timestamp

    return build_metrics_from_timeline(capital_pool, interval_seconds, fills, marks)
