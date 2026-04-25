'''Tests for PT-FIX-20 — `_ensure_entry_position` + `_build_order_context.forced_trade_id`.

Pre-fix: `_build_enter_context` returned `trade_id=None` for ENTER
actions and `_build_order_context` propagated that into
`OrderContext(trade_id=None, …)`. When the FILLED outcome arrived,
`OutcomeProcessor._handle_fill` → `_grow_position` raised
`RuntimeError('entry fill without trade_id')`. Even with a
`trade_id` populated, no Nexus path inserts into `state.positions`
for a fresh ENTER, so `_grow_position` would still raise
`'entry fill for missing position'`. Round-trips never closed.

Post-fix: launcher mints `trade_id = outcome.command_id` for SUBMITTED
ENTER actions, calls `_ensure_entry_position` to insert a `size=0`
placeholder `Position` at that key, and threads the same id into
`OrderContext` via `forced_trade_id`. The first FILLED outcome grows
the placeholder via VWAP (collapsing to `entry_price = fill_price`
when `old_size == 0`).
'''

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from nexus.core.domain.enums import OperationalMode, OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.position import Position
from nexus.infrastructure.praxis_connector.outcome_processor import OutcomeProcessor
from nexus.infrastructure.praxis_connector.order_context import OrderContext
from nexus.infrastructure.praxis_connector.trade_outcome import TradeOutcome
from nexus.infrastructure.praxis_connector.trade_outcome_type import TradeOutcomeType
from nexus.core.domain.order_types import ExecutionMode, OrderType
from nexus.strategy.action import Action, ActionType

from datetime import UTC, datetime

from praxis.launcher import _ensure_entry_position


_TS = datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)


def _enter_action(reference_price: Decimal | None = Decimal('100')) -> Action:
    return Action(
        action_type=ActionType.ENTER,
        direction=OrderSide.BUY,
        size=Decimal('1'),
        reference_price=reference_price,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        deadline=30,
    )


def _state() -> InstanceState:
    return InstanceState.fresh(Decimal('10000'))


def test_ensure_entry_position_inserts_placeholder() -> None:
    state = _state()
    action = _enter_action()

    _ensure_entry_position(
        state=state,
        action=action,
        strategy_id='strat-a',
        trade_id='cmd-1',
        fallback_price_provider=lambda: None,
    )

    assert 'cmd-1' in state.positions
    pos = state.positions['cmd-1']
    assert pos.trade_id == 'cmd-1'
    assert pos.strategy_id == 'strat-a'
    assert pos.size == Decimal('0')
    assert pos.entry_price == Decimal('100')
    assert pos.side == OrderSide.BUY


def test_ensure_entry_position_uses_fallback_price() -> None:
    state = _state()
    action = _enter_action(reference_price=None)

    _ensure_entry_position(
        state=state,
        action=action,
        strategy_id='strat-a',
        trade_id='cmd-2',
        fallback_price_provider=lambda: Decimal('123.45'),
    )

    assert state.positions['cmd-2'].entry_price == Decimal('123.45')


def test_ensure_entry_position_no_op_when_already_present() -> None:
    '''setdefault keeps the existing Position; idempotent across retries.'''

    state = _state()
    existing = Position(
        trade_id='cmd-3',
        strategy_id='strat-a',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        size=Decimal('5'),
        entry_price=Decimal('99'),
    )
    state.positions['cmd-3'] = existing

    _ensure_entry_position(
        state=state,
        action=_enter_action(reference_price=Decimal('100')),
        strategy_id='strat-a',
        trade_id='cmd-3',
        fallback_price_provider=lambda: None,
    )

    assert state.positions['cmd-3'] is existing


def test_ensure_entry_position_skips_when_no_price() -> None:
    state = _state()
    action = _enter_action(reference_price=None)

    _ensure_entry_position(
        state=state,
        action=action,
        strategy_id='strat-a',
        trade_id='cmd-4',
        fallback_price_provider=lambda: None,
    )

    assert 'cmd-4' not in state.positions


def test_outcome_processor_grows_pre_populated_position() -> None:
    '''End-to-end: pre-populate via _ensure_entry_position, then a FILLED outcome
    grows the Position via VWAP. Confirms the launcher fix unblocks the round-trip.'''

    state = _state()
    state.mode = MagicMock()
    state.mode.mode = OperationalMode.ACTIVE

    _ensure_entry_position(
        state=state,
        action=_enter_action(),
        strategy_id='strat-a',
        trade_id='cmd-X',
        fallback_price_provider=lambda: None,
    )

    capital = MagicMock()
    capital.order_fill.return_value = MagicMock(success=True)
    store = MagicMock()
    processor = OutcomeProcessor(
        capital_controller=capital,
        instance_state=state,
        state_store=store,
    )

    context = OrderContext(
        command_id='cmd-X',
        strategy_id='strat-a',
        trade_id='cmd-X',
        side=OrderSide.BUY,
        order_size=Decimal('1'),
        order_notional=Decimal('100'),
        estimated_fees=Decimal('0.1'),
    )
    fill = TradeOutcome(
        outcome_id='out-1',
        command_id='cmd-X',
        outcome_type=TradeOutcomeType.FILLED,
        timestamp=_TS,
        fill_size=Decimal('1'),
        fill_price=Decimal('100.5'),
        fill_notional=Decimal('100.5'),
        actual_fees=Decimal('0.1'),
    )

    result = processor.process(fill, context)

    assert result.success
    assert state.positions['cmd-X'].size == Decimal('1')
    assert state.positions['cmd-X'].entry_price == Decimal('100.5')
