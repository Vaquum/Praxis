'''Tests for the binsim WebSocket endpoints (/ws-api/v3 and /stream).'''

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import Ledger
from praxis.binsim.server import make_app


_URL = 'https://binance-spot-depth20-1000ms.onrender.com/top20'
_TOKEN = 'test-token'  # noqa: S105 — test fixture, not a real credential
_THRESHOLD_MS = 5000

_SIGNING_KEY = secrets.token_hex(16)
_ACCOUNT_ID = 'acc-1'

_SUBSCRIBE_METHOD = 'userDataStream.subscribe.signature'


def _seeded_book() -> OrderBook:

    book = OrderBook()
    book.replace(
        bids=[(Decimal('100.00'), Decimal('1.0'))],
        asks=[(Decimal('101.00'), Decimal('1.0'))],
        last_update_id=1, ts_ms=int(time.time() * 1000),
    )

    return book


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncGenerator[tuple[TestClient, str], None]:

    book = _seeded_book()
    ledger = Ledger(tmp_path)
    api_key = await ledger.register_account(_ACCOUNT_ID, Decimal('10000'))

    poller = DepthPoller(book, _URL, _TOKEN)
    poller._last_success_ts_ms = int(time.time() * 1000)

    app = make_app(book, ledger, poller, _THRESHOLD_MS)
    c = TestClient(TestServer(app))
    await c.start_server()

    yield c, api_key

    await c.close()


def _build_subscribe_request(api_key: str, signing_key: str) -> dict[str, Any]:

    timestamp = int(time.time() * 1000)
    params: dict[str, Any] = {
        'apiKey': api_key,
        'recvWindow': 5000,
        'timestamp': timestamp,
    }
    qs = '&'.join(f'{k}={params[k]}' for k in sorted(params))
    signature = hmac.new(signing_key.encode(), qs.encode(), hashlib.sha256).hexdigest()  # lgtm[py/weak-sensitive-data-hashing]
    params['signature'] = signature

    return {
        'id': str(uuid.uuid4()),
        'method': _SUBSCRIBE_METHOD,
        'params': params,
    }


@pytest.mark.asyncio
async def test_ws_api_accepts_subscribe_and_returns_subscription_id(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = _build_subscribe_request(client[1], _SIGNING_KEY)
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)

        assert msg.type.name == 'TEXT'

        ack = json.loads(msg.data)
        assert ack['id'] == request['id']
        assert ack['status'] == 200
        assert isinstance(ack['result']['subscriptionId'], int)
        assert ack['result']['subscriptionId'] >= 1


@pytest.mark.asyncio
async def test_ws_api_hands_out_monotonic_subscription_ids(client: tuple[TestClient, str]) -> None:

    ids: list[int] = []

    for _ in range(3):
        async with client[0].ws_connect('/ws-api/v3') as ws:
            request = _build_subscribe_request(client[1], _SIGNING_KEY)
            await ws.send_str(json.dumps(request))
            msg = await ws.receive(timeout=5.0)
            ack = json.loads(msg.data)
            ids.append(ack['result']['subscriptionId'])

    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


@pytest.mark.asyncio
async def test_ws_api_rejects_missing_api_key(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = {
            'id': 'req-1',
            'method': _SUBSCRIBE_METHOD,
            'params': {'signature': 'deadbeef', 'recvWindow': 5000, 'timestamp': 0},
        }
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 401
        assert ack['error']['code'] == -1022


@pytest.mark.asyncio
async def test_ws_api_rejects_missing_signature(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = {
            'id': 'req-1',
            'method': _SUBSCRIBE_METHOD,
            'params': {'apiKey': client[1], 'recvWindow': 5000, 'timestamp': 0},
        }
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 401
        assert ack['error']['code'] == -1022


@pytest.mark.asyncio
async def test_ws_api_rejects_unknown_api_key(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = _build_subscribe_request('apikey-not-registered', _SIGNING_KEY)
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 401
        assert ack['error']['code'] == -2014


@pytest.mark.asyncio
async def test_ws_api_rejects_unknown_method(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = {
            'id': 'req-1',
            'method': 'someUnknownMethod',
            'params': {'apiKey': client[1], 'signature': 'x'},
        }
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 400
        assert ack['error']['code'] == -1100


@pytest.mark.asyncio
async def test_ws_api_ignores_non_text_and_malformed_frames(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/ws-api/v3') as ws:
        await ws.send_str('not-json')

        request = _build_subscribe_request(client[1], _SIGNING_KEY)
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 200


@pytest.mark.asyncio
async def test_ws_stream_accepts_connection(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/stream') as ws:
        await ws.close()

        assert ws.closed is True


@pytest.mark.asyncio
async def test_ws_stream_does_not_push_frames(client: tuple[TestClient, str]) -> None:

    async with client[0].ws_connect('/stream') as ws:
        with pytest.raises(TimeoutError):
            await ws.receive(timeout=0.5)


@pytest.mark.asyncio
async def test_ws_api_rejects_non_string_api_key(client: tuple[TestClient, str]) -> None:
    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = {
            'id': 'req-1',
            'method': _SUBSCRIBE_METHOD,
            'params': {'apiKey': 12345, 'signature': 'deadbeef', 'recvWindow': 5000, 'timestamp': 0},
        }
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 401
        assert ack['error']['code'] == -1022


@pytest.mark.asyncio
async def test_ws_api_rejects_non_string_signature(client: tuple[TestClient, str]) -> None:
    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = {
            'id': 'req-1',
            'method': _SUBSCRIBE_METHOD,
            'params': {'apiKey': client[1], 'signature': 12345, 'recvWindow': 5000, 'timestamp': 0},
        }
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 401
        assert ack['error']['code'] == -1022


@pytest.mark.asyncio
async def test_ws_api_rejects_whitespace_api_key(client: tuple[TestClient, str]) -> None:
    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = {
            'id': 'req-1',
            'method': _SUBSCRIBE_METHOD,
            'params': {'apiKey': '   ', 'signature': 'deadbeef', 'recvWindow': 5000, 'timestamp': 0},
        }
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 401
        assert ack['error']['code'] == -1022


@pytest.mark.asyncio
async def test_ws_api_rejects_whitespace_signature(client: tuple[TestClient, str]) -> None:
    async with client[0].ws_connect('/ws-api/v3') as ws:
        request = {
            'id': 'req-1',
            'method': _SUBSCRIBE_METHOD,
            'params': {'apiKey': client[1], 'signature': '   ', 'recvWindow': 5000, 'timestamp': 0},
        }
        await ws.send_str(json.dumps(request))

        msg = await ws.receive(timeout=5.0)
        ack = json.loads(msg.data)

        assert ack['status'] == 401
        assert ack['error']['code'] == -1022
