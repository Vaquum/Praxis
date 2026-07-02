'''Faithful port of Limen's `backtest_snapshot` for exact replay parity.

Reproduces `limen/backtest/backtest_snapshot.py` bar-for-bar over a bar
series (predictions plus OHLC), so a replay over historical bars yields the
same distribution metrics Limen's decoder-level backtest produces. Pinned by
golden fixtures generated from the real Limen (`tests/fixtures/`). Kept in
numpy so pandas stays out of the trading import path.
'''

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import numpy as np

from praxis.metrics.percentiles import finite_values, quantile_triple

__all__ = ['LIMEN_SNAPSHOT_METRIC_NAMES', 'limen_snapshot']

_BPS_PER_UNIT = 10_000.0
_DEFAULT_FEE_BPS = 5.0
_DEFAULT_SLIP_BPS = 5.0
_DEFAULT_LAG = 1
_DURATION_DECIMALS = 3
_CVAR_QUANTILE = 0.05
_SECONDS_PER_DAY = 86_400.0
_PRICE_CHANGE_RTOL = 1e-09
_PRICE_CHANGE_ATOL = 1e-12

LIMEN_SNAPSHOT_METRIC_NAMES = (
    'edge_per_signal_bps',
    'trade_pnl_net_bps',
    'cost_drag_bps',
    'rolling_return_net_bps',
    'return_on_exposure',
    'drawdown_depth_bps',
    'drawdown_duration_days',
    'cvar_95_return_bps',
)


def _shift(values: np.ndarray, periods: int, fill: float) -> np.ndarray:

    out = np.full_like(values, fill, dtype=values.dtype)

    if periods == 0:
        return values.copy()

    if periods > 0:
        out[periods:] = values[:-periods] if periods < len(values) else out[periods:]
    else:
        out[:periods] = values[-periods:] if -periods < len(values) else out[:periods]

    return out


def limen_snapshot(
    predictions: Sequence[float],
    open_px: Sequence[float],
    close_px: Sequence[float],
    price_change: Sequence[float],
    datetimes: Sequence[datetime],
    *,
    execution_lag_bars: int = _DEFAULT_LAG,
    fee_bps: float = _DEFAULT_FEE_BPS,
    slip_bps: float = _DEFAULT_SLIP_BPS,
) -> dict[str, float | None]:

    '''Compute Limen's `backtest_snapshot` metrics over a bar series.

    Rolling return and return-on-exposure bucket by calendar day, matching
    Limen's default `clock_window='1D'`; sub-day and multi-day windows are
    out of scope (Praxis replay uses daily windows).

    Args:
        predictions: Per-bar binary signal (0 exit, 1 enter).
        open_px: Per-bar open price.
        close_px: Per-bar close price.
        price_change: Per-bar `close - open`; validated against it.
        datetimes: Per-bar timestamp, timezone-aware, for clock-window
            bucketing and drawdown duration.
        execution_lag_bars: Bars to shift predictions forward onto the
            execution row (Limen default 1).
        fee_bps: Per-fill fee in basis points.
        slip_bps: Per-fill slippage in basis points.

    Returns:
        A dict keyed by each metric in `LIMEN_SNAPSHOT_METRIC_NAMES` suffixed
        with `_p5`/`_p50`/`_p95`, plus the single `cvar_95_return_bps`.
        Missing values are `None`.

    Raises:
        ValueError: The series is empty, the columns differ in length,
            `execution_lag_bars` is negative, a prediction is not 0/1,
            `price_change != close - open`, or a timestamp is not a
            `datetime`. Unlike Limen, invalid timestamps are rejected
            rather than silently coerced, since the callers guarantee
            valid timestamps and a missing one signals a caller bug.
    '''

    pred = np.asarray(predictions, dtype=float)
    open_arr = np.asarray(open_px, dtype=float)
    close_arr = np.asarray(close_px, dtype=float)
    dpx = np.asarray(price_change, dtype=float)
    size = pred.size

    if size == 0:
        raise ValueError('limen_snapshot requires at least one bar')

    if not (open_arr.size == close_arr.size == dpx.size == len(datetimes) == size):
        raise ValueError('all input columns must have the same length')

    if not all(isinstance(moment, datetime) for moment in datetimes):
        raise ValueError('datetimes must all be datetime instances')

    if execution_lag_bars < 0:
        raise ValueError('execution_lag_bars must be >= 0')

    if not bool(((pred == 0.0) | (pred == 1.0)).all()):
        raise ValueError('predictions must contain only 0 or 1')

    price_known = ~np.isnan(open_arr) & ~np.isnan(close_arr) & ~np.isnan(dpx)

    with np.errstate(invalid='ignore'):
        price_change_ok = not price_known.any() or bool(np.allclose(
            dpx[price_known], (close_arr - open_arr)[price_known],
            rtol=_PRICE_CHANGE_RTOL, atol=_PRICE_CHANGE_ATOL,
        ))

    if not price_change_ok:
        raise ValueError('price_change must equal close - open')

    tradable = price_known & (open_arr != 0.0)

    execution_rows = np.zeros(size, dtype=bool)
    execution_rows[min(execution_lag_bars, size):] = True

    lagged = _shift(pred, execution_lag_bars, 0.0)
    eval_mask = execution_rows & tradable
    pos = (lagged == 1.0) & eval_mask

    entry_mask = pos & ~_shift(pos.astype(float), 1, 0.0).astype(bool)
    cont_mask = pos & _shift(pos.astype(float), 1, 0.0).astype(bool)
    exit_mask = pos & ~_shift(pos.astype(float), -1, 0.0).astype(bool)

    with np.errstate(divide='ignore', invalid='ignore'):
        r_entry = dpx / open_arr
        r_cont = close_arr / _shift(close_arr, 1, np.nan) - 1.0

    r_gross = np.where(entry_mask, r_entry, 0.0) + np.where(cont_mask, r_cont, 0.0)
    r_gross = np.where(np.isnan(r_gross), 0.0, r_gross)

    fee = fee_bps / _BPS_PER_UNIT
    slip = slip_bps / _BPS_PER_UNIT
    cost_mult = np.ones(size)
    cost_mult[entry_mask] *= (1.0 - fee) / (1.0 + slip)
    cost_mult[exit_mask] *= (1.0 - fee) * (1.0 - slip)

    r_net = (1.0 + r_gross) * cost_mult - 1.0
    r_net = np.where(np.isnan(r_net), 0.0, r_net)
    eq_net = np.cumprod(1.0 + r_net)

    trade_net, trade_gross = _trade_runs(pos, entry_mask, r_net, r_gross)

    edge_per_signal = [float(v * _BPS_PER_UNIT) for v in r_gross[pos]]
    trade_pnl_net_bps = [v * _BPS_PER_UNIT for v in trade_net]
    cost_drag_bps = [(g - n) * _BPS_PER_UNIT for g, n in zip(trade_gross, trade_net, strict=True)]
    rolling_return_net_bps, return_on_exposure = _clock_window_returns(
        datetimes, eval_mask, pos, r_net,
    )
    drawdown_depth_bps, drawdown_duration_days = _drawdown_episodes(
        eq_net, eval_mask, datetimes,
    )

    result: dict[str, float | None] = {}
    triples: dict[str, Sequence[float | None]] = {
        'edge_per_signal_bps': edge_per_signal,
        'trade_pnl_net_bps': trade_pnl_net_bps,
        'cost_drag_bps': cost_drag_bps,
        'rolling_return_net_bps': rolling_return_net_bps,
        'return_on_exposure': return_on_exposure,
        'drawdown_depth_bps': drawdown_depth_bps,
    }

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


