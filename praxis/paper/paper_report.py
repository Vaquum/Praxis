'''Build a paper-trading metrics report from Event Spine events.

Reads a run's `FillReceived` and `MarkSampled` events, computes the shared
Limen-parity and portfolio metrics against the mark timeline, and renders a
JSON-serialisable report. This is the read side of the paper metrics
endpoint and of any offline analysis of a paper run's spine.
'''

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from praxis.core.domain.events import Event, FillReceived, MarkSampled
from praxis.paper.paper_metrics import build_paper_metrics
from praxis.replay.metrics_serialization import metrics_to_json, trade_to_json

__all__ = ['build_paper_report']


def build_paper_report(
    capital_pool: Decimal,
    interval_seconds: int,
    events: Sequence[Event],
) -> dict[str, Any]:

    '''Render a paper run's metrics report from its spine events.

    Args:
        capital_pool: Starting quote capital.
        interval_seconds: Mark sampling spacing, used to annualize Sharpe.
        events: The run's spine events, in any order; only `FillReceived`
            and `MarkSampled` are consumed.

    Returns:
        A JSON-serialisable dict with `metrics` and `trades`.
    '''

    fills = [event for event in events if isinstance(event, FillReceived)]
    samples = sorted(
        (event for event in events if isinstance(event, MarkSampled)),
        key=lambda event: event.timestamp,
    )
    marks: list[tuple[datetime, Decimal]] = []
    last_timestamp: datetime | None = None

    for event in samples:

        if last_timestamp is not None and event.timestamp <= last_timestamp:
            continue

        marks.append((event.timestamp, event.mark_price))
        last_timestamp = event.timestamp

    trades, metrics = build_paper_metrics(capital_pool, interval_seconds, fills, marks)

    return {
        'metrics': metrics_to_json(metrics),
        'trades': [trade_to_json(trade) for trade in trades],
    }
