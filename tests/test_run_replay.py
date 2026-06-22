from __future__ import annotations

from datetime import datetime, timedelta, UTC
from decimal import Decimal
from pathlib import Path

from praxis.infrastructure.venue_adapter import SymbolFilters
from praxis.replay.replay_scenario import ReplayBar, ReplayScenario
from praxis.replay.run_replay import run_replay

_SERIES = 'time_15m'
_INTERVAL = 900
_SYMBOL = 'BTCUSDT'
_NS = 1_000_000_000

_STRATEGY_SOURCE = '''
from __future__ import annotations

from decimal import Decimal

from nexus.strategy import Action, Strategy, StrategyContext, StrategyParams
from nexus.strategy.action import ActionType
from nexus.strategy.signal import Signal
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.order_types import ExecutionMode, OrderType

_DEADLINE = 60
_QUOTE = Decimal("1000")


class Strategy(Strategy):

    def on_save(self):
        return b""

    def on_load(self, data):
        pass

    def on_startup(self, params, context):
        return []

    def on_signal(self, signal, params, context):
        pred = signal.get("_preds")

        if pred == 1 and not context.positions:
            return [
                Action(
                    action_type=ActionType.ENTER,
                    direction=OrderSide.BUY,
                    quote_qty=_QUOTE,
                    execution_mode=ExecutionMode.SINGLE_SHOT,
                    order_type=OrderType.MARKET,
                    deadline=_DEADLINE,
                    reference_price=Decimal(str(signal.get("close"))),
                ),
            ]

        if pred == 0 and context.positions:
            position = context.positions[0]
            remaining = position.size - position.pending_exit
            return [
                Action(
                    action_type=ActionType.EXIT,
                    direction=OrderSide.SELL,
                    size=remaining,
                    execution_mode=ExecutionMode.SINGLE_SHOT,
                    order_type=OrderType.MARKET,
                    deadline=_DEADLINE,
                    trade_id=position.trade_id,
                ),
            ]

        return []

    def on_outcome(self, outcome, params, context):
        return []

    def on_timer(self, timer_id, params, context):
        return []

    def on_shutdown(self, params, context):
        return []
'''


def _filters() -> SymbolFilters:
    return SymbolFilters(
        symbol=_SYMBOL,
        tick_size=Decimal('0.01'),
        lot_step=Decimal('0.00001'),
        lot_min=Decimal('0.00001'),
        lot_max=Decimal('9000'),
        min_notional=Decimal('10'),
    )


def _scenario() -> ReplayScenario:
    first_settle = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)
    second_settle = first_settle + timedelta(seconds=_INTERVAL)
    first_open = int((first_settle - timedelta(seconds=_INTERVAL)).timestamp() * _NS)
    second_open = int(first_settle.timestamp() * _NS)

    bars = (
        ReplayBar(
            ts_ns=first_open,
            settle=first_settle,
            close=60000.0,
            prediction=1,
            probability=0.9,
        ),
        ReplayBar(
            ts_ns=second_open,
            settle=second_settle,
            close=61000.0,
            prediction=0,
            probability=0.1,
        ),
    )

    return ReplayScenario(
        account_id='replay-acc',
        series=_SERIES,
        interval_seconds=_INTERVAL,
        symbol=_SYMBOL,
        capital_pool=Decimal('10000'),
        filters=_filters(),
        strategy_source=_STRATEGY_SOURCE,
        bars=bars,
    )


def _dollar_scenario() -> ReplayScenario:
    first_settle = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)
    second_settle = first_settle + timedelta(seconds=433)
    first_settle_ns = int(first_settle.timestamp() * _NS)
    second_settle_ns = int(second_settle.timestamp() * _NS)

    bars = (
        ReplayBar(
            ts_ns=first_settle_ns,
            settle=first_settle,
            close=60000.0,
            prediction=1,
            probability=0.9,
            start_ts_ns=first_settle_ns - 400 * _NS,
        ),
        ReplayBar(
            ts_ns=second_settle_ns,
            settle=second_settle,
            close=61000.0,
            prediction=0,
            probability=0.1,
            start_ts_ns=first_settle_ns,
        ),
    )

    return ReplayScenario(
        account_id='replay-acc',
        series='dollar_60M',
        interval_seconds=300,
        symbol=_SYMBOL,
        capital_pool=Decimal('10000'),
        filters=_filters(),
        strategy_source=_STRATEGY_SOURCE,
        bars=bars,
    )


def test_run_replay_enter_then_exit(tmp_path: Path) -> None:
    result = run_replay(_scenario(), work_dir=tmp_path)

    assert result.bars == 2
    assert result.fills == 2
    assert result.buy_qty > Decimal(0)
    assert result.buy_qty == result.sell_qty
    assert result.fees > Decimal(0)
    assert result.realized_pnl > Decimal(0)
    assert result.outcome_status_counts.get('FILLED', 0) >= 1


def test_run_replay_dollar_bars(tmp_path: Path) -> None:
    result = run_replay(_dollar_scenario(), work_dir=tmp_path)

    assert result.bars == 2
    assert result.fills == 2
    assert result.buy_qty == result.sell_qty
    assert result.buy_qty > Decimal(0)
    assert result.realized_pnl > Decimal(0)


def test_run_replay_is_deterministic(tmp_path: Path) -> None:
    first = run_replay(_scenario(), work_dir=tmp_path / 'a')
    second = run_replay(_scenario(), work_dir=tmp_path / 'b')

    assert first == second
