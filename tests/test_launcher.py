'''Integration test for Launcher lifecycle.

Tests startup → run → shutdown cycle with mock venue adapter.
'''

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Sequence
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import aiosqlite
import pytest

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    BalanceEntry,
    CancelResult,
    ExecutionReport,
    OrderBookSnapshot,
    SubmitResult,
    SymbolFilters,
    VenueAdapter,
    VenueOrder,
    VenueTrade,
)
from praxis.launcher import _DEFAULT_FEE_RATE, InstanceConfig, Launcher
from praxis.trading_config import TradingConfig


VALID_STRATEGY = '''
from nexus.strategy import Action, Strategy, StrategyContext, StrategyParams
from nexus.strategy.signal import Signal
from nexus.infrastructure.praxis_connector.trade_outcome import TradeOutcome

class Strategy(Strategy):
    def on_save(self) -> bytes:
        return b""

    def on_load(self, data: bytes) -> None:
        pass

    def on_startup(self, params: StrategyParams, context: StrategyContext) -> list[Action]:
        return []

    def on_signal(self, signal: Signal, params: StrategyParams, context: StrategyContext) -> list[Action]:
        return []

    def on_outcome(self, outcome: TradeOutcome, params: StrategyParams, context: StrategyContext) -> list[Action]:
        return []

    def on_timer(self, timer_id: str, params: StrategyParams, context: StrategyContext) -> list[Action]:
        return []

    def on_shutdown(self, params: StrategyParams, context: StrategyContext) -> list[Action]:
        return []
'''


class MockVenueAdapter:
    '''Minimal venue adapter for integration testing.'''

    def register_account(self, account_id: str, api_key: str, api_secret: str) -> None:
        pass

    def unregister_account(self, account_id: str) -> None:
        pass

    async def submit_order(
        self,
        _account_id: str,
        _symbol: str,
        _side: OrderSide,
        _order_type: OrderType,
        _qty: Decimal,
        **_kwargs: object,
    ) -> SubmitResult:
        return SubmitResult(
            venue_order_id='venue-mock-1',
            status=OrderStatus.OPEN,
            immediate_fills=(),
        )

    async def cancel_order(self, _account_id: str, _symbol: str, **_kwargs: object) -> CancelResult:
        return CancelResult(venue_order_id='venue-mock-1', status=OrderStatus.CANCELED)

    async def cancel_order_list(self, _account_id: str, _symbol: str, **_kwargs: object) -> CancelResult:
        return CancelResult(venue_order_id='venue-mock-1', status=OrderStatus.CANCELED)

    async def query_order(self, _account_id: str, _symbol: str, **_kwargs: object) -> VenueOrder:
        from praxis.infrastructure.venue_adapter import NotFoundError
        raise NotFoundError('not found')

    async def query_open_orders(self, _account_id: str, _symbol: str) -> list[VenueOrder]:
        return []

    async def query_balance(self, _account_id: str, _assets: frozenset[str]) -> list[BalanceEntry]:
        return []

    async def query_trades(self, _account_id: str, _symbol: str, **_kwargs: object) -> list[VenueTrade]:
        return []

    async def get_exchange_info(self, _symbol: str) -> SymbolFilters:
        raise NotImplementedError

    async def query_order_book(self, _symbol: str, **_kwargs: object) -> OrderBookSnapshot:
        from praxis.infrastructure.venue_adapter import OrderBookLevel

        bid = OrderBookLevel(price=Decimal('49999'), qty=Decimal('10'))
        ask = OrderBookLevel(price=Decimal('50001'), qty=Decimal('10'))
        return OrderBookSnapshot(bids=(bid,), asks=(ask,), last_update_id=1)

    async def get_server_time(self) -> int:
        raise NotImplementedError

    async def load_filters(self, _symbols: Sequence[str]) -> None:
        pass

    def parse_execution_report(self, _data: dict[str, object]) -> ExecutionReport:
        raise NotImplementedError

    async def close(self) -> None:
        pass


def _make_manifest_yaml(
    tmp_path: Path,
    _exp_dir: Path,
    account_id: str = 'test-acc',
    allocated_capital: int = 10000,
    capital_pool: int = 10000,
) -> Path:
    manifest_path = tmp_path / 'manifest.yaml'
    strategy_file = tmp_path / 'strat.py'
    strategy_file.write_text(VALID_STRATEGY)

    manifest_path.write_text(
        f'account_id: {account_id}\n'
        f'allocated_capital: {allocated_capital}\n'
        f'capital_pool: {capital_pool}\n'
        f'strategies:\n'
        f'  - id: test_strat\n'
        f'    file: strat.py\n'
        f'    signal:\n'
        f'      series: time_15m\n'
        f'      interval_seconds: 900\n'
        f'    capital_pct: 100\n'
    )
    return manifest_path


