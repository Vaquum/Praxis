'''
Tests for praxis.infrastructure.binance_adapter.
'''

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from praxis.core.domain.enums import ExecutionType, OrderSide, OrderStatus, OrderType
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.venue_adapter import (
    AuthenticationError,
    BalanceEntry,
    CancelResult,
    ExecutionReport,
    NotFoundError,
    OrderRejectedError,
    RateLimitError,
    SymbolFilters,
    TransientError,
    VenueError,
    VenueOrder,
    VenueTrade,
)


_BASE_URL = 'https://testnet.binance.vision'
_WS_BASE_URL = 'wss://stream.testnet.binance.vision'
_ACCOUNT_ID = 'test-account'
_API_KEY = 'test-api-key'
_API_SECRET = 'test-api-secret'  # noqa: S105
_VENUE_ORDER_ID = '12345'
_VENUE_TRADE_ID = '99'
_BINANCE_REJECTION_CODE = -1013
_BINANCE_REJECTION_MSG = 'Filter failure: MIN_NOTIONAL'
_SHA256_HEX_LENGTH = 64
_FALLBACK_VENUE_CODE = -1
_BINANCE_ORDER_NOT_EXIST_CODE = -2013
_BINANCE_UNKNOWN_ORDER_CODE = -2011
_BINANCE_ORDER_NOT_EXIST_MSG = 'Order does not exist.'
_BINANCE_UNKNOWN_ORDER_MSG = 'Unknown order sent.'

_BINANCE_FILLED_RESPONSE: dict[str, Any] = {
    'orderId': 12345,
    'status': 'FILLED',
    'fills': [
        {
            'tradeId': 99,
            'qty': '0.5',
            'price': '50000.00',
            'commission': '0.001',
            'commissionAsset': 'BTC',
        },
    ],
}

_BINANCE_NEW_RESPONSE: dict[str, Any] = {
    'orderId': 12345,
    'status': 'NEW',
    'fills': [],
}

_BINANCE_EXPIRED_RESPONSE: dict[str, Any] = {
    'orderId': 12345,
    'status': 'EXPIRED',
    'fills': [],
}

_BINANCE_LIMIT_ORDER_RESPONSE: dict[str, Any] = {
    'orderId': 12345,
    'clientOrderId': 'my-client-id',
    'status': 'NEW',
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'LIMIT',
    'timeInForce': 'GTC',
    'origQty': '1.00000000',
    'executedQty': '0.00000000',
    'price': '50000.00000000',
}

_BINANCE_MARKET_ORDER_RESPONSE: dict[str, Any] = {
    'orderId': 12345,
    'clientOrderId': 'my-client-id',
    'status': 'FILLED',
    'symbol': 'BTCUSDT',
    'side': 'SELL',
    'type': 'MARKET',
    'timeInForce': 'GTC',
    'origQty': '0.50000000',
    'executedQty': '0.50000000',
    'price': '0.00000000',
}

_BINANCE_LIMIT_IOC_ORDER_RESPONSE: dict[str, Any] = {
    'orderId': 12345,
    'clientOrderId': 'my-client-id',
    'status': 'EXPIRED',
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'LIMIT',
    'timeInForce': 'IOC',
    'origQty': '1.00000000',
    'executedQty': '0.30000000',
    'price': '50000.00000000',
}

_BINANCE_TRADE_RESPONSE: dict[str, Any] = {
    'id': 99,
    'orderId': 12345,
    'clientOrderId': 'my-client-id',
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'qty': '0.50000000',
    'price': '50000.12345678',
    'commission': '0.00050000',
    'commissionAsset': 'BTC',
    'isMaker': True,
    'time': 1700000000000,
}

_BINANCE_OCO_RESPONSE: dict[str, Any] = {
    'orderListId': 99999,
    'contingencyType': 'OCO',
    'listStatusType': 'EXEC_STARTED',
    'listOrderStatus': 'EXECUTING',
    'listClientOrderId': 'oco-list-1',
    'transactionTime': 1700000000000,
    'symbol': 'BTCUSDT',
    'orders': [
        {'symbol': 'BTCUSDT', 'orderId': 10, 'clientOrderId': 'limit-leg'},
        {'symbol': 'BTCUSDT', 'orderId': 11, 'clientOrderId': 'stop-leg'},
    ],
    'orderReports': [
        {
            'symbol': 'BTCUSDT',
            'orderId': 10,
            'orderListId': 99999,
            'clientOrderId': 'limit-leg',
            'transactTime': 1700000000000,
            'price': '50000.00',
            'origQty': '0.01',
            'executedQty': '0.00',
            'status': 'NEW',
            'timeInForce': 'GTC',
            'type': 'LIMIT_MAKER',
            'side': 'SELL',
            'fills': [],
        },
        {
            'symbol': 'BTCUSDT',
            'orderId': 11,
            'orderListId': 99999,
            'clientOrderId': 'stop-leg',
            'transactTime': 1700000000000,
            'price': '47500.00',
            'origQty': '0.01',
            'executedQty': '0.00',
            'status': 'NEW',
            'timeInForce': 'GTC',
            'type': 'STOP_LOSS_LIMIT',
            'side': 'SELL',
            'stopPrice': '48000.00',
            'fills': [],
        },
    ],
}

_BINANCE_OCO_RESPONSE_WITH_FILLS: dict[str, Any] = {
    'orderListId': 99999,
    'contingencyType': 'OCO',
    'listStatusType': 'ALL_DONE',
    'listOrderStatus': 'ALL_DONE',
    'listClientOrderId': 'oco-list-2',
    'transactionTime': 1700000000000,
    'symbol': 'BTCUSDT',
    'orders': [
        {'symbol': 'BTCUSDT', 'orderId': 20, 'clientOrderId': 'limit-leg-2'},
        {'symbol': 'BTCUSDT', 'orderId': 21, 'clientOrderId': 'stop-leg-2'},
    ],
    'orderReports': [
        {
            'symbol': 'BTCUSDT',
            'orderId': 20,
            'orderListId': 99999,
            'clientOrderId': 'limit-leg-2',
            'transactTime': 1700000000000,
            'price': '50000.00',
            'origQty': '0.01',
            'executedQty': '0.01',
            'status': 'FILLED',
            'timeInForce': 'GTC',
            'type': 'LIMIT_MAKER',
            'side': 'SELL',
            'fills': [
                {
                    'tradeId': 201,
                    'qty': '0.01',
                    'price': '50000.00',
                    'commission': '0.00001',
                    'commissionAsset': 'BTC',
                },
            ],
        },
        {
            'symbol': 'BTCUSDT',
            'orderId': 21,
            'orderListId': 99999,
            'clientOrderId': 'stop-leg-2',
            'transactTime': 1700000000000,
            'price': '47500.00',
            'origQty': '0.01',
            'executedQty': '0.00',
            'status': 'CANCELED',
            'timeInForce': 'GTC',
            'type': 'STOP_LOSS_LIMIT',
            'side': 'SELL',
            'stopPrice': '48000.00',
            'fills': [],
        },
    ],
}

