'''Test for PT-FIX-2: launcher passes `config` into ShutdownSequencer.

Pre-fix: `Launcher._run_nexus_instance` constructed `ShutdownSequencer`
without `config=`. `nexus.startup.shutdown_sequencer.ShutdownSequencer.
_submit_actions` checks `if self._config is None` and early-returns
with a warning log, dropping every EXIT/ABORT action returned from
`Strategy.on_shutdown`. Open positions were never closed during
graceful shutdown.

Post-fix: `_run_nexus_instance` passes `config=runtime.nexus_config`,
so the Nexus shutdown sequencer can translate EXIT/ABORT actions into
TradeCommands and submit them via PraxisOutbound.
'''

from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

from nexus.instance_config import InstanceConfig as NexusInstanceConfig

from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.launcher import InstanceConfig, Launcher, _NexusRuntime
from praxis.trading import Trading
from praxis.trading_config import TradingConfig


def _instance_config(tmp_path: Path) -> InstanceConfig:
    state_dir = tmp_path / 'state'
    state_dir.mkdir()
    manifest_path = tmp_path / 'manifest.yaml'
    manifest_path.write_text('placeholder: true\n')

    return InstanceConfig(
        account_id='acct-pt-fix-2',
        manifest_path=manifest_path,
        strategies_base_path=tmp_path,
        state_dir=state_dir,
    )


def _stub_nexus_runtime() -> _NexusRuntime:
    nexus_config = MagicMock(spec=NexusInstanceConfig)
    nexus_config.account_id = 'acct-pt-fix-2'

    return _NexusRuntime(
        state_store=MagicMock(),
        sequencer=MagicMock(),
        runner=MagicMock(),
        manifest=MagicMock(),
        state=MagicMock(),
        nexus_config=nexus_config,
        capital_controller=MagicMock(),
        pipeline=MagicMock(),
        praxis_outbound=MagicMock(),
        praxis_inbound=MagicMock(),
        predict_loop=MagicMock(),
        timer_loop=None,
        outcome_loop=MagicMock(),
        health_loop=MagicMock(),
        outcome_processor=MagicMock(),
        process_outcome=MagicMock(),
    )


def test_run_nexus_instance_passes_config_into_shutdown_sequencer(
    tmp_path: Path,
) -> None:
    '''ShutdownSequencer is constructed with `config=runtime.nexus_config`.

    Without this, `_submit_actions` in the Nexus shutdown sequencer
    silently drops every EXIT/ABORT action returned by
    `Strategy.on_shutdown` (early-return on `self._config is None`).
    '''

    inst = _instance_config(tmp_path)

    runtime = _stub_nexus_runtime()

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()

    try:
        launcher = Launcher(
            trading_config=TradingConfig(epoch_id=1),
            instances=[inst],
            db_path=tmp_path / 'spine.sqlite',
        )
        launcher._loop = loop
        launcher._trading = MagicMock(spec=Trading)
        launcher._stop_event.set()

        outcome_queue: queue.Queue[TradeOutcome] = queue.Queue()

        captured: dict[str, object] = {}

        def fake_shutdown_ctor(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            instance = MagicMock()
            instance.shutdown.return_value = None
            return instance

        with patch.object(
            launcher,
            '_build_nexus_runtime',
            return_value=runtime,
        ), patch(
            'praxis.launcher.ShutdownSequencer',
            side_effect=fake_shutdown_ctor,
        ):
            launcher._run_nexus_instance(inst, outcome_queue)

        assert 'config' in captured
        assert captured['config'] is runtime.nexus_config
        runtime.health_loop.stop.assert_called_once()
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=5)

        if not loop.is_closed():
            loop.close()
