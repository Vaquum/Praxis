"""Verify Binance Spot testnet WebSocket connectivity."""

from __future__ import annotations

import asyncio
import json
import time

import aiohttp
import pytest
import websockets

from tests.testnet.conftest import (
    HTTP_OK,
    MIN_ORDER_QUOTE_QTY,
    REST_BASE,
    SESSION_TIMEOUT,
    SYMBOL,
    WS_BASE,
    WS_CLOSE_TIMEOUT,
    WS_RECV_TIMEOUT,
    auth_headers,
    pytestmark,
    signed_params,
    skip_no_creds,
)

__all__ = ["pytestmark"]


@skip_no_creds
@pytest.mark.asyncio
async def test_create_listen_key() -> None:
    """Verify POST /api/v3/userDataStream returns a listenKey."""

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.post(f"{REST_BASE}/api/v3/userDataStream", headers=auth_headers()) as r,
    ):
        assert r.status == HTTP_OK
        data = await r.json()
    assert len(data.get("listenKey", "")) > 0


@skip_no_creds
@pytest.mark.asyncio
async def test_ws_connect() -> None:
    """Verify WebSocket connection to user data stream opens and closes cleanly."""

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.post(f"{REST_BASE}/api/v3/userDataStream", headers=auth_headers()) as r,
    ):
        assert r.status == HTTP_OK
        listen_key = (await r.json())["listenKey"]
    async with websockets.connect(
        f"{WS_BASE}/ws/{listen_key}", close_timeout=WS_CLOSE_TIMEOUT
    ):
        pass


@skip_no_creds
@pytest.mark.asyncio
async def test_listen_key_keepalive() -> None:
    """Verify PUT /api/v3/userDataStream keepalive returns 200."""

    async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s:
        async with s.post(
            f"{REST_BASE}/api/v3/userDataStream", headers=auth_headers()
        ) as r:
            assert r.status == HTTP_OK
            listen_key = (await r.json())["listenKey"]
        async with s.put(
            f"{REST_BASE}/api/v3/userDataStream",
            headers=auth_headers(),
            params={"listenKey": listen_key},
        ) as r:
            assert r.status == HTTP_OK


@skip_no_creds
@pytest.mark.asyncio
async def test_e2e_fill() -> None:
    """Verify market order submission and executionReport arrival on WebSocket."""

    async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s:
        async with s.post(
            f"{REST_BASE}/api/v3/userDataStream", headers=auth_headers()
        ) as r:
            assert r.status == HTTP_OK
            listen_key = (await r.json())["listenKey"]

        async with websockets.connect(
            f"{WS_BASE}/ws/{listen_key}", close_timeout=WS_CLOSE_TIMEOUT
        ) as ws:
            params = signed_params(
                symbol=SYMBOL,
                side="BUY",
                type="MARKET",
                quoteOrderQty=MIN_ORDER_QUOTE_QTY,
            )
            async with s.post(
                f"{REST_BASE}/api/v3/order",
                params=params,
                headers=auth_headers(),
            ) as r:
                assert r.status == HTTP_OK, f"Order rejected: {await r.text()}"
                order_data = await r.json()
            order_id = order_data["orderId"]

            deadline = time.time() + WS_RECV_TIMEOUT
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except TimeoutError:
                    break
                event = json.loads(msg)
                if (
                    event.get("e") == "executionReport"
                    and event.get("i") == order_id
                    and event.get("X") == "FILLED"
                ):
                    return

            pytest.fail(
                f"No executionReport for order {order_id} within {WS_RECV_TIMEOUT}s"
            )