_BINANCE_EXCHANGE_INFO_RESPONSE: dict[str, Any] = {
    'rateLimits': [
        {'rateLimitType': 'REQUEST_WEIGHT', 'interval': 'MINUTE', 'intervalNum': 1, 'limit': 1200},
        {'rateLimitType': 'ORDERS', 'interval': 'SECOND', 'intervalNum': 10, 'limit': 100},
        {'rateLimitType': 'ORDERS', 'interval': 'DAY', 'intervalNum': 1, 'limit': 200000},
    ],
    'symbols': [
        {
            'symbol': 'BTCUSDT',
            'filters': [
                {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'},
                {'filterType': 'LOT_SIZE', 'stepSize': '0.00001', 'minQty': '0.00001', 'maxQty': '9000.0'},
                {'filterType': 'NOTIONAL', 'minNotional': '5.0'},
                {'filterType': 'ICEBERG_PARTS', 'limit': '10'},
            ],
        },
    ],
}


_BINANCE_EXCHANGE_INFO_MISSING_FILTER: dict[str, Any] = {
    'symbols': [
        {
            'symbol': 'BTCUSDT',
            'filters': [
                {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'},
                {'filterType': 'LOT_SIZE', 'stepSize': '0.00001', 'minQty': '0.00001', 'maxQty': '9000.0'},
            ],
        },
    ],
}


_TEST_FILTERS = SymbolFilters(
    symbol='BTCUSDT',
    tick_size=Decimal('0.01'),
    lot_step=Decimal('0.00001'),
    lot_min=Decimal('0.001'),
    lot_max=Decimal('9000.0'),
    min_notional=Decimal('5.0'),
)


def _make_adapter(
    credentials: dict[str, tuple[str, str]] | None = None,
) -> BinanceAdapter:

    '''
    Create a BinanceAdapter with default test credentials.

    Args:
        credentials (dict[str, tuple[str, str]] | None): Override credentials

    Returns:
        BinanceAdapter: Adapter configured for testing
    '''

    creds = credentials or {_ACCOUNT_ID: (_API_KEY, _API_SECRET)}
    return BinanceAdapter(_BASE_URL, _WS_BASE_URL, creds)


def _mock_response(
    status: int,
    data: Any = None,
    headers: dict[str, str] | None = None,
) -> AsyncMock:

    '''
    Create a mock aiohttp response.

    Args:
        status (int): HTTP status code
        data (Any): JSON response body
        headers (dict[str, str] | None): Response headers

    Returns:
        AsyncMock: Mock response with status, json(), and headers
    '''

    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data if data is not None else {})
    resp.headers = headers or {}
    return resp


def _patch_session(adapter: BinanceAdapter, response: AsyncMock) -> None:

    '''
    Inject a mock session into the adapter.

    Args:
        adapter (BinanceAdapter): Adapter to patch
        response (AsyncMock): Mock response for session.request()
    '''

    session = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.request = MagicMock(return_value=ctx)
    session.closed = False
    adapter._session = session


class TestCredentialManagement:

    def test_register_account(self) -> None:

        adapter = BinanceAdapter(_BASE_URL, _WS_BASE_URL)
        adapter.register_account('acc1', 'key1', 'secret1')
        assert adapter._get_credentials('acc1') == ('key1', 'secret1')

    def test_unregister_account(self) -> None:

        adapter = _make_adapter()
        adapter.unregister_account(_ACCOUNT_ID)
        with pytest.raises(AuthenticationError):
            adapter._get_credentials(_ACCOUNT_ID)

    def test_unregister_unknown_raises_key_error(self) -> None:

        adapter = BinanceAdapter(_BASE_URL, _WS_BASE_URL)
        with pytest.raises(KeyError):
            adapter.unregister_account('nonexistent')

    def test_get_credentials_unknown_raises_auth_error(self) -> None:

        adapter = BinanceAdapter(_BASE_URL, _WS_BASE_URL)
        with pytest.raises(AuthenticationError, match='No credentials'):
            adapter._get_credentials('unknown')


class TestSigningAndAuth:

    def test_sign_params_returns_signed_query_string(self) -> None:

        adapter = _make_adapter()
        query = adapter._sign_params({'symbol': 'BTCUSDT'}, _API_SECRET)
        assert 'timestamp=' in query
        assert '&signature=' in query
        signature = query.split('signature=')[1]
        assert len(signature) == _SHA256_HEX_LENGTH

    def test_sign_params_preserves_original_params(self) -> None:

        adapter = _make_adapter()
        original = {'symbol': 'BTCUSDT', 'side': 'BUY'}
        query = adapter._sign_params(original, _API_SECRET)
        assert 'symbol=BTCUSDT' in query
        assert 'side=BUY' in query
        assert 'timestamp' not in original
        assert 'signature' not in original

class TestSignedRequest:

    @pytest.mark.asyncio
    async def test_url_contains_path_and_signed_params(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'result': 'ok'}))
        await adapter._signed_request('GET', '/api/v3/order', {'symbol': 'BTCUSDT'}, _ACCOUNT_ID)
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        method = call_args[0][0]
        url = call_args[0][1]
        assert method == 'GET'
        assert url.startswith(f"{_BASE_URL}/api/v3/order?")
        assert 'symbol=BTCUSDT' in url
        assert 'timestamp=' in url
        assert 'signature=' in url

    @pytest.mark.asyncio
    async def test_delete_method_dispatched(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'orderId': 1, 'status': 'CANCELED'}))
        await adapter._signed_request('DELETE', '/api/v3/order', {'symbol': 'BTCUSDT'}, _ACCOUNT_ID)
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        assert call_args[0][0] == 'DELETE'

    @pytest.mark.asyncio
    async def test_api_key_header_sent(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'result': 'ok'}))
        await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        headers = call_args.kwargs['headers']
        assert headers['X-MBX-APIKEY'] == _API_KEY

    @pytest.mark.asyncio
    async def test_venue_error_not_wrapped(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(401))
        with pytest.raises(AuthenticationError):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

    @pytest.mark.asyncio
    async def test_transport_error_wrapped_as_transient(self) -> None:

        adapter = _make_adapter()
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError())
        session.closed = False
        adapter._session = session
        with (
            patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock),
            pytest.raises(TransientError, match='Request failed'),
        ):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

    @pytest.mark.asyncio
    async def test_updates_weight_from_headers(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(
            200, {'result': 'ok'},
            headers={'X-MBX-USED-WEIGHT-1M': '150'},
        ))
        await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)
        assert adapter._used_weight == 150

    @pytest.mark.asyncio
    async def test_updates_order_count_from_headers(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(
            200, {'result': 'ok'},
            headers={'X-MBX-ORDER-COUNT-10S': '7'},
        ))
        await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)
        assert adapter._order_count[_ACCOUNT_ID] == 7

    @pytest.mark.asyncio
    async def test_logs_warning_on_low_headroom(self) -> None:

        adapter = _make_adapter()
        adapter._weight_limit = 1000
        _patch_session(adapter, _mock_response(
            200, {'result': 'ok'},
            headers={'X-MBX-USED-WEIGHT-1M': '900'},
        ))
        with patch('praxis.infrastructure.binance_adapter._log') as mock_log:
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)
            mock_log.warning.assert_called_once()
            assert 'headroom low' in mock_log.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_unparseable_weight_header_ignored(self) -> None:

        adapter = _make_adapter()
        adapter._used_weight = 50
        _patch_session(adapter, _mock_response(
            200, {'result': 'ok'},
            headers={'X-MBX-USED-WEIGHT-1M': 'garbage'},
        ))
        await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)
        assert adapter._used_weight == 50

    @pytest.mark.asyncio
    async def test_missing_headers_preserve_state(self) -> None:

        adapter = _make_adapter()
        adapter._used_weight = 100
        adapter._order_count[_ACCOUNT_ID] = 5
        _patch_session(adapter, _mock_response(200, {'result': 'ok'}))
        await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)
        assert adapter._used_weight == 100
        assert adapter._order_count[_ACCOUNT_ID] == 5

class TestRetry:

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self) -> None:

        adapter = _make_adapter()
        fail_resp = _mock_response(500)
        ok_resp = _mock_response(200, {'result': 'ok'})

        fail_ctx = MagicMock()
        fail_ctx.__aenter__ = AsyncMock(return_value=fail_resp)
        fail_ctx.__aexit__ = AsyncMock(return_value=False)

        ok_ctx = MagicMock()
        ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
        ok_ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[fail_ctx, ok_ctx])
        session.closed = False
        adapter._session = session

        with patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        assert result == {'result': 'ok'}
        assert session.request.call_count == 2
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_exhaustion_raises_transient_error(self) -> None:

        adapter = _make_adapter()
        fail_resp = _mock_response(500)

        contexts = []
        for _ in range(3):
            ctx = MagicMock()
            ctx.__aenter__ = AsyncMock(return_value=fail_resp)
            ctx.__aexit__ = AsyncMock(return_value=False)
            contexts.append(ctx)

        session = MagicMock()
        session.request = MagicMock(side_effect=contexts)
        session.closed = False
        adapter._session = session

        with (
            patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock),
            pytest.raises(TransientError, match='Venue server error'),
        ):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        assert session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_auth_error_not_retried(self) -> None:

        adapter = _make_adapter()
        fail_resp = _mock_response(401)

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=fail_resp)
        ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(return_value=ctx)
        session.closed = False
        adapter._session = session

        with pytest.raises(AuthenticationError):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        assert session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_order_rejected_not_retried(self) -> None:

        adapter = _make_adapter()
        fail_resp = _mock_response(400, {'code': -1013, 'msg': 'Invalid quantity'})

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=fail_resp)
        ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(return_value=ctx)
        session.closed = False
        adapter._session = session

        with pytest.raises(OrderRejectedError):
            await adapter._signed_request('POST', '/api/v3/order', {}, _ACCOUNT_ID)

        assert session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_calls_asyncio_sleep(self) -> None:

        adapter = _make_adapter()
        fail_resp = _mock_response(500)
        ok_resp = _mock_response(200, {'result': 'ok'})

        fail_ctx = MagicMock()
        fail_ctx.__aenter__ = AsyncMock(return_value=fail_resp)
        fail_ctx.__aexit__ = AsyncMock(return_value=False)

        ok_ctx = MagicMock()
        ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
        ok_ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[fail_ctx, ok_ctx])
        session.closed = False
        adapter._session = session

        with patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 0 <= delay <= 0.5

    @pytest.mark.asyncio
    async def test_retry_logs_warning(self) -> None:

        adapter = _make_adapter()
        fail_resp = _mock_response(500)
        ok_resp = _mock_response(200, {'result': 'ok'})

        fail_ctx = MagicMock()
        fail_ctx.__aenter__ = AsyncMock(return_value=fail_resp)
        fail_ctx.__aexit__ = AsyncMock(return_value=False)

        ok_ctx = MagicMock()
        ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
        ok_ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[fail_ctx, ok_ctx])
        session.closed = False
        adapter._session = session

        with (
            patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock),
            patch('praxis.infrastructure.binance_adapter._log') as mock_log,
        ):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        mock_log.warning.assert_called_once()
        assert 'attempt 1/3' in mock_log.warning.call_args[0][0] % mock_log.warning.call_args[0][1:]

    @pytest.mark.asyncio
    async def test_exhaustion_logs_error(self) -> None:

        adapter = _make_adapter()
        fail_resp = _mock_response(500)

        contexts = []
        for _ in range(3):
            ctx = MagicMock()
            ctx.__aenter__ = AsyncMock(return_value=fail_resp)
            ctx.__aexit__ = AsyncMock(return_value=False)
            contexts.append(ctx)

        session = MagicMock()
        session.request = MagicMock(side_effect=contexts)
        session.closed = False
        adapter._session = session

        with (
            patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock),
            patch('praxis.infrastructure.binance_adapter._log') as mock_log,
            pytest.raises(TransientError),
        ):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        mock_log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_transport_error_retried(self) -> None:

        adapter = _make_adapter()
        ok_resp = _mock_response(200, {'result': 'ok'})

        ok_ctx = MagicMock()
        ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
        ok_ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[aiohttp.ClientError('conn reset'), ok_ctx])
        session.closed = False
        adapter._session = session

        with patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        assert result == {'result': 'ok'}
        assert session.request.call_count == 2
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_retried_with_retry_after(self) -> None:

        adapter = _make_adapter()
        rate_resp = _mock_response(429, headers={'Retry-After': '3'})
        ok_resp = _mock_response(200, {'result': 'ok'})

        rate_ctx = MagicMock()
        rate_ctx.__aenter__ = AsyncMock(return_value=rate_resp)
        rate_ctx.__aexit__ = AsyncMock(return_value=False)

        ok_ctx = MagicMock()
        ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
        ok_ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[rate_ctx, ok_ctx])
        session.closed = False
        adapter._session = session

        with patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        assert result == {'result': 'ok'}
        assert session.request.call_count == 2
        mock_sleep.assert_called_once_with(3.0)

    @pytest.mark.asyncio
    async def test_rate_limit_exhaustion_raises(self) -> None:

        adapter = _make_adapter()
        rate_resp = _mock_response(429)

        contexts = []
        for _ in range(3):
            ctx = MagicMock()
            ctx.__aenter__ = AsyncMock(return_value=rate_resp)
            ctx.__aexit__ = AsyncMock(return_value=False)
            contexts.append(ctx)

        session = MagicMock()
        session.request = MagicMock(side_effect=contexts)
        session.closed = False
        adapter._session = session

        with (
            patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock),
            pytest.raises(RateLimitError),
        ):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        assert session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_retry_without_retry_after_uses_backoff(self) -> None:

        adapter = _make_adapter()
        rate_resp = _mock_response(429)
        ok_resp = _mock_response(200, {'result': 'ok'})

        rate_ctx = MagicMock()
        rate_ctx.__aenter__ = AsyncMock(return_value=rate_resp)
        rate_ctx.__aexit__ = AsyncMock(return_value=False)

        ok_ctx = MagicMock()
        ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
        ok_ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[rate_ctx, ok_ctx])
        session.closed = False
        adapter._session = session

        with patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 0 <= delay <= 0.5

    @pytest.mark.asyncio
    async def test_403_rate_limit_not_retried(self) -> None:

        adapter = _make_adapter()
        resp_403 = _mock_response(403)

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=resp_403)
        ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[ctx])
        session.closed = False
        adapter._session = session

        with pytest.raises(RateLimitError, match='Rate limited'):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        session.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_418_rate_limit_not_retried(self) -> None:

        adapter = _make_adapter()
        resp_418 = _mock_response(418)

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=resp_418)
        ctx.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.request = MagicMock(side_effect=[ctx])
        session.closed = False
        adapter._session = session

        with pytest.raises(RateLimitError, match='Rate limited'):
            await adapter._signed_request('GET', '/api/v3/order', {}, _ACCOUNT_ID)

        session.request.assert_called_once()

