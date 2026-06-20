'''Tests for the launcher's pre-handoff registration (`_make_pre_register`).

The deterministic-command-id fix registers a command's strategy
mapping, capital order, position effect, and `OrderContext` BEFORE the
`send_command` handoff, so a fast venue's ACK/FILL resolves against
state that already exists. These drive the module-level factory with
real `CapitalController` / `InstanceState` and a fake context builder.
'''

from __future__ import annotations

import ast
import inspect
import logging
from collections.abc import Callable
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.order_types import ExecutionMode, OrderType
from nexus.core.stp_mode import STPMode
from nexus.core.validator import ValidationAction
from nexus.core.validator.pipeline_models import (
    ValidationDecision,
    ValidationRequestContext,
)
from nexus.infrastructure.praxis_connector.order_context import OrderContext
from nexus.infrastructure.praxis_connector.trade_command import TradeCommand
from nexus.infrastructure.praxis_connector.trade_command_type import TradeCommandType
from nexus.instance_config import InstanceConfig as NexusInstanceConfig
from nexus.strategy.action import Action, ActionType

from praxis.launcher import (
    _make_pre_register,
    _PreRegisterWiring,
    _UnknownSubmission,
    _UnknownSubmissionMonitor,
)

_NOW = datetime(2026, 6, 13, tzinfo=UTC)


def _enter_action(command_id: str = 'cmd-0000000000000001') -> Action:
    return Action(
        action_type=ActionType.ENTER,
        direction=OrderSide.BUY,
        size=Decimal('0.01'),
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        deadline=60,
        reference_price=Decimal('50000'),
        command_id=command_id,
    )


def _exit_action(
    trade_id: str,
    command_id: str = 'cmd-0000000000000002',
) -> Action:
    return Action(
        action_type=ActionType.EXIT,
        direction=OrderSide.SELL,
        size=Decimal('0.01'),
        trade_id=trade_id,
        command_id=command_id,
    )


def _command(command_id: str, trade_id: str | None = None) -> TradeCommand:
    return TradeCommand(
        command_id=command_id,
        command_type=TradeCommandType.NEW_ORDER,
        account_id='acct-1',
        venue='binance_spot',
        symbol='BTCUSDT',
        notional=Decimal('500'),
        created_at=_NOW,
        side=OrderSide.BUY,
        size=Decimal('0.01'),
        stp_mode=STPMode.CANCEL_TAKER,
        trade_id=trade_id,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        execution_params={},
        deadline=60,
    )


def _config() -> NexusInstanceConfig:
    return NexusInstanceConfig(
        account_id='acct-1',
        venue='binance_spot',
        duplicate_window_ms=1000,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct={'strat_a': Decimal('100')},
    )


def _enter_ctx(command_id: str, state: InstanceState) -> ValidationRequestContext:
    return ValidationRequestContext(
        command_id=command_id,
        strategy_id='strat_a',
        action=ValidationAction.ENTER,
        order_side=OrderSide.BUY,
        order_size=Decimal('0.01'),
        order_notional=Decimal('500'),
        estimated_fees=Decimal('0.5'),
        symbol='BTCUSDT',
        strategy_budget=Decimal('100000'),
        state=state,
        config=_config(),
    )


def _exit_ctx(
    command_id: str,
    trade_id: str,
    state: InstanceState,
) -> ValidationRequestContext:
    return ValidationRequestContext(
        command_id=command_id,
        strategy_id='strat_a',
        action=ValidationAction.EXIT,
        order_side=OrderSide.SELL,
        order_size=Decimal('0.01'),
        order_notional=Decimal('500'),
        estimated_fees=Decimal('0.5'),
        symbol='BTCUSDT',
        trade_id=trade_id,
        strategy_budget=Decimal('100000'),
        state=state,
        config=_config(),
    )


