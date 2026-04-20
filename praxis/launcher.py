'''Process launcher for Praxis + Nexus + Limen.

Single entry point that starts the Trading service, market data poller,
and one Nexus Manager thread per account.
'''

from __future__ import annotations

import asyncio
import logging
import os
import queue
import signal
import sys
import threading
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import aiosqlite
import polars as pl
from aiohttp import web

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
from praxis.infrastructure.observability import bind_context, configure_logging
from praxis.market_data_poller import MarketDataPoller
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.trading import Trading
from praxis.trading_config import TradingConfig

__all__ = ['InstanceConfig', 'Launcher', 'main']

_log = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = (
    'EPOCH_ID',
    'VENUE_REST_URL',
    'VENUE_WS_URL',
    'MANIFESTS_DIR',
    'STRATEGIES_BASE_PATH',
    'STATE_BASE',
)
_DEFAULT_SHUTDOWN_TIMEOUT = '30'
_DEFAULT_HEALTHZ_PORT = 8080


@dataclass(frozen=True)
class InstanceConfig:
    '''Configuration for one Nexus Manager instance.

    Args:
        account_id: Trading account identifier (sourced from manifest).
        manifest_path: Path to strategy manifest YAML.
        strategies_base_path: Base path for strategy .py files.
        state_dir: Directory for WAL and snapshots.
        strategy_state_path: Directory for strategy state blobs.
    '''

    account_id: str
    manifest_path: Path
    strategies_base_path: Path
    state_dir: Path
    strategy_state_path: Path | None = None


