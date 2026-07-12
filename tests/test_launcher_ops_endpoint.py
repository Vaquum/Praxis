'''Tests for the Launcher `/ops` operator control endpoints.'''

from __future__ import annotations

import asyncio
import json
import threading
from decimal import Decimal
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, Mock

import aiosqlite
import pytest
from aiohttp.test_utils import make_mocked_request
from aiohttp.web import Request

from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OperationalMode
from nexus.core.domain.instance_state import InstanceState
from nexus.core.mode_controller import ModeController
from praxis.core.domain.enums import OrderSide, OrderType
from praxis.core.domain.position import Position
from praxis.core.domain.events import OperatorHaltRequested, OperatorResumeRequested
from praxis.infrastructure.alert_sink import AlertSink
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.launcher import InstanceConfig, Launcher
from praxis.trading_config import TradingConfig

from tests.test_launcher import MockVenueAdapter, _make_manifest_yaml

_ACCOUNT = 'test-acc'
_TOKEN = 'secret-token'  # noqa: S105 - test bearer token, not a real secret


async def _spine() -> EventSpine:
    conn = await aiosqlite.connect(':memory:')
    spine = EventSpine(conn)
    await spine.ensure_schema()

    return spine


def _request(
    path: str,
    method: str = 'POST',
    remote: str = '127.0.0.1',
    token: str | None = _TOKEN,
) -> Request:
    transport = Mock()
    transport.get_extra_info = lambda key, default=None: (remote, 0) if key == 'peername' else default
    headers = {'Authorization': f'Bearer {token}'} if token is not None else {}

    return make_mocked_request(method, path, headers=headers, transport=transport)


def _launcher(spine: EventSpine, tmp_path: Path) -> Launcher:
    exp_dir = tmp_path / 'experiment'
    exp_dir.mkdir()
    manifest_path = _make_manifest_yaml(tmp_path, exp_dir)
    config = TradingConfig(epoch_id=1, account_credentials={_ACCOUNT: ('key', 'secret')})
    inst = InstanceConfig(
        account_id=_ACCOUNT, manifest_path=manifest_path,
        strategies_base_path=tmp_path, state_dir=tmp_path / 'state',
    )

    return Launcher(
        trading_config=config, instances=[inst], event_spine=spine,
        venue_adapter=cast(VenueAdapter, MockVenueAdapter()),
    )


def _register_runtime(launcher: Launcher) -> Mock:
    state = InstanceState(capital=CapitalState(capital_pool=Decimal('10000')))
    runtime = Mock()
    runtime.mode_controller = ModeController(state, threading.Lock())
    runtime.state = state
    runtime.state_store = Mock()
    runtime.nexus_config.account_id = _ACCOUNT
    launcher._nexus_runtimes[_ACCOUNT] = runtime

    return runtime


@pytest.mark.asyncio
async def test_halt_sets_manual_hold_and_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    spine = await _spine()
    launcher = _launcher(spine, tmp_path)
    runtime = _register_runtime(launcher)

    response = await launcher._ops_halt_handler(_request('/ops/halt'))
    body = json.loads(response.body)

    assert response.status == 200
    assert body['mode'] == OperationalMode.HALTED.value
    assert body['holds']['manual'] is True
    assert runtime.state.mode.mode is OperationalMode.HALTED
    runtime.state_store.append_mutation.assert_called_once_with(runtime.state)

    records = await spine.read(1)
    assert any(isinstance(event, OperatorHaltRequested) for _seq, event in records)


@pytest.mark.asyncio
async def test_resume_clears_manual_hold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    spine = await _spine()
    launcher = _launcher(spine, tmp_path)
    runtime = _register_runtime(launcher)
    runtime.mode_controller.set_manual_halt('manual stop')

    response = await launcher._ops_resume_handler(_request('/ops/resume'))
    body = json.loads(response.body)

    assert response.status == 200
    assert body['mode'] == OperationalMode.ACTIVE.value
    assert body['holds']['manual'] is False

    records = await spine.read(1)
    assert any(isinstance(event, OperatorResumeRequested) for _seq, event in records)


@pytest.mark.asyncio
async def test_status_reports_mode_and_holds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    runtime = _register_runtime(launcher)
    runtime.mode_controller.set_manual_halt('manual stop')

    response = await launcher._ops_status_handler(_request('/ops/status', method='GET'))
    body = json.loads(response.body)

    assert response.status == 200
    assert body['account_id'] == _ACCOUNT
    assert body['mode'] == OperationalMode.HALTED.value
    assert body['holds']['manual'] is True


@pytest.mark.asyncio
async def test_non_loopback_is_forbidden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)

    response = await launcher._ops_halt_handler(_request('/ops/halt', remote='10.0.0.5'))

    assert response.status == 403


@pytest.mark.asyncio
async def test_missing_token_config_disables_ops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('PRAXIS_OPS_TOKEN', raising=False)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)

    response = await launcher._ops_halt_handler(_request('/ops/halt'))

    assert response.status == 503


