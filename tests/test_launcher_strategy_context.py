'''Tests for `_build_strategy_context` (PT.2.2).

The helper derives a per-strategy `StrategyContext` from the live
`InstanceState` and loaded `Manifest` exposed by Nexus's
`StartupSequencer`. Drives the runtime `context_provider` injected
into `PredictLoop` and `TimerLoop`.
'''

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from nexus.core.domain.enums import OperationalMode, OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.operational_mode import ModeState, StrategyModeState
from nexus.core.domain.position import Position
from nexus.infrastructure.manifest import Manifest

from praxis.launcher import _build_strategy_context


def _stub_strategy_spec(strategy_id: str, capital_pct: Decimal) -> MagicMock:
    '''Mock StrategySpec — the helper only reads strategy_id + capital_pct.'''

    spec = MagicMock()
    spec.strategy_id = strategy_id
    spec.capital_pct = capital_pct
    return spec


def _stub_manifest(
    strategies: tuple[MagicMock, ...] = (),
    capital_pool: Decimal = Decimal('10000'),
    allocated_capital: Decimal = Decimal('100000'),
) -> Manifest:
    # SensorSpec validates experiment_dir exists; bypass the entire
    # Manifest constructor with a MagicMock that exposes only the
    # fields the helper reads.
    m = MagicMock()
    m.account_id = 'acct-test'
    m.allocated_capital = allocated_capital
    m.capital_pool = capital_pool
    m.strategies = strategies
    return m  # type: ignore[return-value]


def _position(
    trade_id: str,
    strategy_id: str,
    *,
    size: Decimal = Decimal('1'),
    entry_price: Decimal = Decimal('100'),
) -> Position:
    return Position(
        trade_id=trade_id,
        strategy_id=strategy_id,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        size=size,
        entry_price=entry_price,
    )


class TestBuildStrategyContext:

    def test_state_none_returns_halted_zero(self) -> None:
        '''Missing state yields a halted, zero-capital context.'''

        ctx = _build_strategy_context(None, _stub_manifest(), 'strat_a')

        assert ctx.positions == ()
        assert ctx.capital_available == Decimal('0')
        assert ctx.operational_mode == OperationalMode.HALTED

    def test_manifest_none_returns_halted_zero(self) -> None:
        state = InstanceState.fresh(Decimal('10000'))

        ctx = _build_strategy_context(state, None, 'strat_a')

        assert ctx.positions == ()
        assert ctx.capital_available == Decimal('0')
        assert ctx.operational_mode == OperationalMode.HALTED

    def test_unknown_strategy_returns_halted_zero(self) -> None:
        '''Strategy not in manifest yields a halted, zero-capital context.'''

        state = InstanceState.fresh(Decimal('10000'))
        manifest = _stub_manifest(strategies=(
            _stub_strategy_spec('strat_a', Decimal('50')),
        ))

        ctx = _build_strategy_context(state, manifest, 'strat_unknown')

        assert ctx.positions == ()
        assert ctx.capital_available == Decimal('0')
        assert ctx.operational_mode == OperationalMode.HALTED

    def test_capital_available_full_budget_when_nothing_deployed(self) -> None:
        '''capital_available = manifest.capital_pool * capital_pct / 100 when nothing deployed.'''

        state = InstanceState.fresh(Decimal('10000'))
        manifest = _stub_manifest(
            strategies=(_stub_strategy_spec('strat_a', Decimal('40')),),
            capital_pool=Decimal('10000'),
        )

        ctx = _build_strategy_context(state, manifest, 'strat_a')

        assert ctx.capital_available == Decimal('4000')

    def test_capital_available_subtracts_deployed(self) -> None:
        '''capital_available = budget - per_strategy_deployed[strategy_id].'''

        state = InstanceState.fresh(Decimal('10000'))
        state.capital.per_strategy_deployed['strat_a'] = Decimal('1500')
        manifest = _stub_manifest(
            strategies=(_stub_strategy_spec('strat_a', Decimal('40')),),
            capital_pool=Decimal('10000'),
        )

        ctx = _build_strategy_context(state, manifest, 'strat_a')

        assert ctx.capital_available == Decimal('2500')

    def test_capital_available_clamped_to_zero(self) -> None:
        '''Over-deployed strategies surface zero, not a negative value.'''

        state = InstanceState.fresh(Decimal('10000'))
        state.capital.per_strategy_deployed['strat_a'] = Decimal('99999')
        manifest = _stub_manifest(
            strategies=(_stub_strategy_spec('strat_a', Decimal('40')),),
            capital_pool=Decimal('10000'),
        )

        ctx = _build_strategy_context(state, manifest, 'strat_a')

        assert ctx.capital_available == Decimal('0')

    def test_positions_filtered_by_strategy_id(self) -> None:
        '''Only positions for the requested strategy_id are included.'''

        state = InstanceState.fresh(Decimal('10000'))
        pos_a = _position('t1', 'strat_a')
        pos_b = _position('t2', 'strat_b')
        pos_a2 = _position('t3', 'strat_a')
        state.positions['t1'] = pos_a
        state.positions['t2'] = pos_b
        state.positions['t3'] = pos_a2

        manifest = _stub_manifest(strategies=(
            _stub_strategy_spec('strat_a', Decimal('50')),
            _stub_strategy_spec('strat_b', Decimal('50')),
        ))

        ctx_a = _build_strategy_context(state, manifest, 'strat_a')
        ctx_b = _build_strategy_context(state, manifest, 'strat_b')

        assert sorted(p.trade_id for p in ctx_a.positions) == ['t1', 't3']
        assert ctx_b.positions == (pos_b,)

    def test_operational_mode_uses_strategy_specific_when_present(self) -> None:
        '''strategy_modes[sid].state.mode wins over state.mode.mode.'''

        state = InstanceState.fresh(Decimal('10000'))
        state.mode = ModeState(mode=OperationalMode.ACTIVE)
        state.strategy_modes['strat_a'] = StrategyModeState(
            strategy_id='strat_a',
            state=ModeState(mode=OperationalMode.REDUCE_ONLY),
        )
        manifest = _stub_manifest(strategies=(
            _stub_strategy_spec('strat_a', Decimal('50')),
        ))

        ctx = _build_strategy_context(state, manifest, 'strat_a')

        assert ctx.operational_mode == OperationalMode.REDUCE_ONLY

    def test_operational_mode_falls_back_to_instance_mode(self) -> None:
        '''Without a per-strategy entry, instance-level state.mode.mode is used.'''

        state = InstanceState.fresh(Decimal('10000'))
        state.mode = ModeState(mode=OperationalMode.HALTED)
        manifest = _stub_manifest(strategies=(
            _stub_strategy_spec('strat_a', Decimal('50')),
        ))

        ctx = _build_strategy_context(state, manifest, 'strat_a')

        assert ctx.operational_mode == OperationalMode.HALTED
