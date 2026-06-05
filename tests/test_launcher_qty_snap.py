'''Tests for Vaquum/Praxis#130 — pre-snap `cmd.qty` to venue stepSize.

`_build_enter_context` and `_build_exit_context` accept an optional
`venue_adapter` and route `action.size` through
`venue_adapter.quantize_for_command` before computing
`order_notional`, so the validation request and the eventual
`TradeCommand.qty` are already snapped to the venue's LOT_SIZE grid.

These tests pin: snap-down behavior, INTAKE_BELOW_MIN_QTY rejection
on sub-min sizes, INTAKE_BELOW_MIN_NOTIONAL rejection when the
snapped notional falls below the venue floor, and pre-fix parity
(no `venue_adapter` argument leaves `action.size` untouched).
'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from nexus.core.domain.enums import OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.order_types import ExecutionMode, OrderType
from nexus.core.domain.position import Position
from nexus.core.stp_mode import STPMode
from nexus.instance_config import InstanceConfig as NexusInstanceConfig
from nexus.strategy.action import Action, ActionType

from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.venue_adapter import (
    CommandQuantization,
    SymbolFilters,
)
from praxis.launcher import _build_enter_context, _build_exit_context


def _nexus_config() -> NexusInstanceConfig:

    return NexusInstanceConfig(
        account_id='acct-test',
        venue='binance_spot',
        duplicate_window_ms=1000,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct={'strat-a': Decimal('100')},
    )


_TS = datetime(2026, 6, 5, 0, 0, 0, tzinfo=UTC)
_BTCUSDT_FILTERS = SymbolFilters(
    symbol='BTCUSDT',
    tick_size=Decimal('0.01'),
    lot_step=Decimal('0.00001'),
    lot_min=Decimal('0.00001'),
    lot_max=Decimal('9000.0'),
    min_notional=Decimal('5.0'),
)


def _enter_action(size: Decimal, reference_price: Decimal = Decimal('80000')) -> Action:

    return Action(
        action_type=ActionType.ENTER,
        direction=OrderSide.BUY,
        size=size,
        reference_price=reference_price,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        deadline=30,
    )


def _exit_action(size: Decimal, trade_id: str = 'trade-1') -> Action:

    return Action(
        action_type=ActionType.EXIT,
        direction=OrderSide.SELL,
        size=size,
        trade_id=trade_id,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        order_type=OrderType.MARKET,
        deadline=30,
    )


def _state_with_position() -> InstanceState:

    state = InstanceState.fresh(Decimal('10000'))
    state.positions['trade-1'] = Position(
        trade_id='trade-1',
        strategy_id='strat-a',
        symbol='BTCUSDT',
        size=Decimal('0.001'),
        entry_price=Decimal('80000'),
        side=OrderSide.BUY,
    )
    return state


def _make_real_adapter() -> BinanceAdapter:

    adapter = BinanceAdapter(
        base_url='http://test',
        ws_base_url='ws://test',
        ws_api_url='ws://test-api',
    )
    adapter._filters['BTCUSDT'] = _BTCUSDT_FILTERS
    return adapter


class TestBuildEnterContextQtySnap:

    def test_no_adapter_preserves_action_size(self) -> None:

        action = _enter_action(Decimal('0.0002455253013823074467823909254'))

        ctx = _build_enter_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=InstanceState.fresh(Decimal('10000')),
            strategy_budget=Decimal('1000'),
            fallback_price_provider=lambda: None,
            fee_rate=Decimal('0.001'),
            enter_symbol='BTCUSDT',
            venue_adapter=None,
        )

        assert ctx is not None
        assert ctx.order_size == action.size

    def test_high_precision_size_is_snapped_down_to_lot_step(self) -> None:

        adapter = _make_real_adapter()
        action = _enter_action(Decimal('0.0002455253013823074467823909254'))

        ctx = _build_enter_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=InstanceState.fresh(Decimal('10000')),
            strategy_budget=Decimal('1000'),
            fallback_price_provider=lambda: None,
            fee_rate=Decimal('0.001'),
            enter_symbol='BTCUSDT',
            venue_adapter=adapter,
        )

        assert ctx is not None
        assert ctx.order_size == Decimal('0.00024')
        assert ctx.order_size % _BTCUSDT_FILTERS.lot_step == 0
        assert ctx.order_size <= action.size

    def test_order_notional_reflects_snapped_qty(self) -> None:

        adapter = _make_real_adapter()
        action = _enter_action(
            Decimal('0.0002455253013823074467823909254'),
            reference_price=Decimal('80000'),
        )

        ctx = _build_enter_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=InstanceState.fresh(Decimal('10000')),
            strategy_budget=Decimal('1000'),
            fallback_price_provider=lambda: None,
            fee_rate=Decimal('0.001'),
            enter_symbol='BTCUSDT',
            venue_adapter=adapter,
        )

        assert ctx is not None
        assert ctx.order_notional == Decimal('0.00024') * Decimal('80000')

    def test_below_min_qty_returns_none_with_intake_rejection_logged(self) -> None:

        adapter = _make_real_adapter()
        action = _enter_action(Decimal('0.000001'))

        ctx = _build_enter_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=InstanceState.fresh(Decimal('10000')),
            strategy_budget=Decimal('1000'),
            fallback_price_provider=lambda: None,
            fee_rate=Decimal('0.001'),
            enter_symbol='BTCUSDT',
            venue_adapter=adapter,
        )

        assert ctx is None

    def test_below_min_notional_returns_none(self) -> None:

        adapter = BinanceAdapter(
            base_url='http://test', ws_base_url='ws://test', ws_api_url='ws://test-api',
        )
        adapter._filters['BTCUSDT'] = SymbolFilters(
            symbol='BTCUSDT',
            tick_size=Decimal('0.01'),
            lot_step=Decimal('0.00001'),
            lot_min=Decimal('0.00001'),
            lot_max=Decimal('9000.0'),
            min_notional=Decimal('5.0'),
        )

        action = _enter_action(Decimal('0.00002'), reference_price=Decimal('80000'))

        ctx = _build_enter_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=InstanceState.fresh(Decimal('10000')),
            strategy_budget=Decimal('1000'),
            fallback_price_provider=lambda: None,
            fee_rate=Decimal('0.001'),
            enter_symbol='BTCUSDT',
            venue_adapter=adapter,
        )

        assert ctx is None

    def test_unknown_symbol_passes_qty_through(self) -> None:

        adapter = _make_real_adapter()
        action = _enter_action(Decimal('0.5'))

        ctx = _build_enter_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=InstanceState.fresh(Decimal('10000')),
            strategy_budget=Decimal('1000'),
            fallback_price_provider=lambda: None,
            fee_rate=Decimal('0.001'),
            enter_symbol='UNKNOWN',
            venue_adapter=adapter,
        )

        assert ctx is not None
        assert ctx.order_size == Decimal('0.5')


class TestBuildExitContextQtySnap:

    def test_no_adapter_preserves_action_size(self) -> None:

        action = _exit_action(Decimal('0.0002455253013823074467823909254'))

        ctx = _build_exit_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=_state_with_position(),
            strategy_budget=Decimal('1000'),
            fee_rate=Decimal('0.001'),
            venue_adapter=None,
        )

        assert ctx is not None
        assert ctx.order_size == action.size

    def test_snaps_exit_size_to_lot_step(self) -> None:

        adapter = _make_real_adapter()
        action = _exit_action(Decimal('0.0002455253013823074467823909254'))

        ctx = _build_exit_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=_state_with_position(),
            strategy_budget=Decimal('1000'),
            fee_rate=Decimal('0.001'),
            venue_adapter=adapter,
        )

        assert ctx is not None
        assert ctx.order_size == Decimal('0.00024')
        assert ctx.order_size % _BTCUSDT_FILTERS.lot_step == 0

    def test_order_notional_uses_position_entry_price_with_snapped_size(self) -> None:

        adapter = _make_real_adapter()
        action = _exit_action(Decimal('0.0002455253013823074467823909254'))

        ctx = _build_exit_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=_state_with_position(),
            strategy_budget=Decimal('1000'),
            fee_rate=Decimal('0.001'),
            venue_adapter=adapter,
        )

        assert ctx is not None
        assert ctx.order_notional == Decimal('0.00024') * Decimal('80000')


class TestQuantizationStubInteraction:

    def test_uses_adapter_protocol_method_with_keyword_arg(self) -> None:

        stub_adapter = MagicMock()
        stub_adapter.quantize_for_command.return_value = CommandQuantization(
            snapped_qty=Decimal('0.00024'), rejection_reason=None,
        )

        action = _enter_action(Decimal('0.00024552'))

        ctx = _build_enter_context(
            action=action,
            strategy_id='strat-a',
            nexus_config=_nexus_config(),
            state=InstanceState.fresh(Decimal('10000')),
            strategy_budget=Decimal('1000'),
            fallback_price_provider=lambda: None,
            fee_rate=Decimal('0.001'),
            enter_symbol='BTCUSDT',
            venue_adapter=stub_adapter,
        )

        assert ctx is not None
        assert ctx.order_size == Decimal('0.00024')
        stub_adapter.quantize_for_command.assert_called_once()
        call_kwargs = stub_adapter.quantize_for_command.call_args.kwargs
        assert call_kwargs.get('reference_price') == Decimal('80000')


@pytest.mark.parametrize(
    'raw_size,expected_snapped',
    [
        (Decimal('0.00024999'), Decimal('0.00024')),
        (Decimal('0.00025000'), Decimal('0.00025')),
        (Decimal('1.234567890123'), Decimal('1.23456')),
        (Decimal('0.1'), Decimal('0.10000')),
    ],
)
def test_enter_qty_snap_parametrized(
    raw_size: Decimal, expected_snapped: Decimal,
) -> None:

    adapter = _make_real_adapter()
    action = _enter_action(raw_size)

    ctx = _build_enter_context(
        action=action,
        strategy_id='strat-a',
        nexus_config=_nexus_config(),
        state=InstanceState.fresh(Decimal('10000')),
        strategy_budget=Decimal('1000'),
        fallback_price_provider=lambda: None,
        fee_rate=Decimal('0.001'),
        enter_symbol='BTCUSDT',
        venue_adapter=adapter,
    )

    assert ctx is not None
    assert ctx.order_size == expected_snapped
    assert ctx.order_size <= raw_size
