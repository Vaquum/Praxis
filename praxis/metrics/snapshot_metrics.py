'''Distribution metrics over a return-step series (portfolio basis).

Computes the metric shapes Limen's `backtest_snapshot` defines — per-signal
edge, per-trade net PnL and cost drag, clock-window rolling return and
return-on-exposure, drawdown depth and duration, and 95% CVaR — over a
`MetricStep` series built from a run's marks and fills. This is the
total-account-equity ("portfolio") view; the bit-exact Limen bar backtest
lives in `praxis.metrics.limen_snapshot`. Each metric is a p5/p50/p95
triple, basis-point scaled; `SNAPSHOT_METRIC_NAMES` lists the keys.
'''

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from praxis.metrics.metric_conventions import BPS_PER_UNIT, SECONDS_PER_DAY
from praxis.metrics.metric_step import MetricStep
from praxis.metrics.snapshot_result import (
    SNAPSHOT_METRIC_NAMES,
    build_snapshot_result,
)

__all__ = ['SNAPSHOT_METRIC_NAMES', 'snapshot_metrics']


def snapshot_metrics(
    steps: Sequence[MetricStep],
    clock_window: str = '1d',
) -> dict[str, float | None]:

    '''Compute the portfolio-basis distribution metrics for a run.

    Args:
        steps: The run's return series, in time order.
        clock_window: Polars duration string for rolling-window bucketing
            (e.g. '1d'); rolling return and return-on-exposure are
            computed per window.

    Returns:
        A dict whose keys are each distribution metric in
        `SNAPSHOT_METRIC_NAMES` suffixed with `_p5`/`_p50`/`_p95`, plus the
        single `cvar_95_return_bps`. Missing values are `None`.
    '''

    edge_per_signal = [s.gross_return * BPS_PER_UNIT for s in steps if s.in_position]
    trade_net, trade_gross = _trade_runs(steps)
    rolling_return_net_bps, return_on_exposure = _clock_window_returns(steps, clock_window)
    drawdown_depth_bps, drawdown_duration_days = _drawdown_episodes(steps)

    return build_snapshot_result(
        edge_per_signal_bps=edge_per_signal,
        trade_net=trade_net,
        trade_gross=trade_gross,
        rolling_return_net_bps=rolling_return_net_bps,
        return_on_exposure=return_on_exposure,
        drawdown_depth_bps=drawdown_depth_bps,
        drawdown_duration_days=drawdown_duration_days,
    )


def _trade_runs(steps: Sequence[MetricStep]) -> tuple[list[float], list[float]]:

    trade_net: list[float] = []
    trade_gross: list[float] = []
    net_run = 1.0
    gross_run = 1.0
    open_run = False

    for step in steps:

        if step.in_position:
            net_run *= 1.0 + step.net_return
            gross_run *= 1.0 + step.gross_return
            open_run = True

        elif open_run:
            trade_net.append(net_run - 1.0)
            trade_gross.append(gross_run - 1.0)
            net_run = 1.0
            gross_run = 1.0
            open_run = False

    if open_run:
        trade_net.append(net_run - 1.0)
        trade_gross.append(gross_run - 1.0)

    return trade_net, trade_gross


def _clock_window_returns(
    steps: Sequence[MetricStep],
    clock_window: str,
) -> tuple[list[float], list[float | None]]:

    '''Return per-window rolling net return and return-on-exposure.

    Return-on-exposure divides the window's net return by the fraction of
    the window in position. Numerator and denominator are computed over the
    same steps, so the ratio is internally consistent; `None` when the
    window has no in-position steps.
    '''

    if not steps:
        return [], []

    frame = pl.DataFrame(
        {
            'timestamp': [s.timestamp for s in steps],
            'net_return': [s.net_return for s in steps],
            'in_position': [1.0 if s.in_position else 0.0 for s in steps],
        }
    )
    windowed = frame.group_by(
        pl.col('timestamp').dt.truncate(clock_window).alias('window'),
        maintain_order=True,
    ).agg(
        ((1.0 + pl.col('net_return')).product() - 1.0).alias('window_return'),
        pl.col('in_position').mean().alias('exposure'),
    )

    rolling_bps = [value * BPS_PER_UNIT for value in windowed['window_return']]
    return_on_exposure = [
        window_return / exposure * BPS_PER_UNIT if exposure > 0 else None
        for window_return, exposure in zip(
            windowed['window_return'], windowed['exposure'], strict=True,
        )
    ]

    return rolling_bps, return_on_exposure


def _drawdown_episodes(steps: Sequence[MetricStep]) -> tuple[list[float], list[float]]:

    if not steps:
        return [], []

    equity = 1.0
    peak = 1.0
    depths_bps: list[float] = []
    durations_days: list[float] = []
    in_drawdown = False
    start_time = steps[0].timestamp
    trough = 0.0

    for step in steps:

        equity *= 1.0 + step.net_return
        peak = max(peak, equity)
        drawdown = equity / peak - 1.0 if peak > 0 else 0.0

        if drawdown < 0 and not in_drawdown:
            in_drawdown = True
            start_time = step.timestamp
            trough = drawdown

        elif drawdown < 0:
            trough = min(trough, drawdown)

        elif in_drawdown:
            depths_bps.append(trough * BPS_PER_UNIT)
            durations_days.append(
                (step.timestamp - start_time).total_seconds() / SECONDS_PER_DAY,
            )
            in_drawdown = False
            trough = 0.0

    if in_drawdown:
        depths_bps.append(trough * BPS_PER_UNIT)

    return depths_bps, durations_days
