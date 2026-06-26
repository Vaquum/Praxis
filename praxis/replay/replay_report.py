'''Per-trade ledger and summary metrics derived from a replay run.'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

__all__ = ['ReplayMetrics', 'Trade']


@dataclass(frozen=True)
class Trade:
    '''One closed round-trip: a BUY entry paired with its SELL exit.

    Args:
        entry_ts: Timestamp of the entry fill.
        exit_ts: Timestamp of the exit fill.
        entry_price: Entry fill price in the quote asset.
        exit_price: Exit fill price in the quote asset.
        qty: Base quantity closed by the exit.
        gross_pnl: `(exit_price - entry_price) * qty`, before fees.
        fees: Entry plus exit fees in the quote asset.
        net_pnl: `gross_pnl - fees`.
        return_pct: `net_pnl / (entry_price * qty) * 100`.
        bars_held: Bars between the entry and exit settle.
    '''

    entry_ts: datetime
    exit_ts: datetime
    entry_price: Decimal
    exit_price: Decimal
    qty: Decimal
    gross_pnl: Decimal
    fees: Decimal
    net_pnl: Decimal
    return_pct: Decimal
    bars_held: int


@dataclass(frozen=True)
class ReplayMetrics:
    '''Summary statistics over a replay's closed trades and equity curve.

    Fields that are undefined for the run are `None`: `win_rate`,
    `avg_win`, `avg_loss`, and `profit_factor` when there are no closed
    trades (or no losses, for `profit_factor`); `sharpe` when fewer than
    two equity returns exist or their dispersion is zero.

    Args:
        trade_count: Number of closed round-trips.
        win_count: Closed trades with positive `net_pnl`.
        loss_count: Closed trades with negative `net_pnl`.
        win_rate: `win_count / trade_count * 100`.
        gross_pnl: Sum of every closed trade's `gross_pnl`.
        net_pnl: Sum of every closed trade's `net_pnl` (entry + exit
            fees). Differs from the Nexus `realized_pnl`, which nets exit
            fees only.
        total_fees: Total fees paid across every fill, including the entry
            fee of a position still open at the run's end. Equals
            `ReplayResult.fees`; differs from the sum of closed-trade fees
            only when the run ends holding a position.
        pnl_pct: `net_pnl / starting_capital * 100`.
        avg_win: Mean `net_pnl` of winning trades.
        avg_loss: Mean `net_pnl` of losing trades.
        profit_factor: Gross winning `net_pnl` over absolute gross losing
            `net_pnl`.
        max_drawdown_pct: Largest peak-to-trough equity decline, percent.
        sharpe: Per-bar equity return mean over standard deviation,
            annualized by the bars-per-year implied by the bar interval,
            at a zero risk-free rate.
        exposure_pct: Share of bars closed holding a position, percent.
        final_equity: Cash plus marked position at the last bar close.
        open_position_qty: Base quantity still open at the run's end.
    '''

    trade_count: int
    win_count: int
    loss_count: int
    win_rate: Decimal | None
    gross_pnl: Decimal
    net_pnl: Decimal
    total_fees: Decimal
    pnl_pct: Decimal
    avg_win: Decimal | None
    avg_loss: Decimal | None
    profit_factor: Decimal | None
    max_drawdown_pct: Decimal
    sharpe: Decimal | None
    exposure_pct: Decimal
    final_equity: Decimal
    open_position_qty: Decimal