def _wiring(
    state: InstanceState,
    controller: CapitalController,
    pending: dict[str, tuple[Action, str, ValidationRequestContext]],
    contexts: dict[str, OrderContext],
    append_delivery_context: Callable[[str, OrderContext], None] = lambda *_: None,
) -> _PreRegisterWiring:
    return _PreRegisterWiring(
        pending_registrations=pending,
        command_strategy_ids={},
        command_contexts=contexts,
        unknown_submissions={},
        command_registry_lock=threading.Lock(),
        capital_controller=controller,
        state=state,
        positions_lock=threading.Lock(),
        fallback_price_provider=lambda: Decimal('50000'),
        now=lambda: _NOW,
        append_delivery_context=append_delivery_context,
    )


def _granted_decision(
    controller: CapitalController,
) -> ValidationDecision:
    result = controller.check_and_reserve(
        strategy_id='strat_a',
        order_notional=Decimal('500'),
        estimated_fees=Decimal('0.5'),
        strategy_budget=Decimal('100000'),
    )
    assert result.reservation is not None
    return ValidationDecision(allowed=True, reservation=result.reservation)


def test_enter_registers_before_handoff() -> None:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    cmd = _command('cmd-0000000000000001')
    action = _enter_action()
    pending = {cmd.command_id: (action, 'strat_a', _enter_ctx(cmd.command_id, state))}
    contexts: dict[str, OrderContext] = {}
    wiring = _wiring(state, controller, pending, contexts)

    handle = _make_pre_register(wiring)(cmd, _granted_decision(controller))

    assert wiring.command_strategy_ids[cmd.command_id] == 'strat_a'
    assert cmd.command_id in contexts
    assert cmd.command_id in controller._orders
    assert cmd.command_id in state.positions
    handle.mark_submitted(cmd.command_id)


def test_send_order_failure_raises_and_leaves_no_registration() -> None:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    cmd = _command('cmd-0000000000000001')
    action = _enter_action()
    pending = {cmd.command_id: (action, 'strat_a', _enter_ctx(cmd.command_id, state))}
    wiring = _wiring(state, controller, pending, {})

    decision = _granted_decision(controller)
    # consume the reservation under a throwaway id so pre_register's own
    # send_order(reservation_id, cmd.command_id) fails (reservation gone).
    consumed = controller.send_order(
        decision.reservation.reservation_id, 'throwaway-order',
    )
    assert consumed.success

    with pytest.raises(RuntimeError, match='send_order failed'):
        _make_pre_register(wiring)(cmd, decision)

    assert cmd.command_id not in wiring.command_strategy_ids
    assert cmd.command_id not in wiring.command_contexts


def test_post_send_order_exception_rolls_back_capital_and_registry() -> None:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    cmd = _command('cmd-0000000000000001')
    # ENTER with no reference price; the negative fallback makes
    # `_ensure_entry_position`'s `Position(entry_price=...)` raise AFTER
    # `send_order` has consumed the reservation into a capital order.
    action = Action(
        action_type=ActionType.ENTER,
        direction=OrderSide.BUY,
        size=Decimal('0.01'),
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        deadline=60,
        command_id=cmd.command_id,
    )
    pending = {cmd.command_id: (action, 'strat_a', _enter_ctx(cmd.command_id, state))}

    wiring = _PreRegisterWiring(
        pending_registrations=pending,
        command_strategy_ids={},
        command_contexts={},
        unknown_submissions={},
        command_registry_lock=threading.Lock(),
        capital_controller=controller,
        state=state,
        positions_lock=threading.Lock(),
        fallback_price_provider=lambda: Decimal('-1'),
        now=lambda: _NOW,
        append_delivery_context=lambda *_: None,
    )

    with pytest.raises(ValueError):
        _make_pre_register(wiring)(cmd, _granted_decision(controller))

    assert cmd.command_id not in wiring.command_strategy_ids
    assert cmd.command_id not in state.positions
    assert cmd.command_id not in controller._orders


