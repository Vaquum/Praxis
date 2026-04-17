'''Process launcher for Praxis + Nexus + Limen.

Single entry point that starts the Trading service, market data poller,
and one Nexus Manager thread per account.
'''

from __future__ import annotations

import asyncio
import logging
import queue
import signal
import threading
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from nexus.core.domain.enums import OperationalMode
from nexus.infrastructure.manifest import load_manifest
from nexus.infrastructure.praxis_connector.praxis_inbound import PraxisInbound
from nexus.infrastructure.praxis_connector.praxis_outbound import PraxisOutbound
from nexus.infrastructure.state_store import StateStore
from nexus.startup.sequencer import StartupSequencer
from nexus.startup.shutdown_sequencer import ShutdownSequencer
from nexus.strategy.context import StrategyContext
from nexus.strategy.predict_loop import PredictLoop
from nexus.strategy.timer_loop import TimerLoop

from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.infrastructure.event_spine import EventSpine
from praxis.market_data_poller import MarketDataPoller
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.trading import Trading
from praxis.trading_config import TradingConfig

__all__ = ['InstanceConfig', 'Launcher']

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstanceConfig:
    '''Configuration for one Nexus Manager instance.

    Args:
        account_id: Trading account identifier.
        manifest_path: Path to strategy manifest YAML.
        strategies_base_path: Base path for strategy .py files.
        allocated_capital: Hard ceiling for capital_pool.
        state_dir: Directory for WAL and snapshots.
        strategy_state_path: Directory for strategy state blobs.
    '''

    account_id: str
    manifest_path: Path
    strategies_base_path: Path
    allocated_capital: Decimal
    state_dir: Path
    strategy_state_path: Path | None = None


