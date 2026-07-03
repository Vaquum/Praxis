'''Tests for the Launcher `/metrics` paper-trading endpoint.'''

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import aiosqlite
import pytest
from aiohttp.test_utils import make_mocked_request
from aiohttp.web import Request

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived, MarkSampled
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.launcher import InstanceConfig, Launcher
from praxis.trading_config import TradingConfig

from tests.test_launcher import MockVenueAdapter, _make_manifest_yaml

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_INTERVAL = 900
_ACCOUNT = 'test-acc'


async def _spine_with_run() -> EventSpine:
    conn = await aiosqlite.connect(':memory:')
    spine = EventSpine(conn)
    await spine.ensure_schema()

    for index in range(5):
        await spine.append(
            MarkSampled(
                account_id=_ACCOUNT, timestamp=_BASE + timedelta(seconds=index * _INTERVAL),
                symbol='BTCUSDT', mark_price=Decimal(100 + index),
            ),
            1,
        )

    for index, side, price in ((0, OrderSide.BUY, '100'), (2, OrderSide.SELL, '110')):
        await spine.append(
            FillReceived(
                account_id=_ACCOUNT, timestamp=_BASE + timedelta(seconds=index * _INTERVAL + 1),
                client_order_id=f'c{index}', venue_order_id=f'v{index}', venue_trade_id=f'vt{index}',
                trade_id='a', command_id='cmd', symbol='BTCUSDT', side=side,
                qty=Decimal('1'), price=Decimal(price), fee=Decimal('0'),
                fee_asset='USDT', is_maker=False,
            ),
            1,
        )

    return spine


def _request(path: str, remote: str = '127.0.0.1') -> Request:
    transport = Mock()
    transport.get_extra_info = lambda key, default=None: (remote, 0) if key == 'peername' else default

    return make_mocked_request('GET', path, transport=transport)


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


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_paper_report(tmp_path: Path) -> None:
    spine = await _spine_with_run()
    launcher = _launcher(spine, tmp_path)

    response = await launcher._metrics_handler(_request('/metrics'))
    body = json.loads(response.body)

    assert response.status == 200
    assert body['account_id'] == _ACCOUNT
    assert body['metrics']['trade_count'] == 1
    assert body['metrics']['snapshot'] == {}
    assert body['metrics']['snapshot_portfolio']['trade_pnl_net_bps_p50'] is not None
    assert len(body['trades']) == 1

    await spine._conn.close()


@pytest.mark.asyncio
async def test_metrics_endpoint_unknown_account_404(tmp_path: Path) -> None:
    spine = await _spine_with_run()
    launcher = _launcher(spine, tmp_path)

    response = await launcher._metrics_handler(_request('/metrics?account_id=nope'))

    assert response.status == 404

    await spine._conn.close()


@pytest.mark.asyncio
async def test_metrics_endpoint_rejects_non_loopback(tmp_path: Path) -> None:
    spine = await _spine_with_run()
    launcher = _launcher(spine, tmp_path)

    response = await launcher._metrics_handler(_request('/metrics', remote='10.0.0.5'))

    assert response.status == 403

    await spine._conn.close()


@pytest.mark.asyncio
async def test_metrics_endpoint_503_without_spine(tmp_path: Path) -> None:
    spine = await _spine_with_run()
    launcher = _launcher(spine, tmp_path)
    launcher._event_spine = None

    response = await launcher._metrics_handler(_request('/metrics'))

    assert response.status == 503

    await spine._conn.close()
