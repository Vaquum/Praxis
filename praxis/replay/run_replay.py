'''Drive the live trading pipeline over historical bars at simulated time.

`run_replay` boots an isolated Launcher — a throwaway event spine, a
`ReplayVenueAdapter`, and a `ReplayClock` — using the real per-account
wiring (`StartupSequencer`, validator pipeline, `ExecutionManager`,
`OutcomeProcessor`) built but with its realtime loops left unstarted.
It then walks the scenario's settle-ordered bars, and for each one
materializes the Conduit/OHLCV frames, sets the fill price, advances the
clock, runs `PredictLoop.tick_once`, and settles the bar's commands and
outcomes deterministically (`ExecutionManager.quiesce` +
`OutcomeLoop.tick_once`) before moving on. Results are read back from the
spine.

Because every component runs on the same simulated clock and the
synchronous replay adapter fills at the bar close, a run is
deterministic: the same scenario yields the same fills and PnL.
'''

from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

from nexus.core.domain.enums import OperationalMode
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.operational_mode import ModeState

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived, TradeOutcomeProduced
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.launcher import InstanceConfig, Launcher, _NexusRuntime
from praxis.replay.materialize_bar_frames import materialize_bar_frames
from praxis.replay.replay_clock import ReplayClock
from praxis.replay.replay_scenario import ReplayScenario
from praxis.replay.build_replay_report import build_replay_report
from praxis.replay.replay_report import ReplayMetrics, Trade
from praxis.replay.replay_venue_adapter import ReplayVenueAdapter
from praxis.trading import Trading
from praxis.trading_config import TradingConfig

__all__ = ['ReplayResult', 'run_replay']

_ZERO = Decimal(0)
_STRATEGY_FILENAME = 'replay_strategy.py'
_SETTLE_TIMEOUT_SECONDS = 30
_MAX_SETTLE_ROUNDS = 8
_REPLAY_CREDENTIAL = 'replay'


@dataclass(frozen=True)
class ReplayResult:
    '''Spine-derived summary of a replay run.

    Args:
        bars: Number of bars replayed.
        fills: Number of FillReceived events.
        buy_qty: Total base quantity bought.
        sell_qty: Total base quantity sold.
        fees: Total fees paid, in the quote asset.
        realized_pnl: Net realized PnL from the run's Nexus risk state
            (realized on closes, net of fees; zero while a position stays
            open — not a naive sell-minus-buy of the fills).
        outcome_status_counts: Count of TradeOutcomeProduced by status.
        trades: Closed round-trips in entry order.
        metrics: Summary statistics over the trades and equity curve.
    '''

    bars: int
    fills: int
    buy_qty: Decimal
    sell_qty: Decimal
    fees: Decimal
    realized_pnl: Decimal
    outcome_status_counts: dict[str, int]
    trades: tuple[Trade, ...]
    metrics: ReplayMetrics


def run_replay(
    scenario: ReplayScenario,
    *,
    work_dir: Path,
    epoch_id: int = 1,
) -> ReplayResult:
    '''Replay a scenario through an isolated pipeline and return results.

    Args:
        scenario: The series, bars, strategy, and capital to replay.
        work_dir: Directory for the run's spine, frames, and state; the
            caller owns its lifecycle.
        epoch_id: Epoch identifier for the isolated spine.

    Returns:
        A ReplayResult summarising fills and realized PnL.
    '''

    conduit_dir = work_dir / 'conduit'
    arrow_dir = work_dir / 'arrow'
    state_dir = work_dir / 'state'

    for directory in (work_dir, conduit_dir, arrow_dir, state_dir):
        directory.mkdir(parents=True, exist_ok=True)

    (work_dir / _STRATEGY_FILENAME).write_text(scenario.strategy_source)
    manifest_path = work_dir / 'manifest.yaml'
    manifest_path.write_text(_manifest_yaml(scenario))

    clock = ReplayClock(scenario.bars[0].settle)
    adapter = ReplayVenueAdapter(
        clock=clock.now,
        filters={scenario.symbol: scenario.filters},
        starting_balances={'USDT': scenario.capital_pool},
    )

    config = TradingConfig(
        epoch_id=epoch_id,
        account_credentials={
            scenario.account_id: (_REPLAY_CREDENTIAL, _REPLAY_CREDENTIAL),
        },
    )
    inst = InstanceConfig(
        account_id=scenario.account_id,
        manifest_path=manifest_path,
        strategies_base_path=work_dir,
        state_dir=state_dir,
    )
    launcher = Launcher(
        trading_config=config,
        instances=[inst],
        db_path=work_dir / 'event_spine.sqlite',
        venue_adapter=cast(VenueAdapter, adapter),
        clock=clock.now,
        conduit_dir=conduit_dir,
        arrow_dir=arrow_dir,
    )

    try:
        launcher._start_event_loop()
        launcher._start_trading()

        runtime = launcher._build_nexus_runtime(
            inst, launcher._outcome_queues[scenario.account_id],
        )
        trading = launcher._trading
        loop = launcher._loop
        spine = launcher._event_spine

        if trading is None or loop is None or spine is None:
            msg = 'launcher did not initialize trading/loop/spine'
            raise RuntimeError(msg)

        _activate_mode(runtime, clock)

        _drive(
            scenario, runtime, adapter, clock,
            conduit_dir, arrow_dir, trading, loop,
        )

        events = asyncio.run_coroutine_threadsafe(
            spine.read(epoch_id), loop,
        ).result(timeout=_SETTLE_TIMEOUT_SECONDS)

        return _build_result(scenario, events, runtime.state)

    finally:
        launcher._stop_event.set()
        launcher._shutdown()
        _drop_from_sys_path(work_dir)


