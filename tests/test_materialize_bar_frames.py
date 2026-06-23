from __future__ import annotations

from datetime import datetime, timedelta, UTC
from pathlib import Path

from nexus.startup.sequencer import SignalBinding
from nexus.strategy.action import Action
from nexus.strategy.params import StrategyParams
from nexus.strategy.signal import Signal

from praxis.replay.materialize_bar_frames import materialize_bar_frames
from praxis.replay.replay_clock import ReplayClock

_SERIES = 'time_15m'
_INTERVAL = 900
_NS = 1_000_000_000


class _RecordingRunner:
    def __init__(self) -> None:
        self.signals: list[Signal] = []

    def dispatch_signal(
        self,
        _strategy_id: str,
        signal: Signal,
        _params: StrategyParams,
        _context: object,
    ) -> list[Action]:
        self.signals.append(signal)
        return []


def _open_ns(settle: datetime) -> int:
    return int((settle - timedelta(seconds=_INTERVAL)).timestamp() * _NS)


def test_predict_loop_reads_materialized_frames(tmp_path: Path) -> None:
    from nexus.strategy.predict_loop import PredictLoop

    conduit_dir = tmp_path / 'conduit'
    arrow_dir = tmp_path / 'arrow'
    settle = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)
    ts = _open_ns(settle)

    materialize_bar_frames(
        conduit_dir=conduit_dir,
        arrow_dir=arrow_dir,
        series=_SERIES,
        generated_at=settle,
        ohlcv_rows=[(ts, 64000.0)],
        prediction_rows=[(ts, 1, 0.91)],
    )

    runner = _RecordingRunner()
    clock = ReplayClock(settle)
    loop = PredictLoop(
        runner=runner,
        signal_bindings=[SignalBinding(strategy_id='strat', series=_SERIES, interval_seconds=_INTERVAL)],
        context_provider=lambda _strategy_id: None,
        action_submit=None,
        conduit_dir=conduit_dir,
        arrow_dir=arrow_dir,
        clock=clock.now,
    )

    loop.tick_once(SignalBinding(strategy_id='strat', series=_SERIES, interval_seconds=_INTERVAL))

    assert len(runner.signals) == 1
    signal = runner.signals[0]
    assert signal.values['_preds'] == 1
    assert signal.values['close'] == 64000.0
    assert signal.values['_probs'] == 0.91


def test_dollar_frame_carries_start_ts_for_family_detection(tmp_path: Path) -> None:
    from decimal import Decimal

    import polars as pl

    from praxis.arrow_price_store import ArrowPriceStore

    conduit_dir = tmp_path / 'conduit'
    arrow_dir = tmp_path / 'arrow'
    settle = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)
    settle_ns = int(settle.timestamp() * _NS)
    open_ns = settle_ns - 400 * _NS

    materialize_bar_frames(
        conduit_dir=conduit_dir,
        arrow_dir=arrow_dir,
        series='dollar_60M',
        generated_at=settle,
        ohlcv_rows=[(settle_ns, 64000.0)],
        prediction_rows=[(settle_ns, 1, 0.9)],
        start_ts=[open_ns],
    )

    frame = pl.read_ipc(arrow_dir / 'dollar_60M' / 'latest.arrow')
    assert 'start_ts' in frame.columns

    clock = ReplayClock(settle)
    store = ArrowPriceStore(arrow_dir, clock=clock.now)

    assert store.latest_close('dollar_60M', 300) == Decimal('64000.0')


def test_no_dispatch_when_manifest_stale(tmp_path: Path) -> None:
    from nexus.strategy.predict_loop import PredictLoop

    conduit_dir = tmp_path / 'conduit'
    arrow_dir = tmp_path / 'arrow'
    settle = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)
    ts = _open_ns(settle)

    materialize_bar_frames(
        conduit_dir=conduit_dir,
        arrow_dir=arrow_dir,
        series=_SERIES,
        generated_at=settle,
        ohlcv_rows=[(ts, 64000.0)],
        prediction_rows=[(ts, 1, 0.91)],
    )

    runner = _RecordingRunner()
    far_future = ReplayClock(settle + timedelta(seconds=3600))
    loop = PredictLoop(
        runner=runner,
        signal_bindings=[SignalBinding(strategy_id='strat', series=_SERIES, interval_seconds=_INTERVAL)],
        context_provider=lambda _strategy_id: None,
        action_submit=None,
        conduit_dir=conduit_dir,
        arrow_dir=arrow_dir,
        clock=far_future.now,
    )

    loop.tick_once(SignalBinding(strategy_id='strat', series=_SERIES, interval_seconds=_INTERVAL))

    assert runner.signals == []