def _trade_runs(
    pos: np.ndarray,
    entry_mask: np.ndarray,
    r_net: np.ndarray,
    r_gross: np.ndarray,
) -> tuple[list[float], list[float]]:

    if not entry_mask.any():
        return [], []

    run_ids = np.cumsum(entry_mask.astype(int))
    trade_net: list[float] = []
    trade_gross: list[float] = []

    for run in np.unique(run_ids[pos]):
        mask = pos & (run_ids == run)
        trade_net.append(float(np.prod(1.0 + r_net[mask]) - 1.0))
        trade_gross.append(float(np.prod(1.0 + r_gross[mask]) - 1.0))

    return trade_net, trade_gross


def _clock_window_returns(
    datetimes: Sequence[datetime],
    eval_mask: np.ndarray,
    pos: np.ndarray,
    r_net: np.ndarray,
) -> tuple[list[float], list[float | None]]:

    windows: dict[int, list[int]] = {}

    for index, moment in enumerate(datetimes):

        if not eval_mask[index]:
            continue

        windows.setdefault(moment.toordinal(), []).append(index)

    rolling_bps: list[float] = []
    return_on_exposure: list[float | None] = []

    for key in sorted(windows):
        rows = windows[key]
        window_return = float(np.prod([1.0 + r_net[i] for i in rows]) - 1.0)
        exposure = float(np.mean([1.0 if pos[i] else 0.0 for i in rows]))
        rolling_bps.append(window_return * _BPS_PER_UNIT)
        return_on_exposure.append(
            window_return / exposure * _BPS_PER_UNIT if exposure > 0 else None,
        )

    return rolling_bps, return_on_exposure


def _drawdown_episodes(
    eq_net: np.ndarray,
    eval_mask: np.ndarray,
    datetimes: Sequence[datetime],
) -> tuple[list[float], list[float]]:

    indices = [i for i in range(len(eq_net)) if eval_mask[i]]

    if not indices:
        return [], []

    depths_bps: list[float] = []
    durations_days: list[float] = []
    peak = 1.0
    in_drawdown = False
    start_time = datetimes[indices[0]]
    trough = 0.0

    for i in indices:
        peak = max(peak, float(eq_net[i]))
        drawdown = float(eq_net[i]) / peak - 1.0
        moment = datetimes[i]

        if drawdown < 0 and not in_drawdown:
            in_drawdown = True
            start_time = moment
            trough = drawdown

        elif drawdown < 0:
            trough = min(trough, drawdown)

        elif in_drawdown:
            depths_bps.append(trough * _BPS_PER_UNIT)
            durations_days.append((moment - start_time).total_seconds() / _SECONDS_PER_DAY)
            in_drawdown = False
            trough = 0.0

    if in_drawdown:
        depths_bps.append(trough * _BPS_PER_UNIT)

    return depths_bps, durations_days


def _cvar(rolling_return_net_bps: Sequence[float]) -> float | None:

    values = finite_values(rolling_return_net_bps)

    if values.size == 0:
        return None

    cutoff = np.quantile(values, _CVAR_QUANTILE, method='linear')

    return round(float(values[values <= cutoff].mean()), 1)
