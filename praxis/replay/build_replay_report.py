'''Compute the per-trade ledger and summary metrics for a replay run.'''

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived
from praxis.replay.replay_report import ReplayMetrics, Trade
from praxis.replay.replay_scenario import ReplayScenario

__all__ = ['build_replay_report']

_ZERO = Decimal(0)
_HUNDRED = Decimal(100)
_NS_PER_SECOND = 1_000_000_000
_SECONDS_PER_YEAR = 31_536_000
_MIN_RETURNS = 2


def build_replay_report(
    scenario: ReplayScenario,
    fills: Sequence[FillReceived],
) -> tuple[tuple[Trade, ...], ReplayMetrics]:
    '''Pair fills into trades and summarise them against the equity curve.

    Fills are grouped by `trade_id` (the position key the venue and Nexus
    share), so concurrently open positions are paired independently rather
    than against each other; within a position, exits consume entries
    FIFO. The closed trades are returned ordered by entry then exit time.

    Args:
        scenario: The replayed scenario; supplies the settle-ordered
            bars, the bar interval, and the starting capital.
        fills: The run's `FillReceived` events in any order; sorted by
            timestamp here, with equal timestamps keeping their input
            (spine) order as the stable tie-breaker.

    Returns:
        The closed trades in entry order and the run's `ReplayMetrics`.
    '''

    ordered = sorted(fills, key=lambda fill: fill.timestamp)
    settles = [int(bar.settle.timestamp() * _NS_PER_SECOND) for bar in scenario.bars]
    trades = _pair_trades(ordered, settles)
    equity, in_position = _equity_curve(ordered, scenario, settles)
    open_qty = sum(
        (fill.qty if fill.side is OrderSide.BUY else -fill.qty for fill in ordered),
        _ZERO,
    )
    total_fees = sum((fill.fee for fill in ordered), _ZERO)
    metrics = _summarise(trades, equity, in_position, open_qty, total_fees, scenario)

    return trades, metrics


def _fill_bar(fill: FillReceived, settles: list[int]) -> int:

    fill_ns = int(fill.timestamp.timestamp() * _NS_PER_SECOND)

    return max(0, bisect_right(settles, fill_ns) - 1)


@dataclass
class _Lot:
    price: Decimal
    qty: Decimal
    fee: Decimal
    bar: int
    ts: datetime


def _take_fee(remaining_fee: Decimal, remaining_qty: Decimal, taken: Decimal) -> Decimal:

    if taken >= remaining_qty:
        return remaining_fee

    return remaining_fee * taken / remaining_qty


def _pair_trades(fills: Sequence[FillReceived], settles: list[int]) -> tuple[Trade, ...]:

    by_position: dict[str, list[FillReceived]] = {}

    for fill in fills:
        by_position.setdefault(fill.trade_id, []).append(fill)

    trades: list[Trade] = []

    for position_fills in by_position.values():
        trades.extend(_pair_position(position_fills, settles))

    trades.sort(key=lambda trade: (trade.entry_ts, trade.exit_ts))

    return tuple(trades)


def _pair_position(position_fills: Sequence[FillReceived], settles: list[int]) -> list[Trade]:

    trades: list[Trade] = []
    lots: deque[_Lot] = deque()

    for fill in position_fills:

        bar = _fill_bar(fill, settles)

        if fill.side is OrderSide.BUY:
            lots.append(_Lot(fill.price, fill.qty, fill.fee, bar, fill.timestamp))
            continue

        remaining = fill.qty
        sell_fee = fill.fee

        while remaining > _ZERO and lots:

            lot = lots[0]
            taken = min(remaining, lot.qty)
            entry_fee = _take_fee(lot.fee, lot.qty, taken)
            exit_fee = _take_fee(sell_fee, remaining, taken)
            gross = (fill.price - lot.price) * taken
            fees = entry_fee + exit_fee
            net = gross - fees
            cost = lot.price * taken
            trades.append(
                Trade(
                    entry_ts=lot.ts,
                    exit_ts=fill.timestamp,
                    entry_price=lot.price,
                    exit_price=fill.price,
                    qty=taken,
                    gross_pnl=gross,
                    fees=fees,
                    net_pnl=net,
                    return_pct=net / cost * _HUNDRED if cost > _ZERO else _ZERO,
                    bars_held=bar - lot.bar,
                )
            )
            lot.fee -= entry_fee
            lot.qty -= taken
            sell_fee -= exit_fee
            remaining -= taken

            if lot.qty <= _ZERO:
                lots.popleft()

        if remaining > _ZERO:
            raise ValueError(
                f'sell qty exceeds open position {fill.trade_id!r} by {remaining}: '
                f'the replay engine must never emit a sell without sufficient open lots'
            )

    return trades


