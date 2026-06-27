from __future__ import annotations

from datetime import datetime, timedelta, UTC
from decimal import Decimal
from pathlib import Path

import sys

import pytest

from praxis.infrastructure.venue_adapter import SymbolFilters
from praxis.replay.replay_scenario import ReplayBar, ReplayScenario
from praxis.replay.run_replay import _drop_from_sys_path, run_replay

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


def test_run_replay_time_report_reconciles_to_result_fills(tmp_path: Path) -> None:
    result = run_replay(_scenario(), work_dir=tmp_path)

    assert len(result.trades) == 1
    assert result.metrics.trade_count == 1
    assert result.metrics.total_fees == result.fees
    assert result.metrics.open_position_qty == Decimal('0')
    assert result.metrics.gross_pnl == result.trades[0].gross_pnl
    assert result.metrics.net_pnl == result.trades[0].net_pnl
    assert result.metrics.final_equity == Decimal('10000') + result.metrics.net_pnl


def test_run_replay_dollar_report_reconciles_and_bars_held_is_bar_count(
    tmp_path: Path,
) -> None:
    result = run_replay(_dollar_scenario(), work_dir=tmp_path)

    assert len(result.trades) == 1
    assert result.trades[0].bars_held == 1
    assert result.metrics.total_fees == result.fees
    assert result.metrics.open_position_qty == Decimal('0')
    assert result.metrics.final_equity == Decimal('10000') + result.metrics.net_pnl
    assert result.metrics.sharpe is None


def test_drop_from_sys_path_clears_resolved_relative_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    work_dir = Path('run')
    resolved = str(work_dir.resolve())
    sys.path.insert(0, resolved)

    try:
        _drop_from_sys_path(work_dir)
        assert resolved not in sys.path
    finally:
        while resolved in sys.path:
            sys.path.remove(resolved)


def test_run_replay_open_position_realized_pnl_zero(tmp_path: Path) -> None:
    settle = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)
    ts = int((settle - timedelta(seconds=_INTERVAL)).timestamp() * _NS)
    bars = (
        ReplayBar(
            ts_ns=ts, settle=settle, close=60000.0, prediction=1, probability=0.9,
        ),
    )
    scenario = ReplayScenario(
        account_id='replay-acc',
        series=_SERIES,
        interval_seconds=_INTERVAL,
        symbol=_SYMBOL,
        capital_pool=Decimal('10000'),
        filters=_filters(),
        strategy_source=_STRATEGY_SOURCE,
        bars=bars,
    )

    result = run_replay(scenario, work_dir=tmp_path)

    assert result.fills == 1
    assert result.buy_qty > Decimal(0)
    assert result.sell_qty == Decimal(0)
    assert result.realized_pnl == Decimal(0)
    assert result.metrics.trade_count == 0
    assert result.metrics.open_position_qty == result.buy_qty
    assert result.metrics.total_fees == result.fees


def test_run_replay_is_deterministic(tmp_path: Path) -> None:
    first = run_replay(_scenario(), work_dir=tmp_path / 'a')
    second = run_replay(_scenario(), work_dir=tmp_path / 'b')

    assert first == second