class TestBuildOrderParams:

    def test_market_order(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.MARKET, Decimal('0.5'),
        )
        assert params['type'] == 'MARKET'
        assert params['symbol'] == 'BTCUSDT'
        assert params['side'] == 'BUY'
        assert params['quantity'] == '0.5'
        assert params['newOrderRespType'] == 'FULL'
        assert 'price' not in params
        assert 'timeInForce' not in params

    def test_limit_order_defaults_gtc(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.SELL, OrderType.LIMIT, Decimal('1.0'),
            price=Decimal('50000'),
        )
        assert params['type'] == 'LIMIT'
        assert params['price'] == '50000'
        assert params['timeInForce'] == 'GTC'

    def test_limit_order_custom_tif(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.LIMIT, Decimal('1.0'),
            price=Decimal('50000'), time_in_force='FOK',
        )
        assert params['timeInForce'] == 'FOK'

    def test_limit_ioc_order(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.LIMIT_IOC, Decimal('1.0'),
            price=Decimal('50000'),
        )
        assert params['type'] == 'LIMIT'
        assert params['price'] == '50000'
        assert params['timeInForce'] == 'IOC'

    def test_limit_ioc_forces_ioc(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.LIMIT_IOC, Decimal('1.0'),
            price=Decimal('50000'), time_in_force='GTC',
        )
        assert params['timeInForce'] == 'IOC'

    def test_limit_missing_price_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='price is required for LIMIT'):
            adapter._build_order_params(
                'BTCUSDT', OrderSide.BUY, OrderType.LIMIT, Decimal('1.0'),
            )

    def test_limit_ioc_missing_price_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='price is required for LIMIT_IOC'):
            adapter._build_order_params(
                'BTCUSDT', OrderSide.BUY, OrderType.LIMIT_IOC, Decimal('1.0'),
            )

    def test_unsupported_order_type_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='Unsupported order type'):
            adapter._build_order_params(
                'BTCUSDT', OrderSide.BUY, OrderType.STOP, Decimal('1.0'),
            )

    def test_stop_price_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='stop_price is not supported'):
            adapter._build_order_params(
                'BTCUSDT', OrderSide.BUY, OrderType.MARKET, Decimal('1.0'),
                stop_price=Decimal('49000'),
            )

    def test_client_order_id_included(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.MARKET, Decimal('1.0'),
            client_order_id='new_order-cmd1-0',
        )
        assert params['newClientOrderId'] == 'new_order-cmd1-0'

    def test_decimal_serialization(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.LIMIT, Decimal('0.00100'),
            price=Decimal('50000.50'),
        )
        assert params['quantity'] == '0.00100'
        assert params['price'] == '50000.50'

    def test_decimal_scientific_notation_avoided(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.LIMIT, Decimal('1E-7'),
            price=Decimal('1E+4'),
        )
        assert params['quantity'] == '0.0000001'
        assert params['price'] == '10000'


class TestMapOrderStatus:

    @pytest.mark.parametrize(
        ('binance_status', 'expected'),
        [
            ('NEW', OrderStatus.OPEN),
            ('PARTIALLY_FILLED', OrderStatus.PARTIALLY_FILLED),
            ('FILLED', OrderStatus.FILLED),
            ('CANCELED', OrderStatus.CANCELED),
            ('REJECTED', OrderStatus.REJECTED),
            ('EXPIRED', OrderStatus.EXPIRED),
            ('EXPIRED_IN_MATCH', OrderStatus.EXPIRED),
        ],
    )
    def test_known_statuses(
        self, binance_status: str, expected: OrderStatus,
    ) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_status(binance_status) == expected

    def test_unknown_status_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='Unknown Binance order status'):
            adapter._map_order_status('IMAGINARY')