class TestLauncherLifecycle:

    def test_start_and_shutdown(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        '''Launcher starts, runs briefly, then shuts down cleanly.'''

        monkeypatch.setenv('PRAXIS_CONDUIT_DIR', str(tmp_path / 'conduit'))
        monkeypatch.setenv('PRAXIS_ARROW_DIR', str(tmp_path / 'arrow'))

        exp_dir = tmp_path / 'experiment'
        exp_dir.mkdir()

        state_dir = tmp_path / 'state'
        state_dir.mkdir()

        manifest_path = _make_manifest_yaml(tmp_path, exp_dir)

        config = TradingConfig(epoch_id=1)

        inst = InstanceConfig(
            account_id='test-acc',
            manifest_path=manifest_path,
            strategies_base_path=tmp_path,
            state_dir=state_dir,
        )

        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
        loop_thread.start()

        async def make_spine() -> EventSpine:
            conn = await aiosqlite.connect(':memory:')
            es = EventSpine(conn)
            await es.ensure_schema()
            return es

        spine_future = asyncio.run_coroutine_threadsafe(make_spine(), loop)
        spine = spine_future.result(timeout=5)

        adapter = cast(VenueAdapter, MockVenueAdapter())

        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            event_spine=spine,
            venue_adapter=adapter,
        )

        launcher._stop_event.set()
        launcher.launch()

        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=5)

    def test_submit_command_through_launcher(self, tmp_path: Path) -> None:
        '''Launcher wires Trading so commands can be submitted.'''

        exp_dir = tmp_path / 'experiment'
        exp_dir.mkdir()

        state_dir = tmp_path / 'state'
        state_dir.mkdir()

        manifest_path = _make_manifest_yaml(tmp_path, exp_dir)

        config = TradingConfig(
            epoch_id=1,
            account_credentials={'test-acc': ('key', 'secret')},
        )

        inst = InstanceConfig(
            account_id='test-acc',
            manifest_path=manifest_path,
            strategies_base_path=tmp_path,
            state_dir=state_dir,
        )

        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
        loop_thread.start()

        async def make_spine() -> EventSpine:
            conn = await aiosqlite.connect(':memory:')
            es = EventSpine(conn)
            await es.ensure_schema()
            return es

        spine_future = asyncio.run_coroutine_threadsafe(make_spine(), loop)
        spine = spine_future.result(timeout=5)

        adapter = cast(VenueAdapter, MockVenueAdapter())

        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            event_spine=spine,
            venue_adapter=adapter,
        )

        launcher._start_event_loop()
        launcher._start_trading()

        assert launcher._trading is not None
        assert launcher._trading.started is True

        cmd_future = asyncio.run_coroutine_threadsafe(
            launcher._trading.submit_command(
                trade_id='trade-1',
                account_id='test-acc',
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                qty=Decimal('1'),
                order_type=OrderType.LIMIT,
                execution_mode=ExecutionMode.SINGLE_SHOT,
                execution_params=SingleShotParams(price=Decimal('50000')),
                timeout=300,
                reference_price=None,
                maker_preference=MakerPreference.NO_PREFERENCE,
                stp_mode=STPMode.NONE,
                created_at=datetime.now(tz=UTC),
            ),
            launcher._loop,
        )
        cmd_id = cmd_future.result(timeout=5)
        assert cmd_id is not None

        stop_future = asyncio.run_coroutine_threadsafe(launcher._trading.stop(), launcher._loop)
        stop_future.result(timeout=10)

        launcher._loop.call_soon_threadsafe(launcher._loop.stop)
        launcher._loop_thread.join(timeout=5)

    def test_outcome_routed_to_queue(self, tmp_path: Path) -> None:
        '''Outcomes are routed to the correct account queue.'''

        exp_dir = tmp_path / 'experiment'
        exp_dir.mkdir()

        state_dir = tmp_path / 'state'
        state_dir.mkdir()

        manifest_path = _make_manifest_yaml(tmp_path, exp_dir)

        config = TradingConfig(epoch_id=1)

        inst = InstanceConfig(
            account_id='test-acc',
            manifest_path=manifest_path,
            strategies_base_path=tmp_path,
            state_dir=state_dir,
        )

        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
        loop_thread.start()

        async def make_spine() -> EventSpine:
            conn = await aiosqlite.connect(':memory:')
            es = EventSpine(conn)
            await es.ensure_schema()
            return es

        spine_future = asyncio.run_coroutine_threadsafe(make_spine(), loop)
        spine = spine_future.result(timeout=5)

        adapter = cast(VenueAdapter, MockVenueAdapter())

        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            event_spine=spine,
            venue_adapter=adapter,
        )

        launcher._start_event_loop()
        launcher._start_trading()

        assert launcher._trading is not None

        q: queue.Queue[TradeOutcome] = queue.Queue()
        launcher._trading.register_outcome_queue('test-acc', q)

        from praxis.core.domain.enums import TradeStatus

        outcome = TradeOutcome(
            command_id='cmd-1',
            trade_id='trade-1',
            account_id='test-acc',
            status=TradeStatus.FILLED,
            target_qty=Decimal('1'),
            filled_qty=Decimal('1'),
            avg_fill_price=Decimal('50000'),
            slices_completed=1,
            slices_total=1,
            reason=None,
            created_at=datetime.now(tz=UTC),
            cumulative_notional=Decimal('50000'),
        )

        launcher._trading.route_outcome(outcome)

        routed = q.get(timeout=1)
        assert routed is outcome

        stop_future = asyncio.run_coroutine_threadsafe(launcher._trading.stop(), launcher._loop)
        stop_future.result(timeout=10)

        launcher._loop.call_soon_threadsafe(launcher._loop.stop)
        launcher._loop_thread.join(timeout=5)

    def test_full_cycle_submit_fill_outcome_shutdown(self, tmp_path: Path) -> None:
        '''Full cycle: start → submit command → fill → outcome routed → shutdown.'''

        from praxis.core.domain.events import FillReceived

        exp_dir = tmp_path / 'experiment'
        exp_dir.mkdir()

        state_dir = tmp_path / 'state'
        state_dir.mkdir()

        manifest_path = _make_manifest_yaml(tmp_path, exp_dir)

        outcome_queue: queue.Queue[TradeOutcome] = queue.Queue()

        async def route_to_queue(outcome: TradeOutcome) -> None:
            outcome_queue.put_nowait(outcome)

        config = TradingConfig(
            epoch_id=1,
            account_credentials={'test-acc': ('key', 'secret')},
            on_trade_outcome=route_to_queue,
        )

        inst = InstanceConfig(
            account_id='test-acc',
            manifest_path=manifest_path,
            strategies_base_path=tmp_path,
            state_dir=state_dir,
        )

        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
        loop_thread.start()

        async def make_spine() -> EventSpine:
            conn = await aiosqlite.connect(':memory:')
            es = EventSpine(conn)
            await es.ensure_schema()
            return es

        spine_future = asyncio.run_coroutine_threadsafe(make_spine(), loop)
        spine = spine_future.result(timeout=5)

        adapter = cast(VenueAdapter, MockVenueAdapter())

        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            event_spine=spine,
            venue_adapter=adapter,
        )

        launcher._start_event_loop()
        launcher._start_trading()

        assert launcher._trading is not None

        cmd_future = asyncio.run_coroutine_threadsafe(
            launcher._trading.submit_command(
                trade_id='trade-1',
                account_id='test-acc',
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                qty=Decimal('1'),
                order_type=OrderType.LIMIT,
                execution_mode=ExecutionMode.SINGLE_SHOT,
                execution_params=SingleShotParams(price=Decimal('50000')),
                timeout=300,
                reference_price=None,
                maker_preference=MakerPreference.NO_PREFERENCE,
                stp_mode=STPMode.NONE,
                created_at=datetime.now(tz=UTC),
                strategy_id='momentum_v1',
            ),
            launcher._loop,
        )
        cmd_id = cmd_future.result(timeout=5)

        import time
        time.sleep(0.5)

        runtime = launcher._trading.execution_manager._accounts['test-acc']
        orders = {**runtime.trading_state.orders, **runtime.trading_state.closed_orders}
        client_order_id = next(iter(orders))

        fill = FillReceived(
            account_id='test-acc',
            timestamp=datetime.now(tz=UTC),
            client_order_id=client_order_id,
            venue_order_id='venue-mock-1',
            venue_trade_id='vtrade-1',
            trade_id='trade-1',
            command_id=cmd_id,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            price=Decimal('50000'),
            fee=Decimal('0.01'),
            fee_asset='USDT',
            is_maker=False,
        )

        async def inject_fill() -> None:
            launcher._trading.execution_manager.enqueue_ws_event('test-acc', fill)

        asyncio.run_coroutine_threadsafe(inject_fill(), launcher._loop).result(timeout=5)

        time.sleep(0.5)

        async def read_spine_events() -> list[Any]:
            entries = await spine.read(epoch_id=config.epoch_id)
            return [evt for _seq, evt in entries]

        events = asyncio.run_coroutine_threadsafe(read_spine_events(), launcher._loop).result(timeout=5)
        outcome_events = [
            e for e in events
            if e.__class__.__name__ == 'TradeOutcomeProduced'
            and e.command_id == cmd_id
        ]
        terminal_outcomes = [
            e for e in outcome_events
            if e.status.value == 'FILLED'
        ]
        assert terminal_outcomes, (
            f'no FILLED TradeOutcomeProduced for {cmd_id} after WS fill; '
            f'all outcome events: {[(e.status.value) for e in outcome_events]}'
        )

        positions = launcher._trading.pull_positions('test-acc')
        assert ('trade-1', 'test-acc') in positions, (
            f'entry position must survive a FILLED outcome — an entry fill '
            f'no longer emits TradeClosed, so the position stays tracked and '
            f'is recoverable across a restart; got {positions}'
        )
        assert positions[('trade-1', 'test-acc')].qty == Decimal('1')

        stop_future = asyncio.run_coroutine_threadsafe(launcher._trading.stop(), launcher._loop)
        stop_future.result(timeout=10)

        launcher._loop.call_soon_threadsafe(launcher._loop.stop)
        launcher._loop_thread.join(timeout=5)

    def test_build_failure_sets_stop_event_and_unwinds(self, tmp_path: Path) -> None:
        '''PT-FIX-24: When `_build_nexus_runtime` raises, `_run_nexus_instance`
        must set `_stop_event` so `launch()` exits the wait, runs `_shutdown`,
        and the process can return non-zero. Pre-fix the exception was caught
        and logged, the per-instance thread died, but the launcher kept
        sleeping on `_stop_event.wait()` forever — paper trade with one
        manifest left Praxis "alive" doing nothing, with no auto-exit.'''

        exp_dir = tmp_path / 'experiment'
        exp_dir.mkdir()
        state_dir = tmp_path / 'state'
        state_dir.mkdir()

        manifest_path = _make_manifest_yaml(tmp_path, exp_dir)
        config = TradingConfig(epoch_id=1)
        inst = InstanceConfig(
            account_id='test-acc',
            manifest_path=manifest_path,
            strategies_base_path=tmp_path,
            state_dir=state_dir,
        )

        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
        loop_thread.start()

        async def make_spine() -> EventSpine:
            conn = await aiosqlite.connect(':memory:')
            es = EventSpine(conn)
            await es.ensure_schema()
            return es

        spine = asyncio.run_coroutine_threadsafe(make_spine(), loop).result(timeout=5)

        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            event_spine=spine,
            venue_adapter=cast(VenueAdapter, MockVenueAdapter()),
        )

        def _broken_build(*_args: object, **_kwargs: object) -> object:
            msg = 'simulated build failure'
            raise RuntimeError(msg)

        launcher._build_nexus_runtime = _broken_build  # type: ignore[method-assign]

        launch_thread = threading.Thread(target=launcher.launch, daemon=True)
        launch_thread.start()
        launch_thread.join(timeout=30)

        try:
            assert not launch_thread.is_alive(), (
                'launch() did not return after build failure — _stop_event '
                'was not set, so the launcher hung on the wait'
            )
            assert launcher._stop_event.is_set()
        finally:
            loop.call_soon_threadsafe(loop.stop)
            loop_thread.join(timeout=5)


class TestLauncherFeeRateWiring:
    '''The launcher wires the outcome translator with the venue fee rate.'''

    def test_outcome_translator_uses_default_fee_rate(self, tmp_path: Path) -> None:
        '''Settled fills carry the venue fee, not the zero-fee default.

        The reservation path already estimates fees at `_DEFAULT_FEE_RATE`;
        the outcome translator must use the same rate so realized fees
        flowing to Nexus match the reservation and the venue charge,
        instead of the translator's testnet-era zero default.
        '''

        config = TradingConfig(epoch_id=1)
        inst = InstanceConfig(
            account_id='test-acc',
            manifest_path=tmp_path / 'manifest.yaml',
            strategies_base_path=tmp_path,
            state_dir=tmp_path,
        )
        adapter = cast(VenueAdapter, MockVenueAdapter())

        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            db_path=tmp_path / 'spine.db',
            venue_adapter=adapter,
        )

        assert Decimal('0') < _DEFAULT_FEE_RATE
        assert launcher._outcome_translator._fee_rate == _DEFAULT_FEE_RATE