def test_exit_order_context_carries_captured_full_close() -> None:
    from nexus.core.domain.position import Position

    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    state.positions['trade-1'] = Position(
        trade_id='trade-1',
        strategy_id='strat_a',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        size=Decimal('0.05'),
        entry_price=Decimal('50000'),
    )
    cmd = _command('cmd-0000000000000002', trade_id='trade-1')
    action = _exit_action('trade-1')
    ctx = ValidationRequestContext(
        command_id=cmd.command_id,
        strategy_id='strat_a',
        action=ValidationAction.EXIT,
        order_side=OrderSide.SELL,
        order_size=Decimal('0.01'),
        order_notional=Decimal('500'),
        estimated_fees=Decimal('0.5'),
        symbol='BTCUSDT',
        trade_id='trade-1',
        strategy_budget=Decimal('100000'),
        state=state,
        config=_config(),
        intended_full_close=True,
    )
    contexts: dict[str, OrderContext] = {}
    pending = {cmd.command_id: (action, 'strat_a', ctx)}
    wiring = _wiring(state, controller, pending, contexts)

    _make_pre_register(wiring)(cmd, ValidationDecision(allowed=True, reservation=None))

    assert state.positions['trade-1'].pending_exit == Decimal('0.01')
    assert contexts[cmd.command_id].intended_full_close is True


def test_enter_rollback_removes_placeholder() -> None:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    cmd = _command('cmd-0000000000000001')
    pending = {cmd.command_id: (_enter_action(), 'strat_a', _enter_ctx(cmd.command_id, state))}
    wiring = _wiring(state, controller, pending, {})

    handle = _make_pre_register(wiring)(cmd, _granted_decision(controller))
    assert cmd.command_id in state.positions

    handle.rollback(RuntimeError('boom'))

    assert cmd.command_id not in state.positions
    assert cmd.command_id not in wiring.command_strategy_ids


def test_exit_rollback_decrements_pending_exit() -> None:
    from nexus.core.domain.position import Position

    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    state.positions['trade-1'] = Position(
        trade_id='trade-1',
        strategy_id='strat_a',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        size=Decimal('0.05'),
        entry_price=Decimal('50000'),
    )
    cmd = _command('cmd-0000000000000002', trade_id='trade-1')
    action = _exit_action('trade-1')
    pending = {
        cmd.command_id: (action, 'strat_a', _exit_ctx(cmd.command_id, 'trade-1', state)),
    }
    wiring = _wiring(state, controller, pending, {})

    decision = ValidationDecision(allowed=True, reservation=None)
    handle = _make_pre_register(wiring)(cmd, decision)
    assert state.positions['trade-1'].pending_exit == Decimal('0.01')

    handle.rollback(RuntimeError('boom'))

    assert state.positions['trade-1'].pending_exit == Decimal('0')


def test_mark_unknown_retains_registration_and_records_metadata() -> None:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    cmd = _command('cmd-0000000000000001')
    pending = {cmd.command_id: (_enter_action(), 'strat_a', _enter_ctx(cmd.command_id, state))}
    wiring = _wiring(state, controller, pending, {})

    handle = _make_pre_register(wiring)(cmd, _granted_decision(controller))
    handle.mark_unknown(TimeoutError('submit timed out'))

    assert cmd.command_id in wiring.command_strategy_ids
    record = wiring.unknown_submissions[cmd.command_id]
    assert record.command_id == cmd.command_id
    assert record.strategy_id == 'strat_a'
    assert record.created_at == _NOW
    assert record.action_type == ActionType.ENTER.value
    assert record.symbol == 'BTCUSDT'
    assert record.side == OrderSide.BUY.value
    assert record.order_notional == Decimal('500')
    assert record.error == 'submit timed out'


