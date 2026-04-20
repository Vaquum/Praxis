'''Tests for Launcher `/healthz` HTTP endpoint (Render.4).'''

from __future__ import annotations

import asyncio
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import aiosqlite
import pytest

from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.launcher import InstanceConfig, Launcher
from praxis.trading_config import TradingConfig

from tests.test_launcher import MockVenueAdapter, _make_manifest_yaml


@pytest.fixture(autouse=True)
def _mock_trainer() -> None:
    '''Patch Limen Trainer so launcher startup skips real training.'''

    mock_sensor = MagicMock()
    mock_sensor.permutation_id = 1
    mock_sensor.round_params = {}

    mock_trainer = MagicMock()
    mock_trainer.return_value.train.return_value = [mock_sensor]
    mock_trainer.return_value._manifest = MagicMock()

    with patch('nexus.startup.sequencer.Trainer', mock_trainer):
        yield


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return cast(int, s.getsockname()[1])


def _get_healthz(port: int) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class TestHealthzEndpoint:

    def test_healthz_returns_200_when_healthy(self, tmp_path: Path) -> None:
        '''GET /healthz returns 200 while Trading is up.'''

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

        spine = asyncio.run_coroutine_threadsafe(make_spine(), loop).result(timeout=5)

        port = _free_port()
        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            event_spine=spine,
            venue_adapter=cast(VenueAdapter, MockVenueAdapter()),
            healthz_port=port,
        )

        launch_thread = threading.Thread(target=launcher.launch, daemon=True)
        launch_thread.start()

        try:
            deadline = 5.0
            step = 0.1
            while deadline > 0:
                if launcher._healthz_runner is not None:
                    break
                threading.Event().wait(step)
                deadline -= step

            status, body = _get_healthz(port)
            assert status == 200
            assert '"status": "ok"' in body
        finally:
            launcher._stop_event.set()
            launch_thread.join(timeout=15)
            loop.call_soon_threadsafe(loop.stop)
            loop_thread.join(timeout=5)

    def test_healthz_returns_503_during_shutdown(self, tmp_path: Path) -> None:
        '''GET /healthz returns 503 once the stop event is set.'''

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

        spine = asyncio.run_coroutine_threadsafe(make_spine(), loop).result(timeout=5)

        port = _free_port()
        launcher = Launcher(
            trading_config=config,
            instances=[inst],
            event_spine=spine,
            venue_adapter=cast(VenueAdapter, MockVenueAdapter()),
            healthz_port=port,
        )

        app_ready = threading.Event()

        async def _wait_for_healthz() -> None:
            while launcher._healthz_runner is None:
                await asyncio.sleep(0.05)
            app_ready.set()

        def _run() -> None:
            asyncio.run_coroutine_threadsafe(_wait_for_healthz(), loop)
            launcher.launch()

        launch_thread = threading.Thread(target=_run, daemon=True)
        launch_thread.start()

        if not app_ready.wait(timeout=10):
            pytest.fail('healthz server did not start within timeout')

        try:
            status_ok, _ = _get_healthz(port)
            assert status_ok == 200

            launcher._stop_event.set()

            launch_thread.join(timeout=15)

            try:
                _get_healthz(port)
            except urllib.error.URLError:
                pass
            else:
                pytest.fail('healthz still reachable after shutdown')
        finally:
            loop.call_soon_threadsafe(loop.stop)
            loop_thread.join(timeout=5)
