'''Verify unauthenticated Binance Spot testnet REST endpoints.'''

from __future__ import annotations

import time

import aiohttp
import pytest

from tests.testnet.conftest import (
    HTTP_OK,
    MAX_CLOCK_SKEW_MS,
    RATE_LIMIT_HEADER,
    REST_BASE,
    SESSION_TIMEOUT,
    SYMBOL,
    pytestmark,
)

__all__ = ['pytestmark']


@pytest.mark.asyncio
async def test_ping() -> None:
    '''Verify GET /api/v3/ping returns 200.'''

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.get(f"{REST_BASE}/api/v3/ping") as r,
    ):
        assert r.status == HTTP_OK


@pytest.mark.asyncio
async def test_server_time() -> None:
    '''Verify GET /api/v3/time returns server timestamp with clock skew < 5s.'''

    async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s:
        local_before = int(time.time() * 1000)
        async with s.get(f"{REST_BASE}/api/v3/time") as r:
            assert r.status == HTTP_OK
            data = await r.json()
        local_after = int(time.time() * 1000)
    server_time = data['serverTime']
    skew_ms = server_time - (local_before + local_after) // 2
    assert abs(skew_ms) < MAX_CLOCK_SKEW_MS, f"Clock skew {skew_ms}ms exceeds 5s"


@pytest.mark.asyncio
async def test_exchange_info() -> None:
    '''Verify GET /api/v3/exchangeInfo returns PRICE_FILTER and LOT_SIZE for BTCUSDT.'''

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.get(f"{REST_BASE}/api/v3/exchangeInfo", params={'symbol': SYMBOL}) as r,
    ):
        assert r.status == HTTP_OK
        data = await r.json()
    symbols = data['symbols']
    assert len(symbols) > 0
    filters = symbols[0]['filters']
    filter_types = [f['filterType'] for f in filters]
    assert 'PRICE_FILTER' in filter_types
    assert 'LOT_SIZE' in filter_types


@pytest.mark.asyncio
async def test_order_book_depth() -> None:
    '''Verify GET /api/v3/depth returns non-empty bids and asks.'''

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.get(
            f"{REST_BASE}/api/v3/depth", params={'symbol': SYMBOL, 'limit': '5'}
        ) as r,
    ):
        assert r.status == HTTP_OK
        data = await r.json()
    assert len(data['bids']) > 0
    assert len(data['asks']) > 0


@pytest.mark.asyncio
async def test_rate_limit_headers() -> None:
    '''Verify rate limit header is present on responses.'''

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.get(f"{REST_BASE}/api/v3/ping") as r,
    ):
        assert r.status == HTTP_OK
        weight = r.headers.get(RATE_LIMIT_HEADER)
    assert weight is not None, f"{RATE_LIMIT_HEADER} header missing"
