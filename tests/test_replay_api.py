from __future__ import annotations

import asyncio
from pathlib import Path

import polars as pl
import pytest
from aiohttp.test_utils import TestClient, TestServer

from praxis.replay.replay_api import _is_loopback, build_replay_app

_STRATEGY_SOURCE = '''
from __future__ import annotations

from decimal import Decimal

from nexus.strategy import Action, Strategy, StrategyContext, StrategyParams
from nexus.strategy.action import ActionType
from nexus.strategy.signal import Signal
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.order_types import ExecutionMode, OrderType

_DEADLINE = 60
_QUOTE = Decimal("1000")


class Strategy(Strategy):

    def on_save(self):
        return b""

    def on_load(self, data):
        pass

    def on_startup(self, params, context):
        return []

    def on_signal(self, signal, params, context):
        pred = signal.get("_preds")

        if pred == 1 and not context.positions:
            return [
                Action(
                    action_type=ActionType.ENTER,
                    direction=OrderSide.BUY,
                    quote_qty=_QUOTE,
                    execution_mode=ExecutionMode.SINGLE_SHOT,
                    order_type=OrderType.MARKET,
                    deadline=_DEADLINE,
                    reference_price=Decimal(str(signal.get("close"))),
                ),
            ]

        if pred == 0 and context.positions:
            position = context.positions[0]
            remaining = position.size - position.pending_exit
            return [
                Action(
                    action_type=ActionType.EXIT,
                    direction=OrderSide.SELL,
                    size=remaining,
                    execution_mode=ExecutionMode.SINGLE_SHOT,
                    order_type=OrderType.MARKET,
                    deadline=_DEADLINE,
                    trade_id=position.trade_id,
                ),
            ]

        return []

    def on_outcome(self, outcome, params, context):
        return []

    def on_timer(self, timer_id, params, context):
        return []

    def on_shutdown(self, params, context):
        return []
'''

_NS = 1_000_000_000
_INTERVAL = 900
_POLL_ATTEMPTS = 100
_POLL_DELAY = 0.2


def _write_frames(root: Path) -> tuple[Path, Path]:
    arrow_dir = root / 'arrow'
    conduit_dir = root / 'conduit'
    (arrow_dir / 'time_15m').mkdir(parents=True)
    (conduit_dir / 'time_15m').mkdir(parents=True)

    opens = [1000 * _NS, 1900 * _NS]

    pl.DataFrame(
        {'ts': opens, 'close': [60000.0, 61000.0]},
        schema={'ts': pl.Int64, 'close': pl.Float64},
    ).write_ipc(arrow_dir / 'time_15m' / 'latest.arrow')

    pl.DataFrame(
        {
            'ts': opens,
            'prediction': [1, 0],
            'probability': [0.9, 0.1],
            'reason_code': [0, 0],
        },
        schema={
            'ts': pl.Int64,
            'prediction': pl.Int64,
            'probability': pl.Float64,
            'reason_code': pl.Int64,
        },
    ).write_ipc(conduit_dir / 'time_15m' / 'latest.arrow')

    return arrow_dir, conduit_dir


def _payload() -> dict[str, object]:
    return {
        'series': 'time_15m',
        'interval_seconds': _INTERVAL,
        'symbol': 'BTCUSDT',
        'account_id': 'replay-acc',
        'capital_pool': '10000',
        'start': '1970-01-01T00:00:00Z',
        'end': '2100-01-01T00:00:00Z',
        'strategy_source': _STRATEGY_SOURCE,
        'filters': {
            'tick_size': '0.01',
            'lot_step': '0.00001',
            'lot_min': '0.00001',
            'lot_max': '9000',
            'min_notional': '10',
        },
    }


@pytest.mark.asyncio
async def test_post_then_poll_completes(tmp_path: Path) -> None:
    arrow_dir, conduit_dir = _write_frames(tmp_path)
    app = build_replay_app(
        arrow_dir=arrow_dir, conduit_dir=conduit_dir, work_root=tmp_path / 'runs',
    )

    async with TestClient(TestServer(app)) as client:
        post = await client.post('/replay', json=_payload())
        assert post.status == 202
        run_id = (await post.json())['run_id']

        for _ in range(_POLL_ATTEMPTS):
            got = await client.get(f'/replay/{run_id}')
            body = await got.json()
            if body['status'] != 'running':
                break
            await asyncio.sleep(_POLL_DELAY)

        assert body['status'] == 'done', body
        assert body['result']['fills'] == 2
        assert body['result']['bars'] == 2


@pytest.mark.asyncio
async def test_unknown_run_id_returns_404(tmp_path: Path) -> None:
    arrow_dir, conduit_dir = _write_frames(tmp_path)
    app = build_replay_app(
        arrow_dir=arrow_dir, conduit_dir=conduit_dir, work_root=tmp_path / 'runs',
    )

    async with TestClient(TestServer(app)) as client:
        got = await client.get('/replay/nope')
        assert got.status == 404


def test_loopback_predicate() -> None:
    assert _is_loopback('127.0.0.1') is True
    assert _is_loopback('::1') is True
    assert _is_loopback('8.8.8.8') is False
    assert _is_loopback(None) is False


@pytest.mark.asyncio
async def test_malformed_json_rejected(tmp_path: Path) -> None:
    arrow_dir, conduit_dir = _write_frames(tmp_path)
    app = build_replay_app(
        arrow_dir=arrow_dir, conduit_dir=conduit_dir, work_root=tmp_path / 'runs',
    )

    async with TestClient(TestServer(app)) as client:
        post = await client.post(
            '/replay', data='not json',
            headers={'Content-Type': 'application/json'},
        )
        assert post.status == 400


@pytest.mark.asyncio
async def test_bad_decimal_rejected(tmp_path: Path) -> None:
    arrow_dir, conduit_dir = _write_frames(tmp_path)
    app = build_replay_app(
        arrow_dir=arrow_dir, conduit_dir=conduit_dir, work_root=tmp_path / 'runs',
    )

    payload = _payload()
    payload['capital_pool'] = 'not-a-number'

    async with TestClient(TestServer(app)) as client:
        post = await client.post('/replay', json=payload)
        assert post.status == 400


@pytest.mark.asyncio
async def test_empty_range_rejected(tmp_path: Path) -> None:
    arrow_dir, conduit_dir = _write_frames(tmp_path)
    app = build_replay_app(
        arrow_dir=arrow_dir, conduit_dir=conduit_dir, work_root=tmp_path / 'runs',
    )

    payload = _payload()
    payload['start'] = '2099-01-01T00:00:00Z'

    async with TestClient(TestServer(app)) as client:
        post = await client.post('/replay', json=payload)
        assert post.status == 400
