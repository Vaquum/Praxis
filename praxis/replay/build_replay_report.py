'''Compute the per-trade ledger and summary metrics for a replay run.'''

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived
from praxis.metrics.ledger_metrics import LedgerTrade, ledger_metrics
from praxis.metrics.limen_snapshot import limen_snapshot
from praxis.metrics.metric_step import MetricStep
from praxis.metrics.snapshot_metrics import snapshot_metrics
from praxis.replay.replay_report import ReplayMetrics, Trade
from praxis.replay.replay_scenario import ReplayBar, ReplayScenario

__all__ = ['build_metrics_from_timeline', 'build_replay_report']

_ZERO = Decimal(0)
_HUNDRED = Decimal(100)
_SECONDS_PER_YEAR = 31_536_000
_NS_PER_SECOND = 1_000_000_000
_CLOCK_WINDOW = '1d'
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

    timeline = [(bar.settle, Decimal(str(bar.close))) for bar in scenario.bars]

    return build_metrics_from_timeline(
        scenario.capital_pool, scenario.interval_seconds, fills, timeline,
        _limen_snapshot_from_bars(scenario.bars),
    )


def _limen_snapshot_from_bars(bars: Sequence[ReplayBar]) -> dict[str, float | None]:

    '''Return Limen's `backtest_snapshot` metrics over the replay bars.

    The Limen-parity snapshot is the decoder-level backtest Limen would run
    on these bars' predictions and OHLC, independent of the actual fills, so
    it is directly comparable to Limen. Buckets on the bar's shared `ts`
    (the open timestamp for time bars, the settle for dollar bars) that
    Limen keys its clock windows on — not the settle, which is one interval
    later for time bars and would shift boundary bars into another day
    window. Empty for a bar-less run.
    '''

    if not bars:
        return {}

    return limen_snapshot(
        [bar.prediction for bar in bars],
        [bar.open for bar in bars],
        [bar.close for bar in bars],
        [bar.close - bar.open for bar in bars],
        [_ns_to_datetime(bar.ts_ns) for bar in bars],
    )


def _ns_to_datetime(ns: int) -> datetime:

    '''Convert UTC epoch nanoseconds to a datetime without float rounding.

    Uses integer `divmod` so a timestamp on a day boundary cannot drift into
    an adjacent day window, which `ns / 1e9` could do at epoch magnitudes.
    '''

    seconds, nanos = divmod(ns, _NS_PER_SECOND)

    return datetime.fromtimestamp(seconds, UTC) + timedelta(microseconds=nanos // 1000)


def build_metrics_from_timeline(
    capital_pool: Decimal,
    interval_seconds: int,
    fills: Sequence[FillReceived],
    timeline: Sequence[tuple[datetime, Decimal]],
    snapshot: dict[str, float | None] | None = None,
) -> tuple[tuple[Trade, ...], ReplayMetrics]:
    '''Pair fills into trades and summarise them against a mark timeline.

    Shared by replay (bar closes) and paper trading (MtmLoop marks). The
    timeline is the settle-ordered `(timestamp, mark_price)` series the
    equity curve and portfolio return steps are built against.

    Args:
        capital_pool: Starting quote capital.
        interval_seconds: Step spacing, used to annualize Sharpe.
        fills: The run's `FillReceived` events in any order.
        timeline: Settle-ordered `(timestamp, mark_price)` steps.
        snapshot: The Limen-parity distribution metrics for the run;
            replay supplies Limen's bar backtest, paper supplies `{}`
            since a Limen bar backtest is undefined on live marks.
            Defaults to `{}` when omitted.

    Returns:
        The closed trades in entry order and the run's `ReplayMetrics`.
    '''

    snapshot = snapshot if snapshot is not None else {}
    ordered = sorted(fills, key=lambda fill: fill.timestamp)
    settles = [settle for settle, _ in timeline]
    trades = _pair_trades(ordered, settles)
    equity, in_position_bars = _equity_curve(ordered, capital_pool, timeline)
    open_qty = sum(
        (fill.qty if fill.side is OrderSide.BUY else -fill.qty for fill in ordered),
        _ZERO,
    )
    total_fees = sum((fill.fee for fill in ordered), _ZERO)
    snapshot_portfolio = snapshot_metrics(
        _equity_steps(ordered, capital_pool, timeline), _CLOCK_WINDOW,
    )
    scalars = ledger_metrics(_ledger_trades(trades))
    metrics = _summarise(
        trades, equity, in_position_bars, open_qty, total_fees,
        snapshot, snapshot_portfolio, scalars, capital_pool, interval_seconds, len(timeline),
    )

    return trades, metrics


def _equity_steps(
    fills: Sequence[FillReceived],
    capital_pool: Decimal,
    timeline: Sequence[tuple[datetime, Decimal]],
) -> list[MetricStep]:

    '''Return per-step marks on a total-account-equity basis (portfolio view).'''

    settles = [settle for settle, _ in timeline]
    by_step: dict[int, list[FillReceived]] = defaultdict(list)

    for fill in fills:
        by_step[_fill_bar(fill, settles)].append(fill)

    net_cash = capital_pool
    gross_cash = capital_pool
    position = _ZERO
    steps: list[MetricStep] = []
    prev_net = capital_pool
    prev_gross = capital_pool

    for index, (settle, close) in enumerate(timeline):

        held_in = position

        for fill in by_step.get(index, ()):
            notional = fill.qty * fill.price

            if fill.side is OrderSide.BUY:
                net_cash -= notional + fill.fee
                gross_cash -= notional
                position += fill.qty
            else:
                net_cash += notional - fill.fee
                gross_cash += notional
                position -= fill.qty

        marked = position * close
        net_eq = net_cash + marked
        gross_eq = gross_cash + marked
        steps.append(
            MetricStep(
                timestamp=settle,
                in_position=position > _ZERO or held_in > _ZERO,
                gross_return=float(gross_eq / prev_gross - 1) if prev_gross > _ZERO else 0.0,
                net_return=float(net_eq / prev_net - 1) if prev_net > _ZERO else 0.0,
            )
        )
        prev_net = net_eq
        prev_gross = gross_eq

    return steps


def _ledger_trades(trades: Sequence[Trade]) -> list[LedgerTrade]:

    return [
        LedgerTrade(is_long=True, pnl=trade.net_pnl, volume=trade.entry_price * trade.qty)
        for trade in trades
    ]


def _fill_bar(fill: FillReceived, settles: list[datetime]) -> int:

    return max(0, bisect_right(settles, fill.timestamp) - 1)


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


def _pair_trades(fills: Sequence[FillReceived], settles: list[datetime]) -> tuple[Trade, ...]:

    by_position: dict[str, list[FillReceived]] = {}

    for fill in fills:
        by_position.setdefault(fill.trade_id, []).append(fill)

    trades: list[Trade] = []

    for position_fills in by_position.values():
        trades.extend(_pair_position(position_fills, settles))

    trades.sort(key=lambda trade: (trade.entry_ts, trade.exit_ts))

    return tuple(trades)


def _pair_position(position_fills: Sequence[FillReceived], settles: list[datetime]) -> list[Trade]:

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
    capital_pool: Decimal,
    timeline: Sequence[tuple[datetime, Decimal]],
) -> tuple[list[Decimal], int]:

    settles = [settle for settle, _ in timeline]
    by_step: dict[int, list[FillReceived]] = defaultdict(list)

    for fill in fills:
        by_step[_fill_bar(fill, settles)].append(fill)

    cash = capital_pool
    position = _ZERO
    equity: list[Decimal] = []
    in_position_bars = 0

    for index, (_settle, close) in enumerate(timeline):

        for fill in by_step.get(index, ()):
            notional = fill.qty * fill.price

            if fill.side is OrderSide.BUY:
                cash -= notional + fill.fee
                position += fill.qty
            else:
                cash += notional - fill.fee
                position -= fill.qty

        equity.append(cash + position * close)

        if position > _ZERO:
            in_position_bars += 1

    return equity, in_position_bars


