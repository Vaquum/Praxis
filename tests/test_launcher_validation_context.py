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
from nexus.core.validator.pipeline_models import ValidationRequestContext
from nexus.instance_config import InstanceConfig as NexusInstanceConfig
from nexus.strategy.action import Action, ActionType

from praxis.infrastructure.venue_adapter import CommandQuantization
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


def _quote_native_enter_action(
    *,
    quote_qty: Decimal = Decimal('100'),
    reference_price: Decimal | None = None,
    command_id: str | None = 'cmd_qn',
) -> Action:
    return Action(
        action_type=ActionType.ENTER,
        direction=OrderSide.BUY,
        quote_qty=quote_qty,
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

    def test_enter_quote_native_builds_context_with_quote_qty_as_notional(self) -> None:
        ctx = _build_validation_context(
            _quote_native_enter_action(quote_qty=Decimal('250')),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.action == ValidationAction.ENTER
        assert ctx.order_size is None
        assert ctx.order_notional == Decimal('250')
        assert ctx.order_side == OrderSide.BUY

    def test_enter_quote_native_does_not_require_reference_price(self) -> None:
        ctx = _build_validation_context(
            _quote_native_enter_action(
                quote_qty=Decimal('100'), reference_price=None,
            ),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.order_notional == Decimal('100')

    def test_enter_quote_native_estimated_fees_uses_quote_qty(self) -> None:
        ctx = _build_validation_context(
            _quote_native_enter_action(quote_qty=Decimal('1000')),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=_instance_state(),
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.estimated_fees == Decimal('1.000')

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


class TestExitContextIntendedFullCloseFlag:
    '''Verify `_build_exit_context` computes and propagates
    `intended_full_close` to `ValidationRequestContext` (Vaquum/Praxis#142).
    '''

    def _open_position(
        self,
        *,
        trade_id: str = 'trade_1',
        size: Decimal = Decimal('0.5'),
        pending_exit: Decimal = Decimal('0'),
    ) -> Position:
        return Position(
            trade_id=trade_id,
            strategy_id='strat_a',
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            size=size,
            entry_price=Decimal('100'),
            pending_exit=pending_exit,
        )

    def test_intended_full_close_true_when_action_size_equals_remaining(self) -> None:
        position = self._open_position(size=Decimal('0.5'), pending_exit=Decimal('0'))
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
        assert ctx.intended_full_close is True

    def test_intended_full_close_true_with_pending_exit_offset(self) -> None:
        position = self._open_position(
            size=Decimal('0.5'),
            pending_exit=Decimal('0.2'),
        )
        state = _instance_state(positions={position.trade_id: position})

        ctx = _build_validation_context(
            _exit_action(trade_id=position.trade_id, size=Decimal('0.3')),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.intended_full_close is True

    def test_intended_full_close_false_when_partial_exit(self) -> None:
        position = self._open_position(size=Decimal('0.5'), pending_exit=Decimal('0'))
        state = _instance_state(positions={position.trade_id: position})

        ctx = _build_validation_context(
            _exit_action(trade_id=position.trade_id, size=Decimal('0.25')),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
        )

        assert ctx is not None
        assert ctx.intended_full_close is False


class _FakeVenueAdapterRejecting:
    '''Minimal VenueAdapter stub that always rejects via `quantize_for_command`.

    Used to drive the launcher's intake-rejection branch in tests
    without standing up a full Binance adapter.
    '''

    def __init__(self, reason: str = 'INTAKE_BELOW_MIN_QTY qty=0.0001 lot_min=0.001') -> None:
        self.reason = reason

    def quantize_for_command(
        self,
        _symbol: str,
        _qty: Decimal,
        _order_type: OrderType,
        *,
        reference_price: Decimal,  # noqa: ARG002
    ) -> CommandQuantization:

        return CommandQuantization(snapped_qty=None, rejection_reason=self.reason)


class _RecordingOutcomeProcessor:
    '''OutcomeProcessor stub that records `close_as_dust` calls.

    Used to assert the launcher routes intake-rejected full-close
    EXITs to `close_as_dust(...)` with the correct arguments.
    '''

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def close_as_dust(
        self,
        *,
        trade_id: str,
        reason: str,
        dust_close_id: str,
    ) -> bool:
        self.calls.append(
            {
                'trade_id': trade_id,
                'reason': reason,
                'dust_close_id': dust_close_id,
            },
        )
        return True


class TestExitContextDustCloseRouting:
    '''Verify the launcher's intake-rejection branch routes a full-close
    EXIT to `OutcomeProcessor.close_as_dust(...)` (Vaquum/Praxis#142, B2).
    '''

    def _open_position(
        self,
        *,
        trade_id: str = 'trade_1',
        size: Decimal = Decimal('0.00000842'),
        pending_exit: Decimal = Decimal('0'),
    ) -> Position:
        return Position(
            trade_id=trade_id,
            strategy_id='strat_a',
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            size=size,
            entry_price=Decimal('100'),
            pending_exit=pending_exit,
        )

    def test_full_close_rejection_routes_to_close_as_dust(self) -> None:
        position = self._open_position(size=Decimal('0.00000842'))
        state = _instance_state(positions={position.trade_id: position})
        processor = _RecordingOutcomeProcessor()

        ctx = _build_validation_context(
            _exit_action(
                trade_id=position.trade_id,
                size=Decimal('0.00000842'),
                command_id='cmd_dust',
            ),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
            venue_adapter=_FakeVenueAdapterRejecting(),
            outcome_processor=processor,
        )

        assert ctx is None
        assert len(processor.calls) == 1
        assert processor.calls[0]['trade_id'] == position.trade_id
        assert processor.calls[0]['dust_close_id'] == f'dust-{position.trade_id}'
        assert 'INTAKE_BELOW_MIN_QTY' in processor.calls[0]['reason']

    def test_partial_close_rejection_does_not_route_to_close_as_dust(self) -> None:
        position = self._open_position(
            size=Decimal('0.5'),
            pending_exit=Decimal('0'),
        )
        state = _instance_state(positions={position.trade_id: position})
        processor = _RecordingOutcomeProcessor()

        ctx = _build_validation_context(
            _exit_action(
                trade_id=position.trade_id,
                size=Decimal('0.25'),
                command_id='cmd_partial',
            ),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
            venue_adapter=_FakeVenueAdapterRejecting(),
            outcome_processor=processor,
        )

        assert ctx is None
        assert processor.calls == []

    def test_full_close_rejection_with_pending_exit_does_not_route_to_close_as_dust(self) -> None:
        position = self._open_position(
            size=Decimal('0.03254842'),
            pending_exit=Decimal('0.03254000'),
        )
        state = _instance_state(positions={position.trade_id: position})
        processor = _RecordingOutcomeProcessor()

        ctx = _build_validation_context(
            _exit_action(
                trade_id=position.trade_id,
                size=Decimal('0.00000842'),
                command_id='cmd_inflight',
            ),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
            venue_adapter=_FakeVenueAdapterRejecting(),
            outcome_processor=processor,
        )

        assert ctx is None
        assert processor.calls == []

    def test_full_close_rejection_without_outcome_processor_returns_none(self) -> None:
        position = self._open_position(size=Decimal('0.00000842'))
        state = _instance_state(positions={position.trade_id: position})

        ctx = _build_validation_context(
            _exit_action(
                trade_id=position.trade_id,
                size=Decimal('0.00000842'),
                command_id='cmd_no_proc',
            ),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
            venue_adapter=_FakeVenueAdapterRejecting(),
        )

        assert ctx is None

    def test_dust_close_id_deterministic_when_action_command_id_absent(self) -> None:
        '''When `action.command_id is None`, `_build_exit_context` generates
        a fresh `f'cmd-{uuid.uuid4().hex}'` per call. `dust_close_id` must
        not depend on that fresh UUID — otherwise Nexus-side dedup is
        defeated for any caller that doesn't supply a stable `command_id`.

        Regression for Vaquum/Praxis#143 review: keyed on `trade_id` so
        repeated full-close attempts on the same position produce the
        same `dust_close_id` and dedup catches the second call.
        '''

        position = self._open_position(size=Decimal('0.00000842'))
        state = _instance_state(positions={position.trade_id: position})
        processor = _RecordingOutcomeProcessor()

        _build_validation_context(
            _exit_action(
                trade_id=position.trade_id,
                size=Decimal('0.00000842'),
                command_id=None,
            ),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
            venue_adapter=_FakeVenueAdapterRejecting(),
            outcome_processor=processor,
        )

        _build_validation_context(
            _exit_action(
                trade_id=position.trade_id,
                size=Decimal('0.00000842'),
                command_id=None,
            ),
            'strat_a',
            nexus_config=_nexus_config(),
            capital_controller=_capital_controller(),
            state=state,
            capital_pct=Decimal('100'),
            fallback_price_provider=_no_fallback,
            venue_adapter=_FakeVenueAdapterRejecting(),
            outcome_processor=processor,
        )

        assert len(processor.calls) == 2
        assert processor.calls[0]['dust_close_id'] == processor.calls[1]['dust_close_id']
        assert processor.calls[0]['dust_close_id'] == f'dust-{position.trade_id}'


class TestOrderContextCarriesIntendedFullClose:
    '''Regression for the field-only-on-OrderContext bug codex flagged
    (Vaquum/Praxis#142): `_build_order_context` re-runs `build_context`
    and constructs `OrderContext` from the rebuilt
    `ValidationRequestContext`, so the flag must live on both classes.
    '''

    def _open_position(
        self,
        *,
        trade_id: str = 'trade_1',
        size: Decimal = Decimal('0.5'),
    ) -> Position:
        return Position(
            trade_id=trade_id,
            strategy_id='strat_a',
            symbol='ETHUSDT',
            side=OrderSide.BUY,
            size=size,
            entry_price=Decimal('100'),
        )

    def test_build_order_context_propagates_full_close_flag_from_validation_context(
        self,
    ) -> None:
        from praxis.launcher import _build_order_context

        position = self._open_position(size=Decimal('0.5'))
        state = _instance_state(positions={position.trade_id: position})

        def build_context_for_test(action: Action, strategy_id: str) -> ValidationRequestContext | None:
            return _build_validation_context(
                action,
                strategy_id,
                nexus_config=_nexus_config(),
                capital_controller=_capital_controller(),
                state=state,
                capital_pct=Decimal('100'),
                fallback_price_provider=_no_fallback,
            )

        full_close_action = _exit_action(
            trade_id=position.trade_id,
            size=Decimal('0.5'),
            command_id='cmd_oc_full',
        )

        order_context = _build_order_context(
            action=full_close_action,
            strategy_id='strat_a',
            command_id='cmd_oc_full',
            build_context=build_context_for_test,
        )

        assert order_context is not None
        assert order_context.intended_full_close is True

    def test_build_order_context_propagates_false_on_partial_exit(self) -> None:
        from praxis.launcher import _build_order_context

        position = self._open_position(size=Decimal('0.5'))
        state = _instance_state(positions={position.trade_id: position})

        def build_context_for_test(action: Action, strategy_id: str) -> ValidationRequestContext | None:
            return _build_validation_context(
                action,
                strategy_id,
                nexus_config=_nexus_config(),
                capital_controller=_capital_controller(),
                state=state,
                capital_pct=Decimal('100'),
                fallback_price_provider=_no_fallback,
            )

        partial_action = _exit_action(
            trade_id=position.trade_id,
            size=Decimal('0.25'),
            command_id='cmd_oc_partial',
        )

        order_context = _build_order_context(
            action=partial_action,
            strategy_id='strat_a',
            command_id='cmd_oc_partial',
            build_context=build_context_for_test,
        )

        assert order_context is not None
        assert order_context.intended_full_close is False