def _drop_from_sys_path(work_dir: Path) -> None:
    '''Remove the run's strategy dir from sys.path after the run.

    The launcher inserts the resolved strategies base path (the run's
    work dir) onto sys.path to import the replay strategy module; drop
    both the given and resolved forms so a finished run — even one with a
    relative work_dir — does not leave its dir resolving later imports.
    '''

    for entry in {str(work_dir), str(work_dir.resolve())}:

        while entry in sys.path:
            sys.path.remove(entry)


def _activate_mode(runtime: _NexusRuntime, clock: ReplayClock) -> None:
    '''Force ACTIVE mode; replay has no HealthLoop to lift REDUCE_ONLY.

    The StartupSequencer boots the instance into REDUCE_ONLY until the
    HealthLoop confirms venue health, which would block every ENTER. A
    replay has no live venue and starts no HealthLoop, so it sets the
    mode directly under the positions lock — the same write the
    HealthLoop makes on transition.
    '''

    with runtime.positions_lock:
        runtime.state.mode = ModeState(
            mode=OperationalMode.ACTIVE,
            trigger='replay',
            transitioned_at=clock.now(),
        )


def _drive(
    scenario: ReplayScenario,
    runtime: _NexusRuntime,
    adapter: ReplayVenueAdapter,
    clock: ReplayClock,
    conduit_dir: Path,
    arrow_dir: Path,
    trading: Trading,
    loop: asyncio.AbstractEventLoop,
) -> None:
    '''Walk the scenario's bars, dispatching each through PredictLoop.'''

    ohlcv_rows: list[tuple[int, float]] = []
    prediction_rows: list[tuple[int, int, float]] = []
    dollar_open_ts: list[int] = []
    bindings = runtime.sequencer.signal_bindings

    for bar in scenario.bars:
        ohlcv_rows.append((bar.ts_ns, bar.close))
        prediction_rows.append((bar.ts_ns, bar.prediction, bar.probability))

        if bar.start_ts_ns is not None:
            dollar_open_ts.append(bar.start_ts_ns)

        materialize_bar_frames(
            conduit_dir=conduit_dir,
            arrow_dir=arrow_dir,
            series=scenario.series,
            generated_at=bar.settle,
            ohlcv_rows=ohlcv_rows,
            prediction_rows=prediction_rows,
            start_ts=dollar_open_ts or None,
        )
        adapter.set_price(Decimal(str(bar.close)))
        clock.advance_to(bar.settle)

        for binding in bindings:
            runtime.predict_loop.tick_once(binding)

        _settle(trading, runtime, scenario.account_id, loop)


def _settle(
    trading: Trading,
    runtime: _NexusRuntime,
    account_id: str,
    loop: asyncio.AbstractEventLoop,
) -> None:
    '''Quiesce commands then drain outcomes until the bar stabilizes.'''

    for _ in range(_MAX_SETTLE_ROUNDS):
        asyncio.run_coroutine_threadsafe(
            trading.quiesce(account_id), loop,
        ).result(timeout=_SETTLE_TIMEOUT_SECONDS)

        drained = 0
        while runtime.outcome_loop.tick_once():
            drained += 1

        if drained == 0:
            return

    msg = 'replay settle did not converge'
    raise RuntimeError(msg)


def _build_result(
    scenario: ReplayScenario,
    events: Sequence[tuple[int, object]],
    state: InstanceState,
) -> ReplayResult:
    '''Summarise a run's fills from the spine and realized PnL from state.'''

    fills = [event for _, event in events if isinstance(event, FillReceived)]

    buy_qty = sum((f.qty for f in fills if f.side is OrderSide.BUY), _ZERO)
    sell_qty = sum((f.qty for f in fills if f.side is OrderSide.SELL), _ZERO)
    fees = sum((f.fee for f in fills), _ZERO)

    status_counts: dict[str, int] = {}

    for _, event in events:

        if isinstance(event, TradeOutcomeProduced):
            status_counts[event.status.value] = (
                status_counts.get(event.status.value, 0) + 1
            )

    trades, metrics = build_replay_report(scenario, fills)

    return ReplayResult(
        bars=len(scenario.bars),
        fills=len(fills),
        buy_qty=buy_qty,
        sell_qty=sell_qty,
        fees=fees,
        realized_pnl=state.risk.realized_pnl,
        outcome_status_counts=status_counts,
        trades=trades,
        metrics=metrics,
    )


def _manifest_yaml(scenario: ReplayScenario) -> str:
    '''Render the per-account manifest the StartupSequencer loads.'''

    capital = int(scenario.capital_pool)

    return (
        f'account_id: {scenario.account_id}\n'
        f'allocated_capital: {capital}\n'
        f'capital_pool: {capital}\n'
        f'strategies:\n'
        f'  - id: replay_strat\n'
        f'    file: {_STRATEGY_FILENAME}\n'
        f'    signal:\n'
        f'      series: {scenario.series}\n'
        f'      interval_seconds: {scenario.interval_seconds}\n'
        f'    capital_pct: 100\n'
    )