class TestMapOrderType:

    def test_market(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('MARKET', 'GTC') == OrderType.MARKET

    def test_limit_gtc(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('LIMIT', 'GTC') == OrderType.LIMIT

    def test_limit_ioc(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('LIMIT', 'IOC') == OrderType.LIMIT_IOC

    def test_limit_fok(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('LIMIT', 'FOK') == OrderType.LIMIT_IOC

    def test_limit_maker(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('LIMIT_MAKER', 'GTC') == OrderType.LIMIT

    def test_stop_loss(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('STOP_LOSS', 'GTC') == OrderType.STOP

    def test_stop_loss_limit(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('STOP_LOSS_LIMIT', 'GTC') == OrderType.STOP_LIMIT

    def test_take_profit(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('TAKE_PROFIT', 'GTC') == OrderType.TAKE_PROFIT

    def test_take_profit_limit(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('TAKE_PROFIT_LIMIT', 'GTC') == OrderType.TP_LIMIT

    def test_oco(self) -> None:

        adapter = _make_adapter()
        assert adapter._map_order_type('OCO', '') == OrderType.OCO

    def test_unknown_type_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='Unknown Binance order type'):
            adapter._map_order_type('TRAILING_STOP', 'GTC')


class TestParseSubmitResponse:

    def test_filled_with_fills(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_submit_response(_BINANCE_FILLED_RESPONSE)
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.status == OrderStatus.FILLED
        assert len(result.immediate_fills) == 1
        fill = result.immediate_fills[0]
        assert fill.venue_trade_id == _VENUE_TRADE_ID
        assert fill.qty == Decimal('0.5')
        assert fill.price == Decimal('50000.00')
        assert fill.fee == Decimal('0.001')
        assert fill.fee_asset == 'BTC'
        assert fill.is_maker is False

    def test_new_no_fills(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_submit_response(_BINANCE_NEW_RESPONSE)
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.status == OrderStatus.OPEN
        assert result.immediate_fills == ()

    def test_expired_no_fills(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_submit_response(_BINANCE_EXPIRED_RESPONSE)
        assert result.status == OrderStatus.EXPIRED
        assert result.immediate_fills == ()

class TestParseVenueOrder:

    def test_limit_order(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_venue_order(_BINANCE_LIMIT_ORDER_RESPONSE)
        assert isinstance(result, VenueOrder)
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.client_order_id == 'my-client-id'
        assert result.status == OrderStatus.OPEN
        assert result.symbol == 'BTCUSDT'
        assert result.side == OrderSide.BUY
        assert result.order_type == OrderType.LIMIT
        assert result.qty == Decimal('1.0')
        assert result.filled_qty == Decimal('0.0')
        assert result.price == Decimal('50000.0')

    def test_market_order_price_is_none(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_venue_order(_BINANCE_MARKET_ORDER_RESPONSE)
        assert result.order_type == OrderType.MARKET
        assert result.price is None
        assert result.side == OrderSide.SELL
        assert result.status == OrderStatus.FILLED
        assert result.filled_qty == Decimal('0.5')

    def test_limit_ioc_order(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_venue_order(_BINANCE_LIMIT_IOC_ORDER_RESPONSE)
        assert result.order_type == OrderType.LIMIT_IOC
        assert result.status == OrderStatus.EXPIRED
        assert result.filled_qty == Decimal('0.3')
        assert result.price == Decimal('50000.0')


class TestRaiseOnError:

    @pytest.mark.asyncio
    async def test_success_does_not_raise(self) -> None:

        adapter = _make_adapter()
        await adapter._raise_on_error(_mock_response(200))

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(AuthenticationError, match='Authentication failed'):
            await adapter._raise_on_error(_mock_response(401))

    @pytest.mark.asyncio
    async def test_403_raises_rate_limit_error(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(RateLimitError, match='Rate limited'):
            await adapter._raise_on_error(_mock_response(403))

    @pytest.mark.asyncio
    async def test_418_raises_rate_limit_error(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(RateLimitError, match='Rate limited'):
            await adapter._raise_on_error(_mock_response(418))

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(RateLimitError, match='Rate limited'):
            await adapter._raise_on_error(_mock_response(429))

    @pytest.mark.asyncio
    async def test_429_parses_retry_after_header(self) -> None:

        adapter = _make_adapter()
        resp = _mock_response(429, headers={'Retry-After': '45'})
        with pytest.raises(RateLimitError) as exc_info:
            await adapter._raise_on_error(resp)
        assert exc_info.value.retry_after == 45.0

    @pytest.mark.asyncio
    async def test_429_without_retry_after_sets_none(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(RateLimitError) as exc_info:
            await adapter._raise_on_error(_mock_response(429))
        assert exc_info.value.retry_after is None

    @pytest.mark.asyncio
    async def test_429_sets_status_code(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(RateLimitError) as exc_info:
            await adapter._raise_on_error(_mock_response(429))
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_non_finite_retry_after_treated_as_none(self) -> None:

        adapter = _make_adapter()
        for val in ['NaN', 'inf', '-inf']:
            resp = _mock_response(429, headers={'Retry-After': val})
            with pytest.raises(RateLimitError) as exc_info:
                await adapter._raise_on_error(resp)
            assert exc_info.value.retry_after is None, f"Expected None for Retry-After={val!r}"

    @pytest.mark.asyncio
    async def test_negative_retry_after_treated_as_none(self) -> None:

        adapter = _make_adapter()
        resp = _mock_response(429, headers={'Retry-After': '-5'})
        with pytest.raises(RateLimitError) as exc_info:
            await adapter._raise_on_error(resp)
        assert exc_info.value.retry_after is None

    @pytest.mark.asyncio
    async def test_500_raises_transient_error(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(TransientError, match='Venue server error'):
            await adapter._raise_on_error(_mock_response(500))

    @pytest.mark.asyncio
    async def test_400_with_json_raises_order_rejected(self) -> None:

        adapter = _make_adapter()
        response = _mock_response(400, {
            'code': _BINANCE_REJECTION_CODE,
            'msg': _BINANCE_REJECTION_MSG,
        })
        with pytest.raises(OrderRejectedError) as exc_info:
            await adapter._raise_on_error(response)
        assert exc_info.value.venue_code == _BINANCE_REJECTION_CODE
        assert exc_info.value.reason == _BINANCE_REJECTION_MSG

    @pytest.mark.asyncio
    async def test_400_with_bad_json_falls_back(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(OrderRejectedError) as exc_info:
            await adapter._raise_on_error(_mock_response(400))
        assert exc_info.value.venue_code == _FALLBACK_VENUE_CODE

    @pytest.mark.asyncio
    async def test_400_order_not_exist_raises_not_found(self) -> None:

        adapter = _make_adapter()
        response = _mock_response(400, {
            'code': _BINANCE_ORDER_NOT_EXIST_CODE,
            'msg': _BINANCE_ORDER_NOT_EXIST_MSG,
        })
        with pytest.raises(NotFoundError, match='Not found'):
            await adapter._raise_on_error(response)

    @pytest.mark.asyncio
    async def test_400_unknown_order_raises_not_found(self) -> None:

        adapter = _make_adapter()
        response = _mock_response(400, {
            'code': _BINANCE_UNKNOWN_ORDER_CODE,
            'msg': _BINANCE_UNKNOWN_ORDER_MSG,
        })
        with pytest.raises(NotFoundError, match='Not found'):
            await adapter._raise_on_error(response)

class TestSessionLifecycle:

    @pytest.mark.asyncio
    async def test_context_manager_creates_and_closes_session(self) -> None:

        async with BinanceAdapter(_BASE_URL, _WS_BASE_URL) as adapter:
            assert adapter._session is not None
        assert adapter._session is None

    @pytest.mark.asyncio
    async def test_close_cleans_up_session(self) -> None:

        adapter = BinanceAdapter(_BASE_URL, _WS_BASE_URL)
        mock_session = AsyncMock()
        mock_session.closed = False
        adapter._session = mock_session
        await adapter.close()
        assert adapter._session is None
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_session_creates_if_none(self) -> None:

        adapter = BinanceAdapter(_BASE_URL, _WS_BASE_URL)
        session = await adapter._ensure_session()
        assert session is not None
        await session.close()


class TestSubmitOrder:

    @pytest.mark.asyncio
    async def test_market_buy_filled(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_FILLED_RESPONSE))
        result = await adapter.submit_order(
            _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
            Decimal('0.5'),
        )
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.status == OrderStatus.FILLED
        assert len(result.immediate_fills) == 1

    @pytest.mark.asyncio
    async def test_limit_sell_new(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_NEW_RESPONSE))
        result = await adapter.submit_order(
            _ACCOUNT_ID, 'BTCUSDT', OrderSide.SELL, OrderType.LIMIT,
            Decimal('1.0'), price=Decimal('50000'),
        )
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.status == OrderStatus.OPEN
        assert result.immediate_fills == ()

    @pytest.mark.asyncio
    async def test_limit_ioc_expired(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_EXPIRED_RESPONSE))
        result = await adapter.submit_order(
            _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.LIMIT_IOC,
            Decimal('1.0'), price=Decimal('50000'),
        )
        assert result.status == OrderStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_unregistered_account_raises_auth_error(self) -> None:

        adapter = BinanceAdapter(_BASE_URL, _WS_BASE_URL)
        with pytest.raises(AuthenticationError, match='No credentials'):
            await adapter.submit_order(
                'unknown', 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('1.0'),
            )

    @pytest.mark.asyncio
    async def test_network_error_raises_transient(self) -> None:

        adapter = _make_adapter()
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError())
        session.closed = False
        adapter._session = session
        with (
            patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock),
            pytest.raises(TransientError, match='Request failed'),
        ):
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('1.0'),
            )

    @pytest.mark.asyncio
    async def test_http_error_propagates(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(429))
        with pytest.raises(RateLimitError):
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('1.0'),
            )

    @pytest.mark.asyncio
    async def test_domain_errors_not_wrapped_as_transient(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(400, {
            'code': _BINANCE_REJECTION_CODE,
            'msg': _BINANCE_REJECTION_MSG,
        }))
        with pytest.raises(OrderRejectedError):
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('1.0'),
            )


class TestCancelOrder:

    @pytest.mark.asyncio
    async def test_cancel_with_venue_order_id(self) -> None:

        adapter = _make_adapter()
        response_data = {'orderId': 12345, 'status': 'CANCELED'}
        _patch_session(adapter, _mock_response(200, response_data))
        result = await adapter.cancel_order(
            _ACCOUNT_ID, 'BTCUSDT', venue_order_id=_VENUE_ORDER_ID,
        )
        assert isinstance(result, CancelResult)
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.status == OrderStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_with_client_order_id(self) -> None:

        adapter = _make_adapter()
        response_data = {'orderId': 12345, 'status': 'CANCELED'}
        _patch_session(adapter, _mock_response(200, response_data))
        result = await adapter.cancel_order(
            _ACCOUNT_ID, 'BTCUSDT', client_order_id='my-client-id',
        )
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.status == OrderStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_with_both_identifiers(self) -> None:

        adapter = _make_adapter()
        response_data = {'orderId': 12345, 'status': 'CANCELED'}
        _patch_session(adapter, _mock_response(200, response_data))
        result = await adapter.cancel_order(
            _ACCOUNT_ID, 'BTCUSDT',
            venue_order_id=_VENUE_ORDER_ID,
            client_order_id='my-client-id',
        )
        assert result.venue_order_id == _VENUE_ORDER_ID

    @pytest.mark.asyncio
    async def test_cancel_with_neither_identifier_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='At least one'):
            await adapter.cancel_order(_ACCOUNT_ID, 'BTCUSDT')

    @pytest.mark.asyncio
    async def test_cancel_not_found_raises(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(400, {
            'code': _BINANCE_ORDER_NOT_EXIST_CODE,
            'msg': _BINANCE_ORDER_NOT_EXIST_MSG,
        }))
        with pytest.raises(NotFoundError):
            await adapter.cancel_order(
                _ACCOUNT_ID, 'BTCUSDT', venue_order_id=_VENUE_ORDER_ID,
            )


class TestQueryOrder:

    @pytest.mark.asyncio
    async def test_query_limit_order(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_LIMIT_ORDER_RESPONSE))
        result = await adapter.query_order(
            _ACCOUNT_ID, 'BTCUSDT', venue_order_id=_VENUE_ORDER_ID,
        )
        assert isinstance(result, VenueOrder)
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.client_order_id == 'my-client-id'
        assert result.status == OrderStatus.OPEN
        assert result.symbol == 'BTCUSDT'
        assert result.side == OrderSide.BUY
        assert result.order_type == OrderType.LIMIT
        assert result.price == Decimal('50000.0')

    @pytest.mark.asyncio
    async def test_query_market_order_price_none(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_MARKET_ORDER_RESPONSE))
        result = await adapter.query_order(
            _ACCOUNT_ID, 'BTCUSDT', venue_order_id=_VENUE_ORDER_ID,
        )
        assert result.order_type == OrderType.MARKET
        assert result.price is None

    @pytest.mark.asyncio
    async def test_query_limit_ioc_order(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_LIMIT_IOC_ORDER_RESPONSE))
        result = await adapter.query_order(
            _ACCOUNT_ID, 'BTCUSDT', venue_order_id=_VENUE_ORDER_ID,
        )
        assert result.order_type == OrderType.LIMIT_IOC

    @pytest.mark.asyncio
    async def test_query_with_client_order_id(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_LIMIT_ORDER_RESPONSE))
        result = await adapter.query_order(
            _ACCOUNT_ID, 'BTCUSDT', client_order_id='my-client-id',
        )
        assert result.venue_order_id == _VENUE_ORDER_ID

    @pytest.mark.asyncio
    async def test_query_with_neither_identifier_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='At least one'):
            await adapter.query_order(_ACCOUNT_ID, 'BTCUSDT')

    @pytest.mark.asyncio
    async def test_query_not_found_raises(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(400, {
            'code': _BINANCE_ORDER_NOT_EXIST_CODE,
            'msg': _BINANCE_ORDER_NOT_EXIST_MSG,
        }))
        with pytest.raises(NotFoundError):
            await adapter.query_order(
                _ACCOUNT_ID, 'BTCUSDT', venue_order_id=_VENUE_ORDER_ID,
            )


class TestQueryOpenOrders:

    @pytest.mark.asyncio
    async def test_returns_list_of_venue_orders(self) -> None:

        adapter = _make_adapter()
        response_data = [_BINANCE_LIMIT_ORDER_RESPONSE, _BINANCE_MARKET_ORDER_RESPONSE]
        _patch_session(adapter, _mock_response(200, response_data))
        result = await adapter.query_open_orders(_ACCOUNT_ID, 'BTCUSDT')
        assert len(result) == 2
        assert isinstance(result[0], VenueOrder)
        assert result[0].order_type == OrderType.LIMIT
        assert result[1].order_type == OrderType.MARKET

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, []))
        result = await adapter.query_open_orders(_ACCOUNT_ID, 'BTCUSDT')
        assert result == []


class TestQueryBalance:

    _ACCOUNT_RESPONSE: ClassVar[dict[str, Any]] = {
        'balances': [
            {'asset': 'BTC', 'free': '1.50000000', 'locked': '0.25000000'},
            {'asset': 'USDT', 'free': '10000.00', 'locked': '500.00'},
            {'asset': 'ETH', 'free': '0.00000000', 'locked': '0.00000000'},
            {'asset': 'BNB', 'free': '5.00000000', 'locked': '0.00000000'},
        ],
    }

    @pytest.mark.asyncio
    async def test_returns_only_requested_assets(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, self._ACCOUNT_RESPONSE))
        result = await adapter.query_balance(
            _ACCOUNT_ID, frozenset({'BTC', 'USDT'}),
        )
        assert len(result) == 2
        assets = {e.asset for e in result}
        assert assets == {'BTC', 'USDT'}

    @pytest.mark.asyncio
    async def test_balance_values_are_decimal(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, self._ACCOUNT_RESPONSE))
        result = await adapter.query_balance(
            _ACCOUNT_ID, frozenset({'BTC'}),
        )
        assert len(result) == 1
        assert isinstance(result[0], BalanceEntry)
        assert result[0].free == Decimal('1.5')
        assert result[0].locked == Decimal('0.25')

    @pytest.mark.asyncio
    async def test_asset_not_in_response_omitted(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, self._ACCOUNT_RESPONSE))
        result = await adapter.query_balance(
            _ACCOUNT_ID, frozenset({'DOGE'}),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_filters_exclude_unrequested(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, self._ACCOUNT_RESPONSE))
        result = await adapter.query_balance(
            _ACCOUNT_ID, frozenset({'ETH'}),
        )
        assert len(result) == 1
        assert result[0].asset == 'ETH'

    @pytest.mark.asyncio
    async def test_empty_assets_skips_api_call(self) -> None:

        adapter = _make_adapter()
        session = MagicMock()
        session.closed = False
        adapter._session = session
        result = await adapter.query_balance(_ACCOUNT_ID, frozenset())
        assert result == []
        session.request.assert_not_called()


class TestParseVenueTrade:

    def test_field_mapping(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_venue_trade(_BINANCE_TRADE_RESPONSE)
        assert isinstance(result, VenueTrade)
        assert result.venue_trade_id == _VENUE_TRADE_ID
        assert result.venue_order_id == _VENUE_ORDER_ID
        assert result.client_order_id == 'my-client-id'
        assert result.symbol == 'BTCUSDT'
        assert result.side == OrderSide.BUY
        assert result.fee_asset == 'BTC'

    def test_decimal_precision_preserved(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_venue_trade(_BINANCE_TRADE_RESPONSE)
        assert str(result.qty) == '0.50000000'
        assert str(result.price) == '50000.12345678'
        assert str(result.fee) == '0.00050000'

    def test_timestamp_is_utc(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_venue_trade(_BINANCE_TRADE_RESPONSE)
        assert result.timestamp.tzinfo == timezone.utc
        expected = datetime.fromtimestamp(1700000000, tz=timezone.utc)
        assert result.timestamp == expected

    def test_is_maker_true(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_venue_trade(_BINANCE_TRADE_RESPONSE)
        assert result.is_maker is True

    def test_is_maker_false(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_TRADE_RESPONSE)
        data['isMaker'] = False
        result = adapter._parse_venue_trade(data)
        assert result.is_maker is False


class TestQueryTrades:

    @pytest.mark.asyncio
    async def test_returns_list_of_venue_trades(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, [_BINANCE_TRADE_RESPONSE]))
        result = await adapter.query_trades(_ACCOUNT_ID, 'BTCUSDT')
        assert len(result) == 1
        assert isinstance(result[0], VenueTrade)
        assert result[0].venue_trade_id == _VENUE_TRADE_ID

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, []))
        result = await adapter.query_trades(_ACCOUNT_ID, 'BTCUSDT')
        assert result == []

    @pytest.mark.asyncio
    async def test_start_time_converted_to_ms(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, []))
        start = datetime.fromtimestamp(1700000000, tz=timezone.utc)
        await adapter.query_trades(_ACCOUNT_ID, 'BTCUSDT', start_time=start)
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        url = call_args[0][1]
        assert 'startTime=1700000000000' in url

    @pytest.mark.asyncio
    async def test_naive_start_time_raises(self) -> None:

        adapter = _make_adapter()
        naive = datetime(2023, 11, 14, 22, 13, 20)
        with pytest.raises(ValueError, match='timezone-aware'):
            await adapter.query_trades(_ACCOUNT_ID, 'BTCUSDT', start_time=naive)


class TestGetExchangeInfo:

    @pytest.mark.asyncio
    async def test_parses_filters_correctly(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_EXCHANGE_INFO_RESPONSE))
        result = await adapter.get_exchange_info('BTCUSDT')
        assert result.symbol == 'BTCUSDT'
        assert result.tick_size == Decimal('0.01')
        assert result.lot_step == Decimal('0.00001')
        assert result.lot_min == Decimal('0.00001')
        assert result.lot_max == Decimal('9000.0')
        assert result.min_notional == Decimal('5.0')

    @pytest.mark.asyncio
    async def test_missing_filter_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_EXCHANGE_INFO_MISSING_FILTER))
        with pytest.raises(VenueError, match='Missing required filters'):
            await adapter.get_exchange_info('BTCUSDT')

    @pytest.mark.asyncio
    async def test_empty_symbols_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'symbols': []}))
        with pytest.raises(VenueError, match="missing or empty 'symbols'"):
            await adapter.get_exchange_info('BTCUSDT')

    @pytest.mark.asyncio
    async def test_missing_inner_field_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        payload: dict[str, Any] = {
            'symbols': [
                {
                    'symbol': 'BTCUSDT',
                    'filters': [
                        {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'},
                        {'filterType': 'LOT_SIZE'},
                        {'filterType': 'NOTIONAL', 'minNotional': '5.0'},
                    ],
                },
            ],
        }
        _patch_session(adapter, _mock_response(200, payload))
        with pytest.raises(VenueError, match='Malformed exchangeInfo payload'):
            await adapter.get_exchange_info('BTCUSDT')

    @pytest.mark.asyncio
    async def test_parses_rate_limits_from_response(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(
            200, _BINANCE_EXCHANGE_INFO_RESPONSE,
            headers={'X-MBX-USED-WEIGHT-1M': '42'},
        ))
        await adapter.get_exchange_info('BTCUSDT')
        assert adapter._weight_limit == 1200
        assert adapter._order_count_limit == 100
        assert adapter._used_weight == 42

    @pytest.mark.asyncio
    async def test_missing_rate_limits_keeps_defaults(self) -> None:

        adapter = _make_adapter()
        payload: dict[str, Any] = {
            'symbols': [
                {
                    'symbol': 'BTCUSDT',
                    'filters': [
                        {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'},
                        {'filterType': 'LOT_SIZE', 'stepSize': '0.00001', 'minQty': '0.00001', 'maxQty': '9000.0'},
                        {'filterType': 'NOTIONAL', 'minNotional': '5.0'},
                    ],
                },
            ],
        }
        _patch_session(adapter, _mock_response(200, payload))
        await adapter.get_exchange_info('BTCUSDT')
        assert adapter._weight_limit == 6000
        assert adapter._order_count_limit == 10


class TestHeadroom:

    def test_weight_headroom_full(self) -> None:

        adapter = _make_adapter()
        adapter._weight_limit = 1200
        adapter._used_weight = 0
        assert adapter.weight_headroom == 1.0

    def test_weight_headroom_partial(self) -> None:

        adapter = _make_adapter()
        adapter._weight_limit = 1000
        adapter._used_weight = 800
        assert adapter.weight_headroom == pytest.approx(0.2)

    def test_weight_headroom_exhausted(self) -> None:

        adapter = _make_adapter()
        adapter._weight_limit = 1000
        adapter._used_weight = 1000
        assert adapter.weight_headroom == 0.0

    def test_weight_headroom_zero_limit(self) -> None:

        adapter = _make_adapter()
        adapter._weight_limit = 0
        assert adapter.weight_headroom == 1.0

    def test_order_count_headroom_full(self) -> None:

        adapter = _make_adapter()
        adapter._order_count_limit = 100
        assert adapter.order_count_headroom(_ACCOUNT_ID) == 1.0

    def test_order_count_headroom_partial(self) -> None:

        adapter = _make_adapter()
        adapter._order_count_limit = 10
        adapter._order_count[_ACCOUNT_ID] = 8
        assert adapter.order_count_headroom(_ACCOUNT_ID) == pytest.approx(0.2)

    def test_order_count_headroom_per_account(self) -> None:

        adapter = _make_adapter()
        adapter._order_count_limit = 100
        adapter._order_count['acct_a'] = 90
        adapter._order_count['acct_b'] = 10
        assert adapter.order_count_headroom('acct_a') == pytest.approx(0.1)
        assert adapter.order_count_headroom('acct_b') == pytest.approx(0.9)

    def test_order_count_headroom_zero_limit(self) -> None:

        adapter = _make_adapter()
        adapter._order_count_limit = 0
        assert adapter.order_count_headroom(_ACCOUNT_ID) == 1.0

    def test_weight_headroom_clamps_negative_to_zero(self) -> None:

        adapter = _make_adapter()
        adapter._weight_limit = 1000
        adapter._used_weight = 1200
        assert adapter.weight_headroom == 0.0

    def test_order_count_headroom_clamps_negative_to_zero(self) -> None:

        adapter = _make_adapter()
        adapter._order_count_limit = 10
        adapter._order_count[_ACCOUNT_ID] = 15
        assert adapter.order_count_headroom(_ACCOUNT_ID) == 0.0


class TestLoadFilters:

    @pytest.mark.asyncio
    async def test_caches_multiple_symbols(self) -> None:

        adapter = _make_adapter()
        filters_btc = SymbolFilters(
            symbol='BTCUSDT', tick_size=Decimal('0.01'),
            lot_step=Decimal('0.00001'), lot_min=Decimal('0.00001'),
            lot_max=Decimal('9000.0'), min_notional=Decimal('5.0'),
        )
        filters_eth = SymbolFilters(
            symbol='ETHUSDT', tick_size=Decimal('0.1'),
            lot_step=Decimal('0.0001'), lot_min=Decimal('0.001'),
            lot_max=Decimal('10000.0'), min_notional=Decimal('10.0'),
        )
        adapter.get_exchange_info = AsyncMock(side_effect=[filters_btc, filters_eth])  # type: ignore[method-assign]
        await adapter.load_filters(['BTCUSDT', 'ETHUSDT'])
        assert adapter._filters['BTCUSDT'] == filters_btc
        assert adapter._filters['ETHUSDT'] == filters_eth

    @pytest.mark.asyncio
    async def test_bare_string_raises_type_error(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(TypeError, match='not a single string'):
            await adapter.load_filters('BTCUSDT')


class TestValidateOrder:

    def test_valid_limit_order_passes(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        adapter._validate_order('BTCUSDT', OrderType.LIMIT, Decimal('1.0'), Decimal('50000.00'))

    def test_valid_market_order_passes(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        adapter._validate_order('BTCUSDT', OrderType.MARKET, Decimal('1.0'), None)

    def test_price_not_multiple_of_tick_size_raises(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        with pytest.raises(ValueError, match='not a multiple of tick size'):
            adapter._validate_order('BTCUSDT', OrderType.LIMIT, Decimal('1.0'), Decimal('50000.005'))

    def test_qty_not_multiple_of_lot_step_raises(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        with pytest.raises(ValueError, match='not a multiple of lot step'):
            adapter._validate_order('BTCUSDT', OrderType.LIMIT, Decimal('0.000012'), Decimal('50000.00'))

    def test_qty_below_lot_min_raises(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        with pytest.raises(ValueError, match='below lot minimum'):
            adapter._validate_order('BTCUSDT', OrderType.LIMIT, Decimal('0.0001'), Decimal('50000.00'))

    def test_qty_above_lot_max_raises(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        with pytest.raises(ValueError, match='above lot maximum'):
            adapter._validate_order('BTCUSDT', OrderType.LIMIT, Decimal('10000.0'), Decimal('50000.00'))

    def test_below_min_notional_raises(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        with pytest.raises(ValueError, match='below minimum'):
            adapter._validate_order('BTCUSDT', OrderType.LIMIT, Decimal('0.001'), Decimal('100.00'))

    def test_skips_notional_check_for_market_orders(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        adapter._validate_order('BTCUSDT', OrderType.MARKET, Decimal('0.001'), None)

    def test_warns_when_filters_not_cached(self, caplog: pytest.LogCaptureFixture) -> None:

        adapter = _make_adapter()
        with caplog.at_level(logging.WARNING):
            adapter._validate_order('UNKNOWN', OrderType.LIMIT, Decimal('1.0'), Decimal('50000'))
        assert 'No cached filters for UNKNOWN' in caplog.text

    @pytest.mark.asyncio
    async def test_submit_order_validates_before_request(self) -> None:

        adapter = _make_adapter()
        adapter._filters['BTCUSDT'] = _TEST_FILTERS
        _patch_session(adapter, _mock_response(200, _BINANCE_FILLED_RESPONSE))
        with pytest.raises(ValueError, match='not a multiple of tick size'):
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.LIMIT,
                Decimal('1.0'), price=Decimal('50000.005'),
            )
        adapter._session.request.assert_not_called()  # type: ignore[union-attr]


class TestQueryOrderBook:

    @pytest.mark.asyncio
    async def test_parses_bids_and_asks(self) -> None:

        adapter = _make_adapter()
        payload = {
            'lastUpdateId': 1027024,
            'bids': [['50000.00', '1.5'], ['49999.00', '2.0']],
            'asks': [['50001.00', '0.8'], ['50002.00', '1.2']],
        }
        _patch_session(adapter, _mock_response(200, payload))
        result = await adapter.query_order_book('BTCUSDT')
        assert result.last_update_id == 1027024
        assert len(result.bids) == 2
        assert len(result.asks) == 2
        assert result.bids[0].price == Decimal('50000.00')
        assert result.bids[0].qty == Decimal('1.5')
        assert result.bids[1].price == Decimal('49999.00')
        assert result.asks[0].price == Decimal('50001.00')
        assert result.asks[1].qty == Decimal('1.2')

    @pytest.mark.asyncio
    async def test_empty_book(self) -> None:

        adapter = _make_adapter()
        payload = {'lastUpdateId': 100, 'bids': [], 'asks': []}
        _patch_session(adapter, _mock_response(200, payload))
        result = await adapter.query_order_book('BTCUSDT')
        assert result.bids == ()
        assert result.asks == ()
        assert result.last_update_id == 100

    @pytest.mark.asyncio
    async def test_custom_limit_passed_as_param(self) -> None:

        adapter = _make_adapter()
        payload = {'lastUpdateId': 1, 'bids': [], 'asks': []}
        _patch_session(adapter, _mock_response(200, payload))
        await adapter.query_order_book('ETHUSDT', limit=50)
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        url = call_args[0][1]
        params = call_args[1].get('params', {})
        assert 'depth' in url
        assert params.get('limit') == '50'
        assert params.get('symbol') == 'ETHUSDT'

    @pytest.mark.asyncio
    async def test_updates_weight_from_headers(self) -> None:

        adapter = _make_adapter()
        payload = {'lastUpdateId': 1, 'bids': [], 'asks': []}
        _patch_session(adapter, _mock_response(
            200, payload,
            headers={'X-MBX-USED-WEIGHT-1M': '55'},
        ))
        await adapter.query_order_book('BTCUSDT')
        assert adapter._used_weight == 55

    @pytest.mark.asyncio
    async def test_malformed_payload_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'broken': True}))
        with pytest.raises(VenueError, match='Malformed depth payload'):
            await adapter.query_order_book('BTCUSDT')

    @pytest.mark.asyncio
    async def test_malformed_level_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        payload = {
            'lastUpdateId': 1,
            'bids': [['not_a_number', '1.0']],
            'asks': [],
        }
        _patch_session(adapter, _mock_response(200, payload))
        with pytest.raises(VenueError, match='Malformed depth payload'):
            await adapter.query_order_book('BTCUSDT')

    @pytest.mark.asyncio
    async def test_network_error_raises_transient(self) -> None:

        adapter = _make_adapter()
        session = MagicMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError('timeout'))
        ctx.__aexit__ = AsyncMock(return_value=False)
        session.request = MagicMock(return_value=ctx)
        session.closed = False
        adapter._session = session
        with pytest.raises(TransientError, match='Request failed'):
            await adapter.query_order_book('BTCUSDT')

    @pytest.mark.asyncio
    async def test_http_error_propagates(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(500))
        with pytest.raises(TransientError, match='Venue server error'):
            await adapter.query_order_book('BTCUSDT')

    @pytest.mark.asyncio
    async def test_invalid_symbol_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        payload = {'code': -1121, 'msg': 'Invalid symbol.'}
        _patch_session(adapter, _mock_response(400, payload))
        with pytest.raises(VenueError, match='depth query failed'):
            await adapter.query_order_book('INVALID')

    @pytest.mark.asyncio
    async def test_snapshot_is_immutable(self) -> None:

        adapter = _make_adapter()
        payload = {
            'lastUpdateId': 1,
            'bids': [['100.0', '1.0']],
            'asks': [['101.0', '2.0']],
        }
        _patch_session(adapter, _mock_response(200, payload))
        result = await adapter.query_order_book('BTCUSDT')
        with pytest.raises(AttributeError):
            result.last_update_id = 999  # type: ignore[misc]


class TestApiKeyRequest:

    @pytest.mark.asyncio
    async def test_sends_api_key_header_without_signature(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'result': 'ok'}))
        await adapter._api_key_request('POST', '/api/v3/userDataStream', {}, _ACCOUNT_ID)
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        method = call_args[0][0]
        url = call_args[0][1]
        headers = call_args.kwargs['headers']
        assert method == 'POST'
        assert url == f"{_BASE_URL}/api/v3/userDataStream"
        assert headers['X-MBX-APIKEY'] == _API_KEY
        assert 'signature' not in url

    @pytest.mark.asyncio
    async def test_passes_query_params(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {}))
        await adapter._api_key_request(
            'PUT', '/api/v3/userDataStream',
            {'listenKey': 'abc123'}, _ACCOUNT_ID,
        )
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        params = call_args.kwargs['params']
        assert params == {'listenKey': 'abc123'}

    @pytest.mark.asyncio
    async def test_transport_error_retried_and_raises_transient(self) -> None:

        adapter = _make_adapter()
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError())
        session.closed = False
        adapter._session = session
        with (
            patch('praxis.infrastructure.binance_adapter.asyncio.sleep', new_callable=AsyncMock),
            pytest.raises(TransientError, match='Request failed'),
        ):
            await adapter._api_key_request('POST', '/api/v3/userDataStream', {}, _ACCOUNT_ID)


class TestCreateListenKey:

    @pytest.mark.asyncio
    async def test_returns_listen_key_string(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'listenKey': 'abc123'}))
        result = await adapter._create_listen_key(_ACCOUNT_ID)
        assert result == 'abc123'

    @pytest.mark.asyncio
    async def test_missing_listen_key_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {}))
        with pytest.raises(VenueError, match='Missing listenKey'):
            await adapter._create_listen_key(_ACCOUNT_ID)

    @pytest.mark.asyncio
    async def test_empty_listen_key_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {'listenKey': ''}))
        with pytest.raises(VenueError, match='Missing listenKey'):
            await adapter._create_listen_key(_ACCOUNT_ID)

    @pytest.mark.asyncio
    async def test_non_dict_response_raises_venue_error(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, 'not-a-dict'))
        with pytest.raises(VenueError, match='Missing listenKey'):
            await adapter._create_listen_key(_ACCOUNT_ID)


