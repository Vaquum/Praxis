'''
Verify Binance Spot testnet WebSocket-API user-data-stream connectivity.

Subscribes to the user data stream via the WS-API
`userDataStream.subscribe.signature` request and consumes pushed events on
the same connection.
'''

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import uuid

import pytest
import websockets

from tests.testnet.conftest import (
    HTTP_OK,
    MIN_ORDER_QUOTE_QTY,
    REST_BASE,
    SESSION_TIMEOUT,
    SYMBOL,
    WS_API_BASE,
    WS_CLOSE_TIMEOUT,
    WS_RECV_TIMEOUT,
    auth_headers,
    pytestmark,
    signed_params,
    skip_no_creds,
)

import aiohttp

__all__ = ['pytestmark']


_RECV_WINDOW_MS = 5000
_OK_STATUS = 200


def _subscribe_frame(api_key: str, api_secret: str) -> str:

    '''
    Build a signed `userDataStream.subscribe.signature` request frame.

    Args:
        api_key (str): Binance API key
        api_secret (str): Binance API secret

    Returns:
        str: JSON-encoded WS-API request frame
    '''

    params: dict[str, str | int] = {
        'apiKey': api_key,
        'recvWindow': _RECV_WINDOW_MS,
        'timestamp': int(time.time() * 1000),
    }
    qs = '&'.join(f'{k}={params[k]}' for k in sorted(params))
    params['signature'] = hmac.new(
        api_secret.encode(), qs.encode(), hashlib.sha256,
    ).hexdigest()
    return json.dumps({
        'id': str(uuid.uuid4()),
        'method': 'userDataStream.subscribe.signature',
        'params': params,
    })


def _ws_credentials() -> tuple[str, str]:

    '''
    Fetch (api_key, api_secret) from the test environment.

    Returns:
        tuple[str, str]: API key and secret
    '''

    import os
    return (
        os.environ['BINANCE_TESTNET_API_KEY'],
        os.environ['BINANCE_TESTNET_API_SECRET'],
    )


@skip_no_creds
@pytest.mark.asyncio
async def test_ws_api_subscribe_returns_subscription_id() -> None:
    api_key, api_secret = _ws_credentials()
    async with websockets.connect(
        WS_API_BASE, close_timeout=WS_CLOSE_TIMEOUT,
    ) as ws:
        await ws.send(_subscribe_frame(api_key, api_secret))
        ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=WS_RECV_TIMEOUT))

    assert ack['status'] == _OK_STATUS, f'subscribe rejected: {ack}'
    assert isinstance(ack['result']['subscriptionId'], int)


@skip_no_creds
@pytest.mark.asyncio
async def test_ws_api_unsubscribe_after_subscribe() -> None:
    api_key, api_secret = _ws_credentials()
    async with websockets.connect(
        WS_API_BASE, close_timeout=WS_CLOSE_TIMEOUT,
    ) as ws:
        await ws.send(_subscribe_frame(api_key, api_secret))
        sub_ack = json.loads(
            await asyncio.wait_for(ws.recv(), timeout=WS_RECV_TIMEOUT),
        )
        assert sub_ack['status'] == _OK_STATUS, f'subscribe rejected: {sub_ack}'
        sub_id = sub_ack['result']['subscriptionId']

        await ws.send(json.dumps({
            'id': str(uuid.uuid4()),
            'method': 'userDataStream.unsubscribe',
            'params': {'subscriptionId': sub_id},
        }))
        ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=WS_RECV_TIMEOUT))

    assert ack['status'] == _OK_STATUS, f'unsubscribe rejected: {ack}'


@skip_no_creds
@pytest.mark.asyncio
async def test_e2e_fill() -> None:
    api_key, api_secret = _ws_credentials()
    async with websockets.connect(
        WS_API_BASE, close_timeout=WS_CLOSE_TIMEOUT,
    ) as ws:
        await ws.send(_subscribe_frame(api_key, api_secret))
        ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=WS_RECV_TIMEOUT))
        assert ack['status'] == _OK_STATUS, f'subscribe rejected: {ack}'

        async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s:
            params = signed_params(
                symbol=SYMBOL,
                side='BUY',
                type='MARKET',
                quoteOrderQty=MIN_ORDER_QUOTE_QTY,
            )
            async with s.post(
                f'{REST_BASE}/api/v3/order',
                params=params,
                headers=auth_headers(),
            ) as r:
                assert r.status == HTTP_OK, f'Order rejected: {await r.text()}'
                order_data = await r.json()
        order_id = order_data['orderId']

        deadline = time.time() + WS_RECV_TIMEOUT
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except TimeoutError:
                break
            frame = json.loads(msg)
            event = frame.get('event') if isinstance(frame, dict) else None
            if not isinstance(event, dict):
                continue
            if (
                event.get('e') == 'executionReport'
                and event.get('i') == order_id
                and event.get('X') == 'FILLED'
            ):
                return

        pytest.fail(
            f'No executionReport for order {order_id} within {WS_RECV_TIMEOUT}s',
        )