def test_registries_populated_when_send_command_is_entered() -> None:
    from unittest.mock import MagicMock

    from nexus.strategy.action_submit import SubmissionStatus, submit_actions
    from praxis.launcher import _build_validation_pipeline

    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    nexus_config = _config()
    pipeline = _build_validation_pipeline(nexus_config, controller)

    pending: dict[str, tuple[Action, str, ValidationRequestContext]] = {}
    contexts: dict[str, OrderContext] = {}

    def build_context(
        action: Action,
        strategy_id: str,
    ) -> ValidationRequestContext | None:
        from praxis.launcher import _build_validation_context

        return _build_validation_context(
            action,
            strategy_id,
            nexus_config=nexus_config,
            capital_controller=controller,
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=lambda: Decimal('50000'),
        )

    def recording_build_context(
        action: Action,
        strategy_id: str,
    ) -> ValidationRequestContext | None:
        ctx = build_context(action, strategy_id)
        if ctx is not None and ctx.command_id is not None:
            pending[ctx.command_id] = (action, strategy_id, ctx)
        return ctx

    wiring = _PreRegisterWiring(
        pending_registrations=pending,
        command_strategy_ids={},
        command_contexts=contexts,
        unknown_submissions={},
        command_registry_lock=threading.Lock(),
        capital_controller=controller,
        state=state,
        positions_lock=threading.Lock(),
        fallback_price_provider=lambda: Decimal('50000'),
        now=lambda: _NOW,
        append_delivery_context=lambda *_: None,
    )

    observed: dict[str, bool] = {}

    def fake_send_command(cmd: object) -> str:
        cid = cmd.command_id
        observed['strategy_mapped'] = wiring.command_strategy_ids.get(cid) == 'strat_a'
        observed['context_present'] = (
            cid in contexts and contexts[cid].command_id == cid
        )
        observed['order_present'] = cid in controller._orders
        observed['placeholder_present'] = cid in state.positions
        return cid

    outbound = MagicMock()
    outbound.send_command.side_effect = fake_send_command

    results = submit_actions(
        [_enter_action()],
        strategy_id='strat_a',
        config=nexus_config,
        praxis_outbound=outbound,
        validator=pipeline,
        build_context=recording_build_context,
        now=lambda: _NOW,
        capital_controller=controller,
        pre_register=_make_pre_register(wiring),
    )

    assert results[0][1].status == SubmissionStatus.SUBMITTED
    assert observed == {
        'strategy_mapped': True,
        'context_present': True,
        'order_present': True,
        'placeholder_present': True,
    }


def _unknown_record(
    command_id: str,
    created_at: datetime,
) -> _UnknownSubmission:
    return _UnknownSubmission(
        command_id=command_id,
        strategy_id='strat_a',
        created_at=created_at,
        action_type=ActionType.ENTER.value,
        symbol='BTCUSDT',
        side=OrderSide.BUY.value,
        order_notional=Decimal('500'),
        error='send_command timed out',
    )


def test_monitor_scan_silent_below_threshold(
    caplog: pytest.LogCaptureFixture,
) -> None:
    registry = {'cmd-0000000000000001': _unknown_record('cmd-0000000000000001', _NOW)}
    monitor = _UnknownSubmissionMonitor(
        unknown_submissions=registry,
        lock=threading.Lock(),
        now=lambda: _NOW + timedelta(seconds=59),
        warn_seconds=60.0,
        scan_seconds=15.0,
    )

    with caplog.at_level(logging.WARNING):
        monitor.scan_once()

    assert not [r for r in caplog.records if 'SUBMISSION_UNKNOWN' in r.message]


