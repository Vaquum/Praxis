'''Verify authenticated Binance Spot testnet REST endpoints.'''

from __future__ import annotations

import aiohttp
import pytest

from tests.testnet.conftest import (
    HTTP_OK,
    REST_BASE,
    SESSION_TIMEOUT,
    auth_headers,
    pytestmark,
    signed_params,
    skip_no_creds,
)

__all__ = ['pytestmark']


@skip_no_creds
@pytest.mark.asyncio
async def test_account_auth() -> None:
    '''Verify GET /api/v3/account with signed params returns balances.'''

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.get(
            f"{REST_BASE}/api/v3/account",
            params=signed_params(),
            headers=auth_headers(),
        ) as r,
    ):
        assert r.status == HTTP_OK, f"Auth failed: status {r.status}"
        data = await r.json()
    assert 'balances' in data