def _summarise(
    trades: tuple[Trade, ...],
    equity: list[Decimal],
    in_position_bars: int,
    open_position_qty: Decimal,
    total_fees: Decimal,
    snapshot: dict[str, float | None],
    snapshot_portfolio: dict[str, float | None],
    scalars: dict[str, Decimal],
    capital_pool: Decimal,
    interval_seconds: int,
    step_count: int,
) -> ReplayMetrics:

    wins = [trade for trade in trades if trade.net_pnl > _ZERO]
    losses = [trade for trade in trades if trade.net_pnl < _ZERO]
    loss_total = sum((trade.net_pnl for trade in losses), _ZERO)
    win_total = sum((trade.net_pnl for trade in wins), _ZERO)
    net = sum((trade.net_pnl for trade in trades), _ZERO)

    return ReplayMetrics(
        trade_count=len(trades),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=Decimal(len(wins)) / Decimal(len(trades)) * _HUNDRED if trades else None,
        gross_pnl=sum((trade.gross_pnl for trade in trades), _ZERO),
        net_pnl=net,
        total_fees=total_fees,
        pnl_pct=net / capital_pool * _HUNDRED if capital_pool > _ZERO else _ZERO,
        avg_win=win_total / Decimal(len(wins)) if wins else None,
        avg_loss=loss_total / Decimal(len(losses)) if losses else None,
        profit_factor=win_total / -loss_total if loss_total < _ZERO else None,
        max_drawdown_pct=_max_drawdown_pct(equity),
        sharpe=_sharpe(equity, interval_seconds),
        exposure_pct=Decimal(in_position_bars) / Decimal(step_count) * _HUNDRED if step_count else _ZERO,
        final_equity=equity[-1] if equity else capital_pool + net,
        open_position_qty=open_position_qty,
        snapshot=snapshot,
        snapshot_portfolio=snapshot_portfolio,
        expected_value=scalars['expected_value'],
        net_long_volume=scalars['net_long_volume'],
        net_short_volume=scalars['net_short_volume'],
        net_trade_volume=scalars['net_trade_volume'],
    )


def _max_drawdown_pct(equity: list[Decimal]) -> Decimal:

    if not equity:
        return _ZERO

    peak = equity[0]
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
