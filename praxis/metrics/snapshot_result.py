'''Assemble a snapshot metric result from its computed distributions.

The two engines derive their distributions differently — the portfolio
basis walks a `MetricStep` series, the Limen basis works over bar arrays —
but they publish the same thing: each distribution as a p5/p50/p95 triple,
in basis points except drawdown duration, which is in days, plus a single
CVaR. Holding that assembly here keeps the
two reporting one schema, so a number that differs between them is a
difference in the maths and never in the envelope.
'''

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from praxis.metrics.metric_conventions import BPS_PER_UNIT
from praxis.metrics.percentiles import finite_values, quantile_triple

__all__ = ['SNAPSHOT_METRIC_NAMES', 'build_snapshot_result']

_DURATION_DECIMALS = 3
_CVAR_QUANTILE = 0.05
_CVAR_DECIMALS = 1

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


def build_snapshot_result(
    *,
    edge_per_signal_bps: Sequence[float],
    trade_net: Sequence[float],
    trade_gross: Sequence[float],
    rolling_return_net_bps: Sequence[float],
    return_on_exposure: Sequence[float | None],
    drawdown_depth_bps: Sequence[float],
    drawdown_duration_days: Sequence[float],
) -> dict[str, float | None]:

    '''Reduce the computed distributions to the published metric triples.

    Every argument is keyword-only: the series are same-shaped lists of
    floats, so positional order would let two of them swap silently.

    Args:
        edge_per_signal_bps: Per-in-position-step gross return, in bps.
        trade_net: Per-trade net return as a fraction, scaled here.
        trade_gross: Per-trade gross return as a fraction, paired with
            `trade_net` to give the cost drag.
        rolling_return_net_bps: Per-window net return in bps; also the
            CVaR population.
        return_on_exposure: Per-window return divided by that window's
            in-position fraction, `None` for a window with no exposure.
        drawdown_depth_bps: Per-episode trough depth, in bps.
        drawdown_duration_days: Per-episode duration, in days.

    Returns:
        Each distribution as `<name>_p5` / `_p50` / `_p95`, plus
        `cvar_95_return_bps`. Missing values are `None`.
    '''

    trade_pnl_net_bps = [value * BPS_PER_UNIT for value in trade_net]
    cost_drag_bps = [
        (gross - net) * BPS_PER_UNIT
        for gross, net in zip(trade_gross, trade_net, strict=True)
    ]

    triples: dict[str, Sequence[float | None]] = {
        'edge_per_signal_bps': edge_per_signal_bps,
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


def _cvar(rolling_return_net_bps: Sequence[float]) -> float | None:

    '''Return the mean of the worst 5% of window returns, in bps.

    The cutoff is the linear-interpolation 5th percentile of the finite
    values, and every observation at or below it counts, matching Limen.
    '''

    values = finite_values(rolling_return_net_bps)

    if values.size == 0:
        return None

    cutoff = np.quantile(values, _CVAR_QUANTILE, method='linear')

    return round(float(values[values <= cutoff].mean()), _CVAR_DECIMALS)
