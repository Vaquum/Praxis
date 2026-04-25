'''Tests for `_build_strategy_context` (PT.2.2).

The helper derives a per-strategy `StrategyContext` from the live
`InstanceState` and loaded `Manifest` exposed by Nexus's
`StartupSequencer`. Drives the runtime `context_provider` injected
into `PredictLoop` and `TimerLoop`.
'''

from __future__ import annotations

import threading
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from nexus.core.capital_controller.capital_controller import CapitalController
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
    '''Build a Manifest stub via MagicMock to bypass SensorSpec validation.'''

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


class TestContextReflectsReservations:
    '''PT.2.3 — next context_provider call reflects capital reservations.

    `CapitalController.check_and_reserve` mutates the shared
    `state.capital.per_strategy_deployed` dict; `_build_strategy_context`
    reads that dict on every call and derives `capital_available` from it,
    so a successful reservation shows up on the very next tick without
    any explicit plumbing between the two.
    '''

    def test_capital_available_drops_by_reservation_notional_plus_fees(
        self,
    ) -> None:
        '''After an ENTER reservation, next call sees reduced capital_available.'''

        capital_pool = Decimal('10000')
        state = InstanceState.fresh(capital_pool)
        manifest = _stub_manifest(
            strategies=(_stub_strategy_spec('strat_a', Decimal('100')),),
            capital_pool=capital_pool,
        )
        controller = CapitalController(state.capital)

        first = _build_strategy_context(state, manifest, 'strat_a')

        assert first.capital_available == capital_pool

        order_notional = Decimal('1000')
        estimated_fees = Decimal('1')

        result = controller.check_and_reserve(
            strategy_id='strat_a',
            order_notional=order_notional,
            estimated_fees=estimated_fees,
            strategy_budget=capital_pool,
        )

        assert result.granted

        second = _build_strategy_context(state, manifest, 'strat_a')

        assert second.capital_available == (
            capital_pool - order_notional - estimated_fees
        )

    def test_reservation_for_other_strategy_does_not_affect_this_one(
        self,
    ) -> None:
        '''Per-strategy deployed isolation — one strategy's reservation
        must not reduce the other's view.'''

        capital_pool = Decimal('10000')
        state = InstanceState.fresh(capital_pool)
        manifest = _stub_manifest(
            strategies=(
                _stub_strategy_spec('strat_a', Decimal('50')),
                _stub_strategy_spec('strat_b', Decimal('50')),
            ),
            capital_pool=capital_pool,
        )
        controller = CapitalController(state.capital)

        controller.check_and_reserve(
            strategy_id='strat_b',
            order_notional=Decimal('1000'),
            estimated_fees=Decimal('1'),
            strategy_budget=Decimal('5000'),
        )

        ctx = _build_strategy_context(state, manifest, 'strat_a')

        assert ctx.capital_available == Decimal('5000')


class TestPositionsLock:
    '''PT-FIX-28: `_build_strategy_context` reads `state.positions.values()`
    on PredictLoop / TimerLoop threads while `process_outcome` deletes
    terminal-entry placeholder entries on the OutcomeLoop thread. Without
    the shared lock, the `del` racing the iteration raises
    `RuntimeError: dictionary changed size during iteration`, which is
    silently swallowed by the predict loop's broad except → tick lost,
    signal dropped.'''

    def test_concurrent_del_and_context_read_is_race_free(self) -> None:
        capital_pool = Decimal('10000')
        state = InstanceState.fresh(capital_pool)
        manifest = _stub_manifest(
            strategies=(_stub_strategy_spec('strat_a', Decimal('100')),),
            capital_pool=capital_pool,
        )
        for i in range(50):
            state.positions[f'trade-{i}'] = _position(f'trade-{i}', 'strat_a')

        positions_lock = threading.Lock()
        errors: list[BaseException] = []
        error_lock = threading.Lock()
        stop_event = threading.Event()

        def writer() -> None:
            try:
                for _ in range(200):
                    for i in range(50):
                        key = f'trade-{i}'
                        with positions_lock:
                            state.positions.pop(key, None)
                        with positions_lock:
                            state.positions[key] = _position(key, 'strat_a')
            except BaseException as exc:
                with error_lock:
                    errors.append(exc)
            finally:
                stop_event.set()

        def reader() -> None:
            try:
                while not stop_event.is_set():
                    ctx = _build_strategy_context(
                        state, manifest, 'strat_a',
                        positions_lock=positions_lock,
                    )
                    _ = len(ctx.positions)
            except BaseException as exc:
                with error_lock:
                    errors.append(exc)

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        threads.append(threading.Thread(target=writer, daemon=True))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f'concurrent access raised: {errors[:3]}'

    def test_unlocked_read_can_observe_dict_changed_during_iteration(self) -> None:
        '''Sanity: without the lock, the bug exists. This test deliberately
        proves the race is observable; with the lock (above) it must NOT.'''

        capital_pool = Decimal('10000')
        state = InstanceState.fresh(capital_pool)
        manifest = _stub_manifest(
            strategies=(_stub_strategy_spec('strat_a', Decimal('100')),),
            capital_pool=capital_pool,
        )
        for i in range(200):
            state.positions[f'trade-{i}'] = _position(f'trade-{i}', 'strat_a')

        observed_runtime_error = threading.Event()
        stop_event = threading.Event()

        def writer() -> None:
            try:
                for _ in range(2000):
                    if stop_event.is_set():
                        return
                    for i in range(200):
                        key = f'trade-{i}'
                        state.positions.pop(key, None)
                        state.positions[key] = _position(key, 'strat_a')
            finally:
                stop_event.set()

        def reader() -> None:
            while not stop_event.is_set():
                try:
                    _build_strategy_context(state, manifest, 'strat_a')
                except RuntimeError as exc:
                    if 'dictionary changed size' in str(exc):
                        observed_runtime_error.set()
                        return

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        threads.append(threading.Thread(target=writer, daemon=True))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        if not observed_runtime_error.is_set():
            pytest.skip(
                'race did not trigger in this run; CPython did not interleave '
                'reader and writer in a way that exposed the bug — the '
                "absence of an observation here doesn't disprove the race"
            )