class Launcher:
    '''Orchestrates Praxis + Nexus + Limen in one process.

    Args:
        trading_config: Praxis trading configuration.
        instances: One InstanceConfig per Nexus Manager.
        event_spine: Pre-built event spine for Praxis. Mutually exclusive
            with `db_path`.
        db_path: Path to the SQLite file backing the event spine. When
            provided, the launcher opens the connection on its own loop
            and owns its lifecycle. Mutually exclusive with `event_spine`.
        venue_adapter: Optional injected venue adapter.
    '''

    def __init__(
        self,
        trading_config: TradingConfig,
        instances: list[InstanceConfig],
        event_spine: EventSpine | None = None,
        db_path: Path | None = None,
        venue_adapter: VenueAdapter | None = None,
        healthz_port: int | None = None,
    ) -> None:
        if (event_spine is None) == (db_path is None):
            msg = 'Launcher requires exactly one of event_spine or db_path'
            raise ValueError(msg)

        self._trading_config = trading_config
        self._instances = list(instances)
        self._event_spine = event_spine
        self._db_path = db_path
        self._db_conn: aiosqlite.Connection | None = None
        self._owns_spine = event_spine is None
        self._venue_adapter = venue_adapter
        self._healthz_port = healthz_port
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._trading: Trading | None = None
        self._poller: MarketDataPoller | None = None
        self._nexus_threads: list[threading.Thread] = []
        self._healthz_runner: web.AppRunner | None = None

    def launch(self) -> None:
        '''Start Praxis + Nexus in one process.

        Blocks until SIGINT/SIGTERM. Handles graceful shutdown.
        '''

        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        self._start_event_loop()
        self._start_trading()
        self._start_poller()
        self._start_nexus_instances()
        self._start_healthz()

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

        if self._event_spine is None:
            spine_future = asyncio.run_coroutine_threadsafe(
                self._build_event_spine(),
                self._loop,
            )
            self._event_spine = spine_future.result(timeout=30)

        self._trading = Trading(
            config=self._trading_config,
            event_spine=self._event_spine,
            venue_adapter=self._venue_adapter,
        )

        future = asyncio.run_coroutine_threadsafe(self._trading.start(), self._loop)
        future.result(timeout=30)
        _log.info('trading started')

    async def _build_event_spine(self) -> EventSpine:
        if self._db_path is None:
            msg = 'db_path required to build event spine'
            raise RuntimeError(msg)

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_conn = await aiosqlite.connect(str(self._db_path))
        spine = EventSpine(self._db_conn)
        await spine.ensure_schema()

        _log.info('event spine opened', extra={'db_path': str(self._db_path)})
        return spine

    def _start_poller(self) -> None:
        kline_intervals = self._collect_kline_intervals()
        self._poller = MarketDataPoller(kline_intervals=kline_intervals or {})
        self._poller.start()

    def _start_healthz(self) -> None:
        '''Start the /healthz HTTP listener on the launcher's asyncio loop.

        Render polls this endpoint to decide whether to restart the
        container. 200 means Trading is up, the loop thread is alive,
        and every Nexus thread is alive; 503 otherwise.
        '''

        if self._healthz_port is None or self._loop is None:
            return

        future = asyncio.run_coroutine_threadsafe(
            self._build_healthz_runner(self._healthz_port),
            self._loop,
        )
        self._healthz_runner = future.result(timeout=10)
        _log.info('healthz listener started', extra={'port': self._healthz_port})

    def _stop_healthz(self) -> None:
        '''Stop the /healthz listener; subsequent requests will refuse.'''

        if self._healthz_runner is None or self._loop is None:
            return

        future = asyncio.run_coroutine_threadsafe(
            self._healthz_runner.cleanup(),
            self._loop,
        )
        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - best effort during shutdown
            _log.exception('healthz cleanup failed')
        self._healthz_runner = None

    async def _build_healthz_runner(self, port: int) -> web.AppRunner:
        app = web.Application()
        app.router.add_get('/healthz', self._healthz_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host='0.0.0.0', port=port)  # noqa: S104
        await site.start()
        return runner

    async def _healthz_handler(self, _request: web.Request) -> web.Response:
        failures: list[str] = []

        if self._stop_event.is_set():
            failures.append('shutting_down')

        if self._trading is None or not self._trading.started:
            failures.append('trading_not_started')

        if self._loop_thread is None or not self._loop_thread.is_alive():
            failures.append('loop_thread_dead')

        dead_nexus = [
            t.name for t in self._nexus_threads if not t.is_alive()
        ]
        if dead_nexus:
            failures.append(f'nexus_threads_dead:{",".join(dead_nexus)}')

        if failures:
            return web.json_response(
                {'status': 'unhealthy', 'failures': failures},
                status=503,
            )
        return web.json_response({'status': 'ok'})

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
        self._stop_healthz()

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

        if self._owns_spine and self._db_conn is not None and self._loop is not None:
            close_future = asyncio.run_coroutine_threadsafe(
                self._db_conn.close(),
                self._loop,
            )
            close_future.result(timeout=10)
            self._db_conn = None

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
                strategy_state_path=inst.strategy_state_path,
                praxis_outbound=praxis_outbound,
            )

            runner = sequencer.start()

            def market_data_provider(kline_size: int) -> Any:
                if self._poller is None:
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
                manifest = load_manifest(inst.manifest_path)

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


def _check_required_env(env: dict[str, str]) -> None:
    '''Raise if any required env var is missing or empty.'''

    missing = [name for name in _REQUIRED_ENV_VARS if not env.get(name)]
    if missing:
        msg = f'missing required env vars: {", ".join(missing)}'
        raise RuntimeError(msg)


def _account_id_to_env_suffix(account_id: str) -> str:
    '''Normalize an account_id into a valid env-var suffix.

    Replaces non-alphanumeric chars with `_` and uppercases. e.g.
    `acct-001` -> `ACCT_001`.
    '''

    return ''.join(c if c.isalnum() else '_' for c in account_id).upper()


def _enumerate_manifests(manifests_dir: Path) -> list[Path]:
    '''Return globally-sorted list of manifest YAML paths in `manifests_dir`.'''

    if not manifests_dir.is_dir():
        msg = f'MANIFESTS_DIR not a directory: {manifests_dir}'
        raise RuntimeError(msg)

    paths = sorted(list(manifests_dir.glob('*.yaml')) + list(manifests_dir.glob('*.yml')))
    if not paths:
        msg = f'no manifest files (*.yaml/*.yml) found in {manifests_dir}'
        raise RuntimeError(msg)

    return paths


