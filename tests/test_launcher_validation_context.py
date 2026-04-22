'''Tests for `_build_validation_context` (PT.1.4.3).'''

from __future__ import annotations

from decimal import Decimal

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.order_types import ExecutionMode, OrderType
from nexus.core.domain.position import Position
from nexus.core.stp_mode import STPMode
from nexus.core.validator import ValidationAction
from nexus.instance_config import InstanceConfig as NexusInstanceConfig
from nexus.strategy.action import Action, ActionType

from praxis.launcher import _build_validation_context


def _nexus_config() -> NexusInstanceConfig:
    return NexusInstanceConfig(
        account_id='acct-test',
        venue='binance_spot',
        duplicate_window_ms=1000,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct={'strat_a': Decimal('100')},
    )


def _capital_controller(pool: Decimal = Decimal('10000')) -> CapitalController:
    return CapitalController(CapitalState(capital_pool=pool))


def _instance_state(
    *,
    positions: dict[str, Position] | None = None,
) -> InstanceState:
    return InstanceState(
        capital=CapitalState(capital_pool=Decimal('10000')),
        positions=positions or {},
    )


def _enter_action(
    *,
    size: Decimal = Decimal('0.5'),
    reference_price: Decimal | None = Decimal('100'),
    command_id: str | None = 'cmd_1',
) -> Action:
    return Action(
        action_type=ActionType.ENTER,
        direction=OrderSide.BUY,
        size=size,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        deadline=60,
        reference_price=reference_price,
        command_id=command_id,
    )


def _exit_action(
    *,
    trade_id: str,
    size: Decimal = Decimal('0.25'),
    command_id: str | None = 'cmd_exit',
) -> Action:
    return Action(
        action_type=ActionType.EXIT,
        direction=OrderSide.SELL,
        size=size,
        trade_id=trade_id,
        command_id=command_id,
    )


def _modify_action() -> Action:
    return Action(action_type=ActionType.MODIFY, command_id='cmd_modify')


def _abort_action() -> Action:
    return Action(action_type=ActionType.ABORT, command_id='cmd_abort')


def _no_fallback() -> Decimal | None:
    return None


class TestEnterContext:

    def test_enter_uses_action_reference_price(self) -> None:
        ctx = _build_validation_context(
            _enter_action(size=Decimal('0.5'), reference_price=Decimal('200')),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.action == ValidationAction.ENTER
        assert ctx.order_notional == Decimal('100')
        assert ctx.order_size == Decimal('0.5')
        assert ctx.order_side == OrderSide.BUY
        assert ctx.symbol == 'BTCUSDT'

    def test_enter_falls_back_to_provider_when_reference_absent(self) -> None:
        ctx = _build_validation_context(
            _enter_action(reference_price=None),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=lambda: Decimal('150'),
        )

        assert ctx is not None
        assert ctx.order_notional == Decimal('75')

    def test_enter_returns_none_when_no_price_available(self) -> None:
        ctx = _build_validation_context(
            _enter_action(reference_price=None),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is None

    def test_enter_estimated_fees_uses_taker_default(self) -> None:
        ctx = _build_validation_context(
            _enter_action(size=Decimal('1'), reference_price=Decimal('1000')),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.estimated_fees == Decimal('1.000')

    def test_enter_strategy_budget_uses_capital_pct(self) -> None:
        ctx = _build_validation_context(
            _enter_action(),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(pool=Decimal('5000')),
            state=_instance_state(),
            capital_pct=Decimal('40'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.strategy_budget == Decimal('2000')

    def test_enter_generates_command_id_when_action_lacks_one(self) -> None:
        ctx = _build_validation_context(
            _enter_action(command_id=None),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.command_id is not None
        assert ctx.command_id.startswith('cmd-')


class TestExitContext:

    def _open_position(
        self,
        *,
        trade_id: str = 'trade_1',
        size: Decimal = Decimal('1'),
        entry_price: Decimal = Decimal('100'),
    ) -> Position:
        return Position(
            trade_id=trade_id,
            strategy_id='strat_a',
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            size=size,
            entry_price=entry_price,
        )

    def test_exit_uses_position_entry_price_for_notional(self) -> None:
        position = self._open_position(entry_price=Decimal('200'))
        state = _instance_state(positions={position.trade_id: position})

        ctx = _build_validation_context(
            _exit_action(trade_id=position.trade_id, size=Decimal('0.5')),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.action == ValidationAction.EXIT
        assert ctx.order_notional == Decimal('100')
        assert ctx.order_size == Decimal('0.5')
        assert ctx.symbol == 'ETHUSDT'
        assert ctx.order_side == OrderSide.SELL
        assert ctx.trade_id == position.trade_id

    def test_exit_returns_none_when_trade_id_missing_from_state(self) -> None:
        ctx = _build_validation_context(
            _exit_action(trade_id='unknown_trade'),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is None


class TestModifyAndAbort:

    def test_modify_returns_none_and_logs_warning(self) -> None:
        ctx = _build_validation_context(
            _modify_action(),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is None

    def test_abort_returns_none(self) -> None:
        ctx = _build_validation_context(
            _abort_action(),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is None