class Launcher:
    '''Orchestrates Praxis + Nexus + Limen in one process.

    Args:
        trading_config: Praxis trading configuration.
        instances: One InstanceConfig per Nexus Manager.
        event_spine: Shared event spine for Praxis.
    '''

    def __init__(
        self,
        trading_config: TradingConfig,
        instances: list[InstanceConfig],
        event_spine: EventSpine,
        venue_adapter: VenueAdapter | None = None,
    ) -> None:
        self._trading_config = trading_config
        self._instances = list(instances)
        self._event_spine = event_spine
        self._venue_adapter = venue_adapter
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._trading: Trading | None = None
        self._poller: MarketDataPoller | None = None
        self._nexus_threads: list[threading.Thread] = []

    def launch(self) -> None:
        '''Start Praxis + Nexus in one process.

        Blocks until SIGINT/SIGTERM. Handles graceful shutdown.
        '''

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._start_event_loop()
        self._start_trading()
        self._start_poller()
        self._start_nexus_instances()

        _log.info('all nexus instances started', extra={'count': len(self._nexus_threads)})

        self._stop_event.wait()

        _log.info('shutting down')
        self._shutdown()

    def _signal_handler(self, _signum: int, _frame: Any) -> None:
        _log.info('shutdown signal received')
        self._stop_event.set()

    def _start_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name='asyncio-loop',
        )
        self._loop_thread.start()

    def _start_trading(self) -> None:
        if self._loop is None:
            msg = 'event loop not started'
            raise RuntimeError(msg)

        self._trading = Trading(
            config=self._trading_config,
            event_spine=self._event_spine,
            venue_adapter=self._venue_adapter,
        )

        future = asyncio.run_coroutine_threadsafe(self._trading.start(), self._loop)
        future.result(timeout=30)
        _log.info('trading started')

    def _start_poller(self) -> None:
        kline_intervals = self._collect_kline_intervals()
        self._poller = MarketDataPoller(kline_intervals=kline_intervals or {})
        self._poller.start()

    def _start_nexus_instances(self) -> None:
        if self._trading is None or self._loop is None:
            msg = 'trading not started'
            raise RuntimeError(msg)

        for inst in self._instances:
            outcome_queue: queue.Queue[TradeOutcome] = queue.Queue()
            self._trading.register_outcome_queue(inst.account_id, outcome_queue)

            thread = threading.Thread(
                target=self._run_nexus_instance,
                args=(inst, outcome_queue),
                daemon=True,
                name=f'nexus-{inst.account_id}',
            )
            self._nexus_threads.append(thread)
            thread.start()

    def _shutdown(self) -> None:
        for thread in self._nexus_threads:
            thread.join(timeout=30)

            if thread.is_alive():
                _log.warning(
                    'nexus thread did not finish within timeout',
                    extra={'thread': thread.name},
                )

        if self._poller is not None:
            self._poller.stop()

        if self._trading is not None and self._loop is not None:
            future = asyncio.run_coroutine_threadsafe(self._trading.stop(), self._loop)
            future.result(timeout=30)

        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._loop_thread is not None:
            self._loop_thread.join(timeout=5)

        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()

        self._loop = None
        self._loop_thread = None

        _log.info('shutdown complete')

    def _run_nexus_instance(
        self,
        inst: InstanceConfig,
        outcome_queue: queue.Queue[TradeOutcome],
    ) -> None:
        '''Run one Nexus Manager instance in its own thread.'''

        if self._trading is None or self._loop is None:
            return

        try:
            state_store = StateStore(inst.state_dir)

            praxis_outbound = PraxisOutbound(
                submit_fn=self._trading.submit_command,
                loop=self._loop,
                register_fn=self._trading.register_account,
                unregister_fn=self._trading.unregister_account,
                pull_positions_fn=self._trading.pull_positions,
            )

            sequencer = StartupSequencer(
                state_store=state_store,
                manifest_path=inst.manifest_path,
                strategies_base_path=inst.strategies_base_path,
                allocated_capital=inst.allocated_capital,
                strategy_state_path=inst.strategy_state_path,
                praxis_outbound=praxis_outbound,
                account_id=inst.account_id,
            )

            runner = sequencer.start()

            def market_data_provider(kline_size: int) -> Any:
                if self._poller is None:
                    import polars as pl
                    return pl.DataFrame()
                return self._poller.get_market_data(kline_size)

            def context_provider(_strategy_id: str) -> StrategyContext:
                return StrategyContext(
                    positions=(),
                    capital_available=Decimal('0'),
                    operational_mode=OperationalMode.ACTIVE,
                )

            predict_loop = PredictLoop(
                runner=runner,
                wired_sensors=sequencer.wired_sensors,
                market_data_provider=market_data_provider,
                context_provider=context_provider,
            )
            predict_loop.start()

            timer_loop: TimerLoop | None = None

            if sequencer.timer_specs:
                timer_loop = TimerLoop(
                    runner=runner,
                    strategy_timers=sequencer.timer_specs,
                    context_provider=context_provider,
                )
                timer_loop.start()

            praxis_inbound = PraxisInbound(outcome_queue=outcome_queue)

            _log.info('nexus instance running', extra={'account_id': inst.account_id})

            self._stop_event.wait()

            # NOTE: accessing private attrs on StartupSequencer — no public
            # accessors exist in Nexus as of v0.26.0. Track in Nexus TD.
            shutdown = ShutdownSequencer(
                runner=runner,
                manifest=sequencer._manifest,
                state_store=state_store,
                state=sequencer._state,
                strategy_state_path=inst.strategy_state_path or inst.state_dir / 'strategy_state',
                predict_loop=predict_loop,
                timer_loop=timer_loop,
                praxis_outbound=praxis_outbound,
                praxis_inbound=praxis_inbound,
                account_id=inst.account_id,
            )
            shutdown.shutdown()

            _log.info('nexus instance stopped', extra={'account_id': inst.account_id})

        except Exception:  # noqa: BLE001 - top-level catch for thread, must not propagate
            _log.exception('nexus instance failed', extra={'account_id': inst.account_id})

    def _collect_kline_intervals(self) -> dict[int, int]:
        '''Extract kline_size → min poll interval from all manifests.'''

        kline_intervals: dict[int, int] = {}

        for inst in self._instances:
            try:
                manifest = load_manifest(inst.manifest_path, inst.allocated_capital)

                for spec in manifest.strategies:
                    for sensor in spec.sensors:
                        config = getattr(
                            getattr(sensor, '_limen_manifest', None),
                            'data_source_config',
                            None,
                        )

                        kline_size = None

                        if config is not None:
                            kline_size = config.params.get('kline_size')

                        if kline_size is not None:
                            current = kline_intervals.get(int(kline_size))
                            interval = sensor.interval_seconds

                            if current is None or interval < current:
                                kline_intervals[int(kline_size)] = interval
            except Exception:  # noqa: BLE001 - best-effort extraction, skip on failure
                _log.exception(
                    'failed to extract kline intervals from manifest',
                    extra={'account_id': inst.account_id},
                )

        return kline_intervals
