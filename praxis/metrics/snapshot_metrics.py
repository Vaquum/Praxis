'''Distribution backtest metrics over a return-step series (Limen parity).

Reproduces Limen's `backtest_snapshot` metric definitions from a
`MetricStep` sequence: per-signal edge, per-trade net PnL and cost drag,
clock-window rolling return and return-on-exposure, drawdown depth and
duration, and 95% CVaR — each distribution metric as a p5/p50/p95 triple,
all basis-point scaled.
'''

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from praxis.metrics.metric_step import MetricStep
from praxis.metrics.percentiles import finite_values, quantile_triple

__all__ = ['SNAPSHOT_METRIC_NAMES', 'snapshot_metrics']

_BPS_PER_UNIT = 10_000.0
_DURATION_DECIMALS = 3
_CVAR_QUANTILE = 0.05

SNAPSHOT_METRIC_NAMES = (
    'edge_per_signal_bps',
    'trade_pnl_net_bps',
    'cost_drag_bps',
    'rolling_return_net_bps',
    'return_on_exposure',
    'drawdown_depth_bps',
    'drawdown_duration_days',
    'cvar_95_return_bps',
)


def snapshot_metrics(
    steps: Sequence[MetricStep],
    clock_window: str = '1D',
) -> dict[str, float | None]:

    '''Compute the Limen-parity distribution metrics for a run.

    Args:
        steps: The run's return series, in time order.
        clock_window: Pandas offset alias for rolling-window bucketing
            (e.g. '1D'); rolling return and return-on-exposure are
            computed per window.

    Returns:
        A dict keyed by `SNAPSHOT_METRIC_NAMES`. Each distribution metric
        contributes `_p5`/`_p50`/`_p95` keys; `cvar_95_return_bps` is a
        single value. Missing values are `None`.
    '''

    edge_per_signal = [s.gross_return * _BPS_PER_UNIT for s in steps if s.in_position]
    trade_net, trade_gross = _trade_runs(steps)
    trade_pnl_net_bps = [v * _BPS_PER_UNIT for v in trade_net]
    cost_drag_bps = [(g - n) * _BPS_PER_UNIT for g, n in zip(trade_gross, trade_net, strict=True)]
    rolling_return_net_bps, return_on_exposure = _clock_window_returns(steps, clock_window)
    drawdown_depth_bps, drawdown_duration_days = _drawdown_episodes(steps)

    triples = {
        'edge_per_signal_bps': edge_per_signal,
        'trade_pnl_net_bps': trade_pnl_net_bps,
        'cost_drag_bps': cost_drag_bps,
        'rolling_return_net_bps': rolling_return_net_bps,
        'return_on_exposure': return_on_exposure,
        'drawdown_depth_bps': drawdown_depth_bps,
    }

    result: dict[str, float | None] = {}

    for name, values in triples.items():
        p5, p50, p95 = quantile_triple(values)
        result[f'{name}_p5'] = p5
        result[f'{name}_p50'] = p50
        result[f'{name}_p95'] = p95

    p5, p50, p95 = quantile_triple(drawdown_duration_days, decimals=_DURATION_DECIMALS)
    result['drawdown_duration_days_p5'] = p5
    result['drawdown_duration_days_p50'] = p50
    result['drawdown_duration_days_p95'] = p95
    result['cvar_95_return_bps'] = _cvar(rolling_return_net_bps)

    return result


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
) -> tuple[list[float], list[float]]:

    if not steps:
        return [], []

    frame = pd.DataFrame(
        {
            'timestamp': [s.timestamp for s in steps],
            'net_return': [s.net_return for s in steps],
            'exposure': [1.0 if s.in_position else 0.0 for s in steps],
        }
    )
    windows = pd.to_datetime(frame['timestamp']).dt.floor(clock_window)
    window_return = (1.0 + frame['net_return']).groupby(windows).prod() - 1.0
    exposure = frame['exposure'].groupby(windows).mean()
    return_on_exposure = (window_return / exposure).where(exposure > 0) * _BPS_PER_UNIT

    rolling_bps = (window_return * _BPS_PER_UNIT).tolist()
    roe = return_on_exposure.tolist()

    return rolling_bps, roe


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
            depths_bps.append(trough * _BPS_PER_UNIT)
            durations_days.append((step.timestamp - start_time).total_seconds() / 86_400.0)
            in_drawdown = False
            trough = 0.0

    if in_drawdown:
        depths_bps.append(trough * _BPS_PER_UNIT)

    return depths_bps, durations_days


def _cvar(rolling_return_net_bps: Sequence[float]) -> float | None:

    values = finite_values(rolling_return_net_bps)

    if values.size == 0:
        return None

    cutoff = np.quantile(values, _CVAR_QUANTILE)

    return round(float(values[values <= cutoff].mean()), 1)
