'''End-to-end test for the launcher's outcome-flow wiring (PT.3.4).

Exercises: submitter records `command_id → strategy_id` on SUBMITTED
results; OutcomeLoop resolves the mapping for an inbound outcome and
dispatches `on_outcome` with the correct args, including any
returned actions re-entering the submitter (feedback loop).
'''

from __future__ import annotations

import queue
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OperationalMode, OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.order_types import ExecutionMode, OrderType
from nexus.core.outcome_loop import OutcomeLoop
from nexus.core.stp_mode import STPMode
from nexus.core.validator import ValidationRequestContext
from nexus.infrastructure.praxis_connector.praxis_inbound import PraxisInbound
from nexus.infrastructure.praxis_connector.praxis_outbound import PraxisOutbound
from nexus.infrastructure.praxis_connector.trade_outcome import TradeOutcome
from nexus.infrastructure.praxis_connector.trade_outcome_type import TradeOutcomeType
from nexus.instance_config import InstanceConfig as NexusInstanceConfig
from nexus.strategy.action import Action, ActionType
from nexus.strategy.action_submit import SubmissionStatus, submit_actions
from nexus.strategy.context import StrategyContext

from praxis.launcher import (
    _build_validation_context,
    _build_validation_pipeline,
)


def _nexus_config() -> NexusInstanceConfig:
    return NexusInstanceConfig(
        account_id='acct-e2e',
        venue='binance_spot',
        duplicate_window_ms=1000,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct={'strat_a': Decimal('100')},
    )


def _context(_strategy_id: str) -> StrategyContext:
    return StrategyContext(
        positions=(),
        capital_available=Decimal('10000'),
        operational_mode=OperationalMode.ACTIVE,
    )


def _enter_action(command_id: str = 'cmd_pt34_enter') -> Action:
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


def _ack_outcome(command_id: str) -> TradeOutcome:
    return TradeOutcome(
        outcome_id=f'outcome_{command_id}',
        command_id=command_id,
        outcome_type=TradeOutcomeType.ACK,
        timestamp=datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC),
    )


def _build_submitter_and_registry(
    praxis_outbound: PraxisOutbound,
) -> tuple[
    Callable[[list[Action], str], None],
    dict[str, str],
]:
    nexus_config = _nexus_config()
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))
    controller = CapitalController(state.capital)
    pipeline = _build_validation_pipeline(nexus_config, controller)

    def build_context(
        action: Action,
        strategy_id: str,
    ) -> ValidationRequestContext | None:
        return _build_validation_context(
            action,
            strategy_id,
            nexus_config=nexus_config,
            capital_controller=controller,
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=lambda: None,
        )

    command_strategy_ids: dict[str, str] = {}

    def submitter(actions: list[Action], strategy_id: str) -> None:
        results = submit_actions(
            actions,
            strategy_id=strategy_id,
            config=nexus_config,
            praxis_outbound=praxis_outbound,
            validator=pipeline,
            build_context=build_context,
            now=lambda: datetime.now(UTC),
        )

        for _action, outcome in results:
            if (
                outcome.status == SubmissionStatus.SUBMITTED
                and outcome.command_id is not None
            ):
                command_strategy_ids[outcome.command_id] = strategy_id

    return submitter, command_strategy_ids


def test_submitter_populates_command_strategy_registry() -> None:
    '''Registry is keyed by the Praxis-assigned id returned by send_command.'''

    praxis_outbound = MagicMock(spec=PraxisOutbound)
    praxis_outbound.send_command.return_value = 'praxis-cmd-1'

    submitter, registry = _build_submitter_and_registry(praxis_outbound)

    submitter([_enter_action('cmd_reg_1')], 'strat_a')

    assert registry == {'praxis-cmd-1': 'strat_a'}


def test_outcome_loop_dispatches_known_outcome_via_registry() -> None:
    '''Outcome on queue → OutcomeLoop resolves strategy → dispatch_outcome runs.'''

    praxis_outbound = MagicMock(spec=PraxisOutbound)
    praxis_outbound.send_command.return_value = 'praxis-cmd-2'

    submitter, registry = _build_submitter_and_registry(praxis_outbound)

    submitter([_enter_action('cmd_flow_1')], 'strat_a')

    outcome_queue: queue.Queue[TradeOutcome] = queue.Queue()
    outcome_queue.put(_ack_outcome('praxis-cmd-2'))
    inbound = PraxisInbound(outcome_queue=outcome_queue, poll_timeout=0.01)

    runner = MagicMock()
    runner.dispatch_outcome.return_value = []

    def resolve(outcome: Any) -> str | None:
        return registry.get(outcome.command_id)

    loop = OutcomeLoop(
        runner=runner,
        praxis_inbound=inbound,
        state=InstanceState(capital=CapitalState(capital_pool=Decimal('100000'))),
        context_provider=_context,
        resolve_strategy_id=resolve,
        action_submit=submitter,
    )

    assert loop.tick_once() is True

    runner.dispatch_outcome.assert_called_once()
    args = runner.dispatch_outcome.call_args.args
    assert args[0] == 'strat_a'
    assert args[1].command_id == 'praxis-cmd-2'


def test_outcome_loop_skips_orphan_outcome_not_in_registry() -> None:
    '''Outcome for an unregistered command_id is dropped silently.'''

    _, registry = _build_submitter_and_registry(MagicMock(spec=PraxisOutbound))

    outcome_queue: queue.Queue[TradeOutcome] = queue.Queue()
    outcome_queue.put(_ack_outcome('cmd_orphan'))
    inbound = PraxisInbound(outcome_queue=outcome_queue, poll_timeout=0.01)

    runner = MagicMock()

    def resolve(outcome: Any) -> str | None:
        return registry.get(outcome.command_id)

    loop = OutcomeLoop(
        runner=runner,
        praxis_inbound=inbound,
        state=InstanceState(capital=CapitalState(capital_pool=Decimal('100000'))),
        context_provider=_context,
        resolve_strategy_id=resolve,
    )

    assert loop.tick_once() is True
    runner.dispatch_outcome.assert_not_called()


def test_outcome_returned_actions_re_enter_submitter() -> None:
    '''Strategy's on_outcome returned actions flow back through submitter.'''

    praxis_outbound = MagicMock(spec=PraxisOutbound)

    def fake_send_command(command: Any) -> str:
        return f'praxis-{command.command_id}'

    praxis_outbound.send_command.side_effect = fake_send_command

    submitter, registry = _build_submitter_and_registry(praxis_outbound)

    submitter([_enter_action('cmd_entry')], 'strat_a')
    first_call_count = praxis_outbound.send_command.call_count
    entry_praxis_id = next(iter(registry))

    reply_action = _enter_action('cmd_reply')

    outcome_queue: queue.Queue[TradeOutcome] = queue.Queue()
    outcome_queue.put(_ack_outcome(entry_praxis_id))
    inbound = PraxisInbound(outcome_queue=outcome_queue, poll_timeout=0.01)

    runner = MagicMock()
    runner.dispatch_outcome.return_value = [reply_action]

    def resolve(outcome: Any) -> str | None:
        return registry.get(outcome.command_id)

    loop = OutcomeLoop(
        runner=runner,
        praxis_inbound=inbound,
        state=InstanceState(capital=CapitalState(capital_pool=Decimal('100000'))),
        context_provider=_context,
        resolve_strategy_id=resolve,
        action_submit=submitter,
    )

    consumed = loop.tick_once()

    assert consumed is True
    assert praxis_outbound.send_command.call_count == first_call_count + 1
    assert any(sid == 'strat_a' for sid in registry.values())
    assert len(registry) == first_call_count + 1