class TestKeepaliveListenKey:

    @pytest.mark.asyncio
    async def test_sends_put_with_listen_key(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {}))
        await adapter._keepalive_listen_key(_ACCOUNT_ID, 'abc123')
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        method = call_args[0][0]
        params = call_args.kwargs['params']
        assert method == 'PUT'
        assert params == {'listenKey': 'abc123'}


class TestCloseListenKey:

    @pytest.mark.asyncio
    async def test_sends_delete_with_listen_key(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, {}))
        await adapter._close_listen_key(_ACCOUNT_ID, 'abc123')
        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        method = call_args[0][0]
        params = call_args.kwargs['params']
        assert method == 'DELETE'
        assert params == {'listenKey': 'abc123'}


_BINANCE_EXECUTION_REPORT_TRADE: dict[str, Any] = {
    'e': 'executionReport',
    'E': 1700000000000,
    's': 'BTCUSDT',
    'c': 'my-client-id',
    'S': 'BUY',
    'o': 'LIMIT',
    'f': 'GTC',
    'q': '1.00000000',
    'p': '50000.00000000',
    'x': 'TRADE',
    'X': 'PARTIALLY_FILLED',
    'r': 'NONE',
    'i': 12345,
    'l': '0.50000000',
    'L': '50000.00000000',
    'z': '0.50000000',
    'n': '0.00050000',
    'N': 'BTC',
    'T': 1700000001000,
    't': 99,
    'm': True,
}