def main() -> None:
    '''Env-driven entrypoint for `python -m praxis.launcher`.

    Reads runtime configuration from the process environment, enumerates
    per-account strategy manifests under `MANIFESTS_DIR`, and starts one
    Trading service plus one Nexus Manager instance per manifest.
    Blocks until SIGINT or SIGTERM.

    Per-account Binance credentials are sourced from env vars
    `BINANCE_API_KEY_<ACCOUNT_ID>` / `BINANCE_API_SECRET_<ACCOUNT_ID>`,
    where `<ACCOUNT_ID>` is the manifest's `account_id` normalized
    (non-alphanumeric -> `_`, uppercased).
    '''

    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    log_format = os.environ.get('LOG_FORMAT', 'json').lower()

    if log_format == 'json':
        configure_logging(log_level=log_level)
    else:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
        )

    env = dict(os.environ)
    _check_required_env(env)

    manifests_dir = Path(env['MANIFESTS_DIR'])
    state_base = Path(env['STATE_BASE'])
    strategies_base_path = Path(env['STRATEGIES_BASE_PATH'])
    strategy_state_base_raw = env.get('STRATEGY_STATE_BASE')
    strategy_state_base = Path(strategy_state_base_raw) if strategy_state_base_raw else None

    manifest_paths = _enumerate_manifests(manifests_dir)

    account_credentials: dict[str, tuple[str, str]] = {}
    instances: list[InstanceConfig] = []
    seen_account_ids: dict[str, Path] = {}
    seen_suffixes: dict[str, str] = {}

    for manifest_path in manifest_paths:
        manifest = load_manifest(manifest_path)
        account_id = manifest.account_id
        suffix = _account_id_to_env_suffix(account_id)

        if account_id in seen_account_ids:
            msg = (
                f'duplicate account_id {account_id!r} across manifests: '
                f'{seen_account_ids[account_id]} and {manifest_path}'
            )
            raise RuntimeError(msg)

        if suffix in seen_suffixes and seen_suffixes[suffix] != account_id:
            msg = (
                f'env-var suffix collision: account_ids '
                f'{seen_suffixes[suffix]!r} and {account_id!r} both normalize to '
                f'{suffix!r}, causing ambiguous BINANCE_API_KEY_{suffix} lookup'
            )
            raise RuntimeError(msg)

        seen_account_ids[account_id] = manifest_path
        seen_suffixes[suffix] = account_id

        api_key = env.get(f'BINANCE_API_KEY_{suffix}')
        api_secret = env.get(f'BINANCE_API_SECRET_{suffix}')

        if not api_key or not api_secret:
            msg = (
                f'missing BINANCE_API_KEY_{suffix} or BINANCE_API_SECRET_{suffix} '
                f'for account {account_id!r} (manifest {manifest_path})'
            )
            raise RuntimeError(msg)

        account_credentials[account_id] = (api_key, api_secret)

        state_dir = state_base / account_id
        strategy_state_path = (
            strategy_state_base / account_id if strategy_state_base is not None else None
        )

        instances.append(
            InstanceConfig(
                account_id=account_id,
                manifest_path=manifest_path,
                strategies_base_path=strategies_base_path,
                state_dir=state_dir,
                strategy_state_path=strategy_state_path,
            ),
        )

    trading_config = TradingConfig(
        epoch_id=int(env['EPOCH_ID']),
        venue_rest_url=env['VENUE_REST_URL'],
        venue_ws_url=env['VENUE_WS_URL'],
        account_credentials=account_credentials,
        shutdown_timeout=float(env.get('SHUTDOWN_TIMEOUT', _DEFAULT_SHUTDOWN_TIMEOUT)),
    )

    port_raw = env.get('PORT') or env.get('HEALTHZ_PORT')
    healthz_port = int(port_raw) if port_raw else _DEFAULT_HEALTHZ_PORT

    bind_context(epoch_id=trading_config.epoch_id)

    launcher = Launcher(
        trading_config=trading_config,
        instances=instances,
        db_path=state_base / 'event_spine.sqlite',
        healthz_port=healthz_port,
    )

    _log.info(
        'launching praxis',
        extra={
            'accounts': sorted(account_credentials.keys()),
            'state_base': str(state_base),
        },
    )
    launcher.launch()


if __name__ == '__main__':
    try:
        main()
    except Exception:  # noqa: BLE001 - top-level entrypoint, log and exit non-zero
        _log.exception('launcher failed')
        sys.exit(1)