def _equity_curve(
    fills: Sequence[FillReceived],
    scenario: ReplayScenario,
    settles: list[int],
) -> tuple[list[Decimal], int]:

    by_bar: dict[int, list[FillReceived]] = defaultdict(list)

    for fill in fills:
        by_bar[_fill_bar(fill, settles)].append(fill)

    cash = scenario.capital_pool
    position = _ZERO
    equity: list[Decimal] = []
    in_position = 0

    for index, bar in enumerate(scenario.bars):

        for fill in by_bar.get(index, ()):
            notional = fill.qty * fill.price

            if fill.side is OrderSide.BUY:
                cash -= notional + fill.fee
                position += fill.qty
            else:
                cash += notional - fill.fee
                position -= fill.qty

        equity.append(cash + position * Decimal(str(bar.close)))

        if position > _ZERO:
            in_position += 1

    return equity, in_position


def _summarise(
    trades: tuple[Trade, ...],
    equity: list[Decimal],
    in_position: int,
    open_position_qty: Decimal,
    total_fees: Decimal,
    scenario: ReplayScenario,
) -> ReplayMetrics:

    wins = [trade for trade in trades if trade.net_pnl > _ZERO]
    losses = [trade for trade in trades if trade.net_pnl < _ZERO]
    loss_total = sum((trade.net_pnl for trade in losses), _ZERO)
    win_total = sum((trade.net_pnl for trade in wins), _ZERO)
    net = sum((trade.net_pnl for trade in trades), _ZERO)
    bars = len(scenario.bars)

    return ReplayMetrics(
        trade_count=len(trades),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=Decimal(len(wins)) / Decimal(len(trades)) * _HUNDRED if trades else None,
        gross_pnl=sum((trade.gross_pnl for trade in trades), _ZERO),
        net_pnl=net,
        total_fees=total_fees,
        pnl_pct=net / scenario.capital_pool * _HUNDRED if scenario.capital_pool > _ZERO else _ZERO,
        avg_win=win_total / Decimal(len(wins)) if wins else None,
        avg_loss=loss_total / Decimal(len(losses)) if losses else None,
        profit_factor=win_total / -loss_total if loss_total < _ZERO else None,
        max_drawdown_pct=_max_drawdown_pct(equity),
        sharpe=_sharpe(equity, scenario.interval_seconds),
        exposure_pct=Decimal(in_position) / Decimal(bars) * _HUNDRED if bars else _ZERO,
        final_equity=equity[-1] if equity else scenario.capital_pool,
        open_position_qty=open_position_qty,
    )


def _max_drawdown_pct(equity: list[Decimal]) -> Decimal:

    peak = _ZERO
    worst = _ZERO

    for value in equity:

        peak = max(peak, value)

        if peak > _ZERO:
            worst = max(worst, (peak - value) / peak)

    return worst * _HUNDRED


def _sharpe(equity: list[Decimal], interval_seconds: int) -> Decimal | None:

    if interval_seconds <= 0:
        return None

    returns = [
        equity[i] / equity[i - 1] - 1
        for i in range(1, len(equity))
        if equity[i - 1] > _ZERO
    ]

    if len(returns) < _MIN_RETURNS:
        return None

    mean = sum(returns, _ZERO) / Decimal(len(returns))
    variance = sum(((value - mean) ** 2 for value in returns), _ZERO) / Decimal(len(returns) - 1)

    if variance <= _ZERO:
        return None

    periods = Decimal(_SECONDS_PER_YEAR) / Decimal(interval_seconds)

    return mean / variance.sqrt() * periods.sqrt()