class TestParseExecutionReport:

    def test_trade_fill(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_execution_report(_BINANCE_EXECUTION_REPORT_TRADE)
        assert isinstance(result, ExecutionReport)
        assert result.symbol == 'BTCUSDT'
        assert result.client_order_id == 'my-client-id'
        assert result.side == OrderSide.BUY
        assert result.order_type == OrderType.LIMIT
        assert result.original_qty == Decimal('1.00000000')
        assert result.original_price == Decimal('50000.00000000')
        assert result.execution_type == ExecutionType.TRADE
        assert result.order_status == OrderStatus.PARTIALLY_FILLED
        assert result.reject_reason == 'NONE'
        assert result.venue_order_id == '12345'
        assert result.last_filled_qty == Decimal('0.50000000')
        assert result.last_filled_price == Decimal('50000.00000000')
        assert result.cumulative_filled_qty == Decimal('0.50000000')
        assert result.commission == Decimal('0.00050000')
        assert result.commission_asset == 'BTC'
        assert result.venue_trade_id == '99'
        assert result.is_maker is True

    def test_event_time_is_utc(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_execution_report(_BINANCE_EXECUTION_REPORT_TRADE)
        assert result.event_time.tzinfo == timezone.utc
        expected = datetime.fromtimestamp(1700000000, tz=timezone.utc)
        assert result.event_time == expected

    def test_transaction_time_is_utc(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_execution_report(_BINANCE_EXECUTION_REPORT_TRADE)
        assert result.transaction_time.tzinfo == timezone.utc
        expected = datetime.fromtimestamp(1700000001, tz=timezone.utc)
        assert result.transaction_time == expected

    def test_new_order_no_fill(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['x'] = 'NEW'
        data['X'] = 'NEW'
        data['l'] = '0.00000000'
        data['L'] = '0.00000000'
        data['z'] = '0.00000000'
        data['n'] = '0.00000000'
        data['N'] = None
        data['t'] = -1
        data['m'] = False
        result = adapter._parse_execution_report(data)
        assert result.execution_type == ExecutionType.NEW
        assert result.order_status == OrderStatus.OPEN
        assert result.last_filled_qty == Decimal('0')
        assert result.last_filled_price == Decimal('0')
        assert result.cumulative_filled_qty == Decimal('0')
        assert result.commission_asset is None
        assert result.venue_trade_id is None
        assert result.is_maker is False

    def test_canceled_order(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['x'] = 'CANCELED'
        data['X'] = 'CANCELED'
        result = adapter._parse_execution_report(data)
        assert result.execution_type == ExecutionType.CANCELED
        assert result.order_status == OrderStatus.CANCELED

    def test_replaced_order(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['x'] = 'REPLACED'
        data['X'] = 'CANCELED'
        result = adapter._parse_execution_report(data)
        assert result.execution_type == ExecutionType.REPLACED
        assert result.order_status == OrderStatus.CANCELED

    def test_rejected_order(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['x'] = 'REJECTED'
        data['X'] = 'REJECTED'
        data['r'] = 'INSUFFICIENT_BALANCE'
        result = adapter._parse_execution_report(data)
        assert result.execution_type == ExecutionType.REJECTED
        assert result.order_status == OrderStatus.REJECTED
        assert result.reject_reason == 'INSUFFICIENT_BALANCE'

    def test_expired_ioc(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['x'] = 'EXPIRED'
        data['X'] = 'EXPIRED'
        data['o'] = 'LIMIT'
        data['f'] = 'IOC'
        result = adapter._parse_execution_report(data)
        assert result.execution_type == ExecutionType.EXPIRED
        assert result.order_status == OrderStatus.EXPIRED
        assert result.order_type == OrderType.LIMIT_IOC

    def test_trade_prevention(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['x'] = 'TRADE_PREVENTION'
        data['X'] = 'EXPIRED'
        result = adapter._parse_execution_report(data)
        assert result.execution_type == ExecutionType.TRADE_PREVENTION
        assert result.order_status == OrderStatus.EXPIRED

    def test_market_order(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['o'] = 'MARKET'
        data['f'] = ''
        data['p'] = '0.00000000'
        result = adapter._parse_execution_report(data)
        assert result.order_type == OrderType.MARKET
        assert result.original_price == Decimal('0')

    def test_unknown_execution_type_raises(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['x'] = 'UNKNOWN_TYPE'
        with pytest.raises(ValueError, match='Unknown Binance execution type'):
            adapter._parse_execution_report(data)

    def test_unknown_order_status_raises(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['X'] = 'UNKNOWN_STATUS'
        with pytest.raises(ValueError, match='Unknown Binance order status'):
            adapter._parse_execution_report(data)

    def test_unknown_order_type_raises(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['o'] = 'UNKNOWN_ORDER_TYPE'
        with pytest.raises(ValueError, match='Unknown Binance order type'):
            adapter._parse_execution_report(data)

    def test_is_maker_false(self) -> None:

        adapter = _make_adapter()
        data = dict(_BINANCE_EXECUTION_REPORT_TRADE)
        data['m'] = False
        result = adapter._parse_execution_report(data)
        assert result.is_maker is False

    def test_decimal_precision_preserved(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_execution_report(_BINANCE_EXECUTION_REPORT_TRADE)
        assert str(result.original_qty) == '1.00000000'
        assert str(result.original_price) == '50000.00000000'
        assert str(result.last_filled_qty) == '0.50000000'
        assert str(result.last_filled_price) == '50000.00000000'
        assert str(result.commission) == '0.00050000'


class TestBuildOcoParams:

    def test_required_params(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_oco_params(
            'BTCUSDT', OrderSide.SELL, Decimal('0.01'),
            price=Decimal('50000'), stop_price=Decimal('48000'),
        )
        assert params['symbol'] == 'BTCUSDT'
        assert params['side'] == 'SELL'
        assert params['quantity'] == '0.01'
        assert params['price'] == '50000'
        assert params['stopPrice'] == '48000'
        assert params['newOrderRespType'] == 'FULL'
        assert 'stopLimitPrice' not in params
        assert 'stopLimitTimeInForce' not in params

    def test_stop_limit_price_included(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_oco_params(
            'BTCUSDT', OrderSide.SELL, Decimal('0.01'),
            price=Decimal('50000'), stop_price=Decimal('48000'),
            stop_limit_price=Decimal('47500'),
        )
        assert params['stopLimitPrice'] == '47500'
        assert params['stopLimitTimeInForce'] == 'GTC'

    def test_time_in_force_passed_through(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_oco_params(
            'BTCUSDT', OrderSide.SELL, Decimal('0.01'),
            price=Decimal('50000'), stop_price=Decimal('48000'),
            stop_limit_price=Decimal('47500'),
            time_in_force='IOC',
        )
        assert params['stopLimitTimeInForce'] == 'IOC'

    def test_client_order_id_as_list_client_order_id(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_oco_params(
            'BTCUSDT', OrderSide.BUY, Decimal('1'),
            price=Decimal('50000'), stop_price=Decimal('48000'),
            client_order_id='ss-cmd1-0',
        )
        assert params['listClientOrderId'] == 'ss-cmd1-0'


class TestParseOcoResponse:

    def test_executing_maps_to_open(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_oco_response(_BINANCE_OCO_RESPONSE)
        assert result.venue_order_id == '99999'
        assert result.status == OrderStatus.OPEN
        assert result.immediate_fills == ()

    def test_all_done_with_fills(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_oco_response(_BINANCE_OCO_RESPONSE_WITH_FILLS)
        assert result.venue_order_id == '99999'
        assert result.status == OrderStatus.FILLED
        assert len(result.immediate_fills) == 1
        fill = result.immediate_fills[0]
        assert fill.venue_trade_id == '201'
        assert fill.qty == Decimal('0.01')
        assert fill.price == Decimal('50000.00')
        assert fill.fee == Decimal('0.00001')
        assert fill.fee_asset == 'BTC'

    def test_all_done_canceled_no_fills(self) -> None:

        adapter = _make_adapter()
        canceled_response: dict[str, Any] = {
            'orderListId': 99999,
            'contingencyType': 'OCO',
            'listStatusType': 'ALL_DONE',
            'listOrderStatus': 'ALL_DONE',
            'listClientOrderId': 'oco-list-3',
            'transactionTime': 1700000000000,
            'symbol': 'BTCUSDT',
            'orders': [],
            'orderReports': [
                {'status': 'CANCELED', 'fills': []},
                {'status': 'CANCELED', 'fills': []},
            ],
        }
        result = adapter._parse_oco_response(canceled_response)
        assert result.status == OrderStatus.CANCELED
        assert result.immediate_fills == ()

    def test_all_done_partially_filled(self) -> None:

        adapter = _make_adapter()
        partial_response: dict[str, Any] = {
            'orderListId': 99999,
            'contingencyType': 'OCO',
            'listStatusType': 'ALL_DONE',
            'listOrderStatus': 'ALL_DONE',
            'listClientOrderId': 'oco-list-4',
            'transactionTime': 1700000000000,
            'symbol': 'BTCUSDT',
            'orders': [],
            'orderReports': [
                {'status': 'PARTIALLY_FILLED', 'fills': [
                    {
                        'tradeId': 301,
                        'qty': '0.005',
                        'price': '49000.00',
                        'commission': '0.000005',
                        'commissionAsset': 'BTC',
                    },
                ]},
                {'status': 'CANCELED', 'fills': []},
            ],
        }
        result = adapter._parse_oco_response(partial_response)
        assert result.status == OrderStatus.PARTIALLY_FILLED
        assert len(result.immediate_fills) == 1

    def test_all_done_expired_legs(self) -> None:

        adapter = _make_adapter()
        expired_response: dict[str, Any] = {
            'orderListId': 99999,
            'contingencyType': 'OCO',
            'listStatusType': 'ALL_DONE',
            'listOrderStatus': 'ALL_DONE',
            'listClientOrderId': 'oco-list-5',
            'transactionTime': 1700000000000,
            'symbol': 'BTCUSDT',
            'orders': [],
            'orderReports': [
                {'status': 'EXPIRED', 'fills': []},
                {'status': 'CANCELED', 'fills': []},
            ],
        }
        result = adapter._parse_oco_response(expired_response)
        assert result.status == OrderStatus.EXPIRED
        assert result.immediate_fills == ()

    def test_is_maker_read_from_payload(self) -> None:

        adapter = _make_adapter()
        response_with_maker: dict[str, Any] = {
            **_BINANCE_OCO_RESPONSE_WITH_FILLS,
            'orderReports': [
                {
                    **_BINANCE_OCO_RESPONSE_WITH_FILLS['orderReports'][0],
                    'fills': [
                        {
                            'tradeId': 201,
                            'qty': '0.01',
                            'price': '50000.00',
                            'commission': '0.00001',
                            'commissionAsset': 'BTC',
                            'isMaker': True,
                        },
                    ],
                },
                _BINANCE_OCO_RESPONSE_WITH_FILLS['orderReports'][1],
            ],
        }
        result = adapter._parse_oco_response(response_with_maker)
        assert result.immediate_fills[0].is_maker is True

    def test_unknown_list_status_raises(self) -> None:

        adapter = _make_adapter()
        bad = {**_BINANCE_OCO_RESPONSE, 'listOrderStatus': 'UNKNOWN'}
        with pytest.raises(ValueError, match='Unknown Binance OCO list status'):
            adapter._parse_oco_response(bad)


class TestSubmitOcoOrder:

    @pytest.mark.asyncio
    async def test_oco_dispatches_to_oco_endpoint(self) -> None:

        adapter = _make_adapter()
        _patch_session(adapter, _mock_response(200, _BINANCE_OCO_RESPONSE))
        result = await adapter.submit_order(
            _ACCOUNT_ID, 'BTCUSDT', OrderSide.SELL, OrderType.OCO,
            Decimal('0.01'),
            price=Decimal('50000'), stop_price=Decimal('48000'),
            stop_limit_price=Decimal('47500'),
        )
        assert result.venue_order_id == '99999'
        assert result.status == OrderStatus.OPEN

        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        assert '/api/v3/order/oco?' in call_args.args[1]

    @pytest.mark.asyncio
    async def test_oco_missing_price_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='price and stop_price are required'):
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.SELL, OrderType.OCO,
                Decimal('0.01'), stop_price=Decimal('48000'),
            )

    @pytest.mark.asyncio
    async def test_oco_missing_stop_price_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='price and stop_price are required'):
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.SELL, OrderType.OCO,
                Decimal('0.01'), price=Decimal('50000'),
            )

    @pytest.mark.asyncio
    async def test_stop_limit_price_rejected_for_non_oco(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='stop_limit_price is only supported for OCO'):
            await adapter.submit_order(
                _ACCOUNT_ID, 'BTCUSDT', OrderSide.BUY, OrderType.LIMIT,
                Decimal('0.01'), price=Decimal('50000'),
                stop_limit_price=Decimal('49000'),
            )


class TestCancelOrderList:

    @pytest.mark.asyncio
    async def test_cancel_with_list_client_order_id(self) -> None:

        adapter = _make_adapter()
        cancel_response: dict[str, Any] = {
            'orderListId': 99999,
            'contingencyType': 'OCO',
            'listStatusType': 'ALL_DONE',
            'listOrderStatus': 'ALL_DONE',
            'listClientOrderId': 'oco-list-1',
            'transactionTime': 1700000000000,
            'symbol': 'BTCUSDT',
            'orders': [],
            'orderReports': [],
        }
        _patch_session(adapter, _mock_response(200, cancel_response))
        result = await adapter.cancel_order_list(
            _ACCOUNT_ID, 'BTCUSDT',
            client_order_id='oco-list-1',
        )
        assert result.venue_order_id == '99999'
        assert result.status == OrderStatus.CANCELED

        call_args = adapter._session.request.call_args  # type: ignore[union-attr]
        assert '/api/v3/orderList?' in call_args.args[1]

    @pytest.mark.asyncio
    async def test_cancel_with_order_list_id(self) -> None:

        adapter = _make_adapter()
        cancel_response: dict[str, Any] = {
            'orderListId': 99999,
            'contingencyType': 'OCO',
            'listStatusType': 'ALL_DONE',
            'listOrderStatus': 'ALL_DONE',
            'listClientOrderId': 'oco-list-1',
            'transactionTime': 1700000000000,
            'symbol': 'BTCUSDT',
            'orders': [],
            'orderReports': [],
        }
        _patch_session(adapter, _mock_response(200, cancel_response))
        result = await adapter.cancel_order_list(
            _ACCOUNT_ID, 'BTCUSDT',
            venue_order_id='99999',
        )
        assert result.venue_order_id == '99999'
        assert result.status == OrderStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_with_neither_raises(self) -> None:

        adapter = _make_adapter()
        with pytest.raises(ValueError, match='At least one of'):
            await adapter.cancel_order_list(_ACCOUNT_ID, 'BTCUSDT')
