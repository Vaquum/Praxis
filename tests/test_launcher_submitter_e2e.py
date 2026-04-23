'''End-to-end test for the launcher's action-submission closure (PT.1.4.4).

Exercises the full wiring: strategy-emitted `ENTER` action →
`build_context` → `ValidationPipeline` → `translate_to_trade_command` →
`PraxisOutbound.send_command` (via a test fake). Skips `PredictLoop` /
`TimerLoop` themselves; the loops are thin adapters that call the
`submitter` closure directly and are covered by Nexus's own loop tests.
'''

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.order_types import ExecutionMode, OrderType
from nexus.core.stp_mode import STPMode
from nexus.core.validator import ValidationRequestContext
from nexus.infrastructure.praxis_connector.praxis_outbound import PraxisOutbound
from nexus.instance_config import InstanceConfig as NexusInstanceConfig
from nexus.strategy.action import Action, ActionType
from nexus.strategy.action_submit import submit_actions

from praxis.launcher import (
    _build_validation_context,
    _build_validation_pipeline,
)


def _enter_action() -> Action:
    return Action(
        action_type=ActionType.ENTER,
        direction=OrderSide.BUY,
        size=Decimal('0.01'),
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        deadline=60,
        reference_price=Decimal('50000'),
        command_id='cmd_e2e_1',
    )


def _nexus_config() -> NexusInstanceConfig:
    return NexusInstanceConfig(
        account_id='acct-e2e',
        venue='binance_spot',
        duplicate_window_ms=1000,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct={'strat_a': Decimal('100')},
    )


def _build_submitter(
    praxis_outbound: PraxisOutbound,
) -> Callable[[list[Action], str], None]:
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

    def submitter(actions: list[Action], strategy_id: str) -> None:
        submit_actions(
            actions,
            strategy_id=strategy_id,
            config=nexus_config,
            praxis_outbound=praxis_outbound,
            validator=pipeline,
            build_context=build_context,
            now=lambda: datetime.now(UTC),
        )

    return submitter


def test_enter_action_flows_end_to_end_to_praxis_outbound() -> None:
    '''ENTER Action → validator allow → translate → send_command called once.'''

    praxis_outbound = MagicMock(spec=PraxisOutbound)
    praxis_outbound.send_command.return_value = 'praxis-cmd-id-123'

    submitter = _build_submitter(praxis_outbound)

    submitter([_enter_action()], 'strat_a')

    assert praxis_outbound.send_command.call_count == 1
    (command,) = praxis_outbound.send_command.call_args.args
    assert command.account_id == 'acct-e2e'
    assert command.symbol == 'BTCUSDT'
    assert command.size == Decimal('0.01')
    assert command.side == OrderSide.BUY


def test_submitter_drops_invalid_action_without_crash() -> None:
    '''An EXIT for an unknown trade_id is dropped, no command sent.'''

    praxis_outbound = MagicMock(spec=PraxisOutbound)
    submitter = _build_submitter(praxis_outbound)

    bad_exit = Action(
        action_type=ActionType.EXIT,
        direction=OrderSide.SELL,
        size=Decimal('0.01'),
        trade_id='nonexistent',
        command_id='cmd_exit_bad',
    )

    submitter([bad_exit], 'strat_a')

    praxis_outbound.send_command.assert_not_called()


def test_abort_action_bypasses_validator_and_calls_send_abort() -> None:
    '''ABORT goes straight to send_abort without touching send_command.'''

    praxis_outbound = MagicMock(spec=PraxisOutbound)
    submitter = _build_submitter(praxis_outbound)

    abort = Action(action_type=ActionType.ABORT, command_id='cmd_abort_1')

    submitter([abort], 'strat_a')

    praxis_outbound.send_command.assert_not_called()
    assert praxis_outbound.send_abort.call_count == 1
    kwargs = praxis_outbound.send_abort.call_args.kwargs
    assert kwargs['command_id'] == 'cmd_abort_1'
    assert kwargs['reason'] == 'runtime_strategy_abort'