def test_monitor_scan_warns_above_threshold(
    caplog: pytest.LogCaptureFixture,
) -> None:
    registry = {
        'cmd-0000000000000001': _unknown_record('cmd-0000000000000001', _NOW),
        'cmd-0000000000000002': _unknown_record(
            'cmd-0000000000000002', _NOW + timedelta(seconds=30),
        ),
    }
    monitor = _UnknownSubmissionMonitor(
        unknown_submissions=registry,
        lock=threading.Lock(),
        now=lambda: _NOW + timedelta(seconds=120),
        warn_seconds=60.0,
        scan_seconds=15.0,
    )

    with caplog.at_level(logging.WARNING):
        monitor.scan_once()

    warnings = [r for r in caplog.records if 'SUBMISSION_UNKNOWN' in r.message]
    assert len(warnings) == 1
    record = warnings[0]
    assert record.count == 2
    assert record.max_age_seconds == 120.0
    assert set(record.command_ids) == {
        'cmd-0000000000000001',
        'cmd-0000000000000002',
    }


def test_monitor_stop_cancels_pending_scan() -> None:
    monitor = _UnknownSubmissionMonitor(
        unknown_submissions={},
        lock=threading.Lock(),
        now=lambda: _NOW,
        warn_seconds=60.0,
        scan_seconds=15.0,
    )

    monitor.start()
    assert monitor.running

    monitor.stop()

    assert not monitor.running
    assert monitor._timer is None


def _process_outcome_clears_on_success_not_failure() -> bool:
    src = inspect.getsource(__import__('praxis.launcher', fromlist=['launcher']))
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != '_process_nexus_outcome':
            continue
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.If):
                continue
            if not _is_not_result_success_test(stmt.test):
                continue
            failure_pops = _block_pops_unknown(stmt.body)
            success_pops = _block_pops_unknown(stmt.orelse)
            return success_pops and not failure_pops
    return False


def _is_not_result_success_test(test: ast.AST) -> bool:
    if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
        return False
    operand = test.operand
    if not isinstance(operand, ast.Attribute) or operand.attr != 'success':
        return False
    return isinstance(operand.value, ast.Name) and operand.value.id == 'result'


def _block_pops_unknown(block: list[ast.stmt]) -> bool:
    for stmt in block:
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != 'pop':
                continue
            if (
                isinstance(func.value, ast.Name)
                and func.value.id == 'unknown_submissions'
            ):
                return True
    return False


def test_process_outcome_clears_unknown_on_success_only() -> None:
    assert _process_outcome_clears_on_success_not_failure(), (
        'launcher process_outcome must pop unknown_submissions in the '
        'result.success branch and must NOT pop it in the failure branch'
    )


def test_delivery_context_appended_before_registration() -> None:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    cmd = _command('cmd-0000000000000010')
    action = _enter_action()
    pending = {cmd.command_id: (action, 'strat_a', _enter_ctx(cmd.command_id, state))}
    contexts: dict[str, OrderContext] = {}

    recorded: list[tuple[str, OrderContext]] = []

    def _record(account_id: str, ctx: OrderContext) -> None:
        recorded.append((account_id, ctx))

    wiring = _wiring(
        state, controller, pending, contexts, append_delivery_context=_record,
    )

    handle = _make_pre_register(wiring)(cmd, _granted_decision(controller))

    assert len(recorded) == 1
    assert recorded[0][0] == cmd.account_id
    assert recorded[0][1].command_id == cmd.command_id
    handle.mark_submitted(cmd.command_id)


def test_delivery_context_append_failure_aborts_submission() -> None:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    cmd = _command('cmd-0000000000000011')
    action = _enter_action()
    pending = {cmd.command_id: (action, 'strat_a', _enter_ctx(cmd.command_id, state))}
    contexts: dict[str, OrderContext] = {}

    def _boom(_account_id: str, _ctx: OrderContext) -> None:
        raise RuntimeError('append failed')

    wiring = _wiring(
        state, controller, pending, contexts, append_delivery_context=_boom,
    )

    with pytest.raises(RuntimeError, match='append failed'):
        _make_pre_register(wiring)(cmd, _granted_decision(controller))

    assert cmd.command_id not in contexts
    assert cmd.command_id not in wiring.command_strategy_ids
