'''Scalar ledger metrics over a closed-trade list.

`expected_value` (mean net PnL per closed trade) reproduces Limen's
`BacktestSequential` definition. The traded-volume scalars are the entry
notional actually filled per side (`entry_price * qty`); Limen's sequential
backtest reinvests the full balance each trade, so its volume is not
value-comparable — these are Praxis's own traded-volume totals. PnL, win
rate, max drawdown, and Sharpe are reported elsewhere and not duplicated.
'''

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

__all__ = ['LedgerTrade', 'ledger_metrics']

_ZERO = Decimal(0)
_QUANTUM = Decimal('0.01')


@dataclass(frozen=True)
class LedgerTrade:

    '''One closed trade in quote-asset terms.

    Args:
        is_long: Whether the trade was long (vs short).
        pnl: Realized PnL in the quote asset.
        volume: Entry notional traded, in the quote asset.
    '''

    is_long: bool
    pnl: Decimal
    volume: Decimal


def ledger_metrics(trades: Sequence[LedgerTrade]) -> dict[str, Decimal]:

    '''Compute scalar ledger metrics over closed trades.

    Args:
        trades: The closed trades, in any order.

    Returns:
        A dict with `expected_value` (mean PnL per trade), `net_long_volume`,
        `net_short_volume`, and `net_trade_volume`, each rounded to two
        decimal places. All zero when there are no trades.
    '''

    if not trades:
        zero = _ZERO.quantize(_QUANTUM)

        return {
            'expected_value': zero,
            'net_long_volume': zero,
            'net_short_volume': zero,
            'net_trade_volume': zero,
        }

    total_pnl = sum((trade.pnl for trade in trades), _ZERO)
    expected_value = total_pnl / Decimal(len(trades))
    net_long_volume = sum((trade.volume for trade in trades if trade.is_long), _ZERO)
    net_short_volume = sum((trade.volume for trade in trades if not trade.is_long), _ZERO)

    return {
        'expected_value': expected_value.quantize(_QUANTUM),
        'net_long_volume': net_long_volume.quantize(_QUANTUM),
        'net_short_volume': net_short_volume.quantize(_QUANTUM),
        'net_trade_volume': (net_long_volume + net_short_volume).quantize(_QUANTUM),
    }
