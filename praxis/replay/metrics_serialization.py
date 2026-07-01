'''JSON serialisation for run metrics and trades, shared by replay and paper.

Decimal fields render as strings to preserve precision; undefined metrics
render as null. Used by both the replay HTTP surface and the paper-trading
metrics endpoint so their payloads are identical.
'''

from __future__ import annotations

from decimal import Decimal
from typing import Any

from praxis.replay.replay_report import ReplayMetrics, Trade

__all__ = ['metrics_to_json', 'trade_to_json']


def _optional_decimal(value: Decimal | None) -> str | None:

    return None if value is None else str(value)


def metrics_to_json(metrics: ReplayMetrics) -> dict[str, Any]:

    '''Render a `ReplayMetrics` as a JSON-serialisable dict.'''

    return {
        'trade_count': metrics.trade_count,
        'win_count': metrics.win_count,
        'loss_count': metrics.loss_count,
        'win_rate': _optional_decimal(metrics.win_rate),
        'gross_pnl': str(metrics.gross_pnl),
        'net_pnl': str(metrics.net_pnl),
        'total_fees': str(metrics.total_fees),
        'pnl_pct': str(metrics.pnl_pct),
        'avg_win': _optional_decimal(metrics.avg_win),
        'avg_loss': _optional_decimal(metrics.avg_loss),
        'profit_factor': _optional_decimal(metrics.profit_factor),
        'max_drawdown_pct': str(metrics.max_drawdown_pct),
        'sharpe': _optional_decimal(metrics.sharpe),
        'exposure_pct': str(metrics.exposure_pct),
        'final_equity': str(metrics.final_equity),
        'open_position_qty': str(metrics.open_position_qty),
        'snapshot': metrics.snapshot,
        'snapshot_portfolio': metrics.snapshot_portfolio,
        'expected_value': str(metrics.expected_value),
        'net_long_volume': str(metrics.net_long_volume),
        'net_short_volume': str(metrics.net_short_volume),
        'net_trade_volume': str(metrics.net_trade_volume),
    }


def trade_to_json(trade: Trade) -> dict[str, Any]:

    '''Render a `Trade` as a JSON-serialisable dict.'''

    return {
        'entry_ts': trade.entry_ts.isoformat(),
        'exit_ts': trade.exit_ts.isoformat(),
        'entry_price': str(trade.entry_price),
        'exit_price': str(trade.exit_price),
        'qty': str(trade.qty),
        'gross_pnl': str(trade.gross_pnl),
        'fees': str(trade.fees),
        'net_pnl': str(trade.net_pnl),
        'return_pct': str(trade.return_pct),
        'bars_held': trade.bars_held,
    }
