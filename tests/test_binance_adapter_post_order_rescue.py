'''Tests for `BinanceAdapter._post_order` retry/rescue policy (MAJOR-002).

Order POSTs are non-idempotent: the venue may have accepted the
request even when the response was lost. With a `client_order_id`
supplied (production always passes one), `_post_order` runs without
transport retries and translates rescue-trigger conditions into
`OrderSubmitTimeoutError` / `DuplicateClientOrderIdError`.
'''

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from praxis.core.domain.enums import OrderSide, OrderType
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.secret_store import Credentials
from praxis.infrastructure.venue_adapter import (
    DuplicateClientOrderIdError,
    OrderRejectedError,
    OrderSubmitTimeoutError,
)

_BASE_URL = 'https://stub'
_WS_BASE_URL = 'wss://stub'
_WS_API_URL = 'wss://stub-ws-api'
_ACCOUNT_ID = 'acc1'
_API_KEY = 'k'
_API_SECRET = 's'
_CLIENT_ORDER_ID = 'cid-test-001'


def _make_adapter() -> BinanceAdapter:
    return BinanceAdapter(
        _BASE_URL, _WS_BASE_URL, _WS_API_URL,
        {_ACCOUNT_ID: Credentials(api_key=_API_KEY, api_secret=_API_SECRET)},
    )


def _patch_session_with_side_effect(
    adapter: BinanceAdapter,
    side_effect: object,
) -> MagicMock:
    session = MagicMock()
    session.request = MagicMock(side_effect=side_effect)
    session.closed = False
    adapter._session = session
    return session


class TestPostOrderRescuePolicy:

    @pytest.mark.asyncio
    async def test_timeout_with_client_order_id_raises_submit_timeout_no_retry(
        self,
    ) -> None:
        '''A POST timeout with clientOrderId set raises OrderSubmitTimeoutError
        on the first attempt — no retries, so the venue cannot have accepted
        a duplicate.'''

        adapter = _make_adapter()
        session = _patch_session_with_side_effect(
            adapter, TimeoutError('connection timed out'),
        )

        with pytest.raises(OrderSubmitTimeoutError) as exc_info:
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('0.5'),
                client_order_id=_CLIENT_ORDER_ID,
            )

        assert exc_info.value.client_order_id == _CLIENT_ORDER_ID
        assert session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_client_error_with_client_order_id_raises_submit_timeout_no_retry(
        self,
    ) -> None:
        '''aiohttp.ClientError with clientOrderId surfaces as OrderSubmitTimeoutError
        without retry.'''

        adapter = _make_adapter()
        session = _patch_session_with_side_effect(
            adapter, aiohttp.ClientError('connection reset'),
        )

        with pytest.raises(OrderSubmitTimeoutError) as exc_info:
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('0.5'),
                client_order_id=_CLIENT_ORDER_ID,
            )

        assert exc_info.value.client_order_id == _CLIENT_ORDER_ID
        assert session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_duplicate_client_order_id_code_raises_distinct_error(
        self,
    ) -> None:
        '''A `-2010 Duplicate clientOrderId` rejection surfaces as
        DuplicateClientOrderIdError, not OrderRejectedError.'''

        adapter = _make_adapter()
        resp = AsyncMock()
        resp.status = 400
        resp.json = AsyncMock(
            return_value={'code': -2010, 'msg': 'Order already exists'},
        )
        resp.headers = {}
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=False)
        session = _patch_session_with_side_effect(adapter, [ctx])

        with pytest.raises(DuplicateClientOrderIdError) as exc_info:
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('0.5'),
                client_order_id=_CLIENT_ORDER_ID,
            )

        assert exc_info.value.client_order_id == _CLIENT_ORDER_ID
        assert session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_other_venue_rejects_still_raise_order_rejected_error(
        self,
    ) -> None:
        '''A non-`-2010` venue rejection (e.g., `-1013` filter failure) still
        propagates as OrderRejectedError — only `-2010` triggers the rescue path.'''

        adapter = _make_adapter()
        resp = AsyncMock()
        resp.status = 400
        resp.json = AsyncMock(
            return_value={'code': -1013, 'msg': 'Filter failure'},
        )
        resp.headers = {}
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=False)
        _patch_session_with_side_effect(adapter, [ctx])

        with pytest.raises(OrderRejectedError) as exc_info:
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('0.5'),
                client_order_id=_CLIENT_ORDER_ID,
            )

        assert exc_info.value.venue_code == -1013

    @pytest.mark.asyncio
    async def test_success_path_returns_normally(self) -> None:
        '''Happy path: a successful POST returns a SubmitResult.'''

        adapter = _make_adapter()
        resp = AsyncMock()
        resp.status = 200
        resp.json = AsyncMock(return_value={
            'orderId': 12345,
            'status': 'FILLED',
            'executedQty': '0.5',
            'cummulativeQuoteQty': '25000',
            'fills': [],
        })
        resp.headers = {}
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=False)
        session = _patch_session_with_side_effect(adapter, [ctx])

        result = await adapter.submit_order(
            _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
            Decimal('0.5'),
            client_order_id=_CLIENT_ORDER_ID,
        )

        assert result.venue_order_id == '12345'
        assert session.request.call_count == 1
