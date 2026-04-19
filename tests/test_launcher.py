'''Integration test for Launcher lifecycle.

Tests startup → run → shutdown cycle with mock venue adapter.
'''

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import cast

import aiosqlite

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
from praxis.launcher import InstanceConfig, Launcher
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


def _make_manifest_yaml(
    tmp_path: Path,
    exp_dir: Path,
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
        f'    sensors:\n'
        f'      - experiment: {exp_dir}\n'
        f'        permutation_ids: [1]\n'
        f'        interval_seconds: 60\n'
        f'    capital_pct: 100\n'
    )
    return manifest_path


class TestLauncherLifecycle:

    def test_start_and_shutdown(self, tmp_path: Path) -> None:
        '''Launcher starts, runs briefly, then shuts down cleanly.'''

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
                created_at=datetime.now(tz=timezone.utc),
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
            created_at=datetime.now(tz=timezone.utc),
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
                created_at=datetime.now(tz=timezone.utc),
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
            timestamp=datetime.now(tz=timezone.utc),
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

        positions = launcher._trading.pull_positions('test-acc')
        filled = [p for p in positions.values() if p.qty > Decimal('0')]
        assert filled, 'no position after fill'
        assert filled[0].strategy_id == 'momentum_v1'
        assert filled[0].trade_id == 'trade-1'

        stop_future = asyncio.run_coroutine_threadsafe(launcher._trading.stop(), launcher._loop)
        stop_future.result(timeout=10)

        launcher._loop.call_soon_threadsafe(launcher._loop.stop)
        launcher._loop_thread.join(timeout=5)