@pytest.mark.asyncio
async def test_wrong_token_is_unauthorized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)

    response = await launcher._ops_halt_handler(
        _request('/ops/halt', token='wrong'),  # noqa: S106 - test bearer token
    )

    assert response.status == 401


@pytest.mark.asyncio
async def test_unknown_account_is_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)

    response = await launcher._ops_status_handler(_request('/ops/status', method='GET'))

    assert response.status == 404


@pytest.mark.asyncio
async def test_cancel_all_aborts_working_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)
    launcher._trading = Mock()
    launcher._trading.execution_manager.get_open_orders.return_value = {
        'c1': Mock(command_id='cmd-1'),
        'c2': Mock(command_id='cmd-1'),
        'c3': Mock(command_id='cmd-2'),
    }

    response = await launcher._ops_cancel_all_handler(_request('/ops/cancel-all'))
    body = json.loads(response.body)

    assert response.status == 200
    assert body['canceled'] == ['cmd-1', 'cmd-2']
    assert launcher._trading.submit_abort.call_count == 2


@pytest.mark.asyncio
async def test_close_all_submits_market_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)
    trading = Mock()
    trading.execution_manager.get_open_orders.return_value = {}
    trading.pull_positions.return_value = {
        ('t1', _ACCOUNT): Position(
            account_id=_ACCOUNT, trade_id='t1', symbol='BTCUSDT',
            side=OrderSide.BUY, qty=Decimal('2'), avg_entry_price=Decimal('100'),
        ),
    }
    trading.submit_command = AsyncMock(return_value='exit-cmd')
    launcher._trading = trading

    response = await launcher._ops_close_all_handler(_request('/ops/close-all'))
    body = json.loads(response.body)

    assert response.status == 200
    assert body['closed'] == [{'trade_id': 't1', 'command_id': 'exit-cmd', 'qty': '2'}]

    kwargs = trading.submit_command.call_args.kwargs
    assert kwargs['side'] is OrderSide.SELL
    assert kwargs['order_type'] is OrderType.MARKET
    assert kwargs['qty'] == Decimal('2')


@pytest.mark.asyncio
async def test_halt_emits_operator_alert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)
    posted: list[dict[str, object]] = []

    async def post(_url: str, payload: dict[str, object]) -> None:
        posted.append(payload)

    launcher._alert_sink = AlertSink(webhook_url='http://hook', post=post)

    await launcher._ops_halt_handler(_request('/ops/halt'))

    assert any(p['event'] == 'operator_halt' for p in posted)


@pytest.mark.asyncio
async def test_cancel_all_returns_structured_error_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)
    launcher._trading = Mock()
    launcher._trading.execution_manager.get_open_orders.side_effect = RuntimeError('not registered')

    response = await launcher._ops_cancel_all_handler(_request('/ops/cancel-all'))

    assert response.status == 500
    assert json.loads(response.body) == {'error': 'cancel_all_failed'}


@pytest.mark.asyncio
async def test_close_all_returns_structured_error_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)
    launcher._trading = Mock()
    launcher._trading.execution_manager.get_open_orders.side_effect = RuntimeError('not registered')

    response = await launcher._ops_close_all_handler(_request('/ops/close-all'))

    assert response.status == 500
    assert json.loads(response.body) == {'error': 'close_all_failed'}


@pytest.mark.asyncio
async def test_ambiguous_account_returns_400(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('PRAXIS_OPS_TOKEN', _TOKEN)
    launcher = _launcher(await _spine(), tmp_path)
    _register_runtime(launcher)
    second = Mock()
    second.nexus_config.account_id = 'other-acc'
    launcher._nexus_runtimes['other-acc'] = second

    response = await launcher._ops_status_handler(_request('/ops/status', method='GET'))

    assert response.status == 400
    assert json.loads(response.body)['error'] == 'account_id_required'


@pytest.mark.asyncio
async def test_mode_halt_alert_delivers_webhook_when_loop_available(tmp_path: Path) -> None:
    launcher = _launcher(await _spine(), tmp_path)
    posted: list[dict[str, object]] = []

    async def post(_url: str, payload: dict[str, object]) -> None:
        posted.append(payload)

    launcher._alert_sink = AlertSink(webhook_url='http://hook', post=post)
    launcher._loop = asyncio.get_running_loop()
    on_halt = launcher._build_mode_halt_alert('acc-1')

    on_halt('risk')
    await asyncio.sleep(0.05)

    assert any(p['event'] == 'mode_halted' and p['source'] == 'risk' for p in posted)


@pytest.mark.asyncio
async def test_mode_halt_alert_logs_only_without_loop(tmp_path: Path) -> None:
    launcher = _launcher(await _spine(), tmp_path)
    launcher._alert_sink = Mock()
    launcher._loop = None
    on_halt = launcher._build_mode_halt_alert('acc-1')

    on_halt('manual')

    launcher._alert_sink.alert.assert_called_once()
    launcher._alert_sink.notify.assert_not_called()
