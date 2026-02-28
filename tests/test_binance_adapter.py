'''
Tests for praxis.infrastructure.binance_adapter.
'''

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.venue_adapter import (
    AuthenticationError,
    OrderRejectedError,
    RateLimitError,
    TransientError,
)


_BASE_URL = 'https://testnet.binance.vision'
_ACCOUNT_ID = 'test-account'
_API_KEY = 'test-api-key'
_API_SECRET = 'test-api-secret'  # noqa: S105
_VENUE_ORDER_ID = '12345'
_VENUE_TRADE_ID = '99'
_BINANCE_REJECTION_CODE = -1013
_BINANCE_REJECTION_MSG = 'Filter failure: MIN_NOTIONAL'
_SHA256_HEX_LENGTH = 64
_FALLBACK_VENUE_CODE = -1

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
    return BinanceAdapter(_BASE_URL, creds)


def _mock_response(
    status: int,
    data: dict[str, Any] | None = None,
) -> AsyncMock:

    '''
    Create a mock aiohttp response.

    Args:
        status (int): HTTP status code
        data (dict[str, Any] | None): JSON response body

    Returns:
        AsyncMock: Mock response with status and json()
    '''

    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data or {})
    return resp


def _patch_session(adapter: BinanceAdapter, response: AsyncMock) -> None:

    '''
    Inject a mock session into the adapter.

    Args:
        adapter (BinanceAdapter): Adapter to patch
        response (AsyncMock): Mock response for session.post()
    '''

    session = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.post = MagicMock(return_value=ctx)
    session.closed = False
    adapter._session = session


class TestCredentialManagement:

    def test_register_account(self) -> None:

        adapter = BinanceAdapter(_BASE_URL)
        adapter.register_account('acc1', 'key1', 'secret1')
        assert adapter._get_credentials('acc1') == ('key1', 'secret1')

    def test_unregister_account(self) -> None:

        adapter = _make_adapter()
        adapter.unregister_account(_ACCOUNT_ID)
        with pytest.raises(AuthenticationError):
            adapter._get_credentials(_ACCOUNT_ID)

    def test_unregister_unknown_raises_key_error(self) -> None:

        adapter = BinanceAdapter(_BASE_URL)
        with pytest.raises(KeyError):
            adapter.unregister_account('nonexistent')

    def test_get_credentials_unknown_raises_auth_error(self) -> None:

        adapter = BinanceAdapter(_BASE_URL)
        with pytest.raises(AuthenticationError, match='No credentials'):
            adapter._get_credentials('unknown')


class TestSigningAndAuth:

    def test_sign_params_adds_timestamp_and_signature(self) -> None:

        adapter = _make_adapter()
        params = adapter._sign_params({'symbol': 'BTCUSDT'}, _API_SECRET)
        assert 'timestamp' in params
        assert 'signature' in params
        assert len(params['signature']) == _SHA256_HEX_LENGTH

    def test_sign_params_preserves_original_params(self) -> None:

        adapter = _make_adapter()
        params = adapter._sign_params(
            {'symbol': 'BTCUSDT', 'side': 'BUY'}, _API_SECRET,
        )
        assert params['symbol'] == 'BTCUSDT'
        assert params['side'] == 'BUY'

    def test_auth_headers_contains_api_key(self) -> None:

        adapter = _make_adapter()
        headers = adapter._auth_headers(_ACCOUNT_ID)
        assert headers == {'X-MBX-APIKEY': _API_KEY}


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

    def test_stop_price_included(self) -> None:

        adapter = _make_adapter()
        params = adapter._build_order_params(
            'BTCUSDT', OrderSide.BUY, OrderType.MARKET, Decimal('1.0'),
            stop_price=Decimal('49000'),
        )
        assert params['stopPrice'] == '49000'

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
        assert result.immediate_fills == []

    def test_expired_no_fills(self) -> None:

        adapter = _make_adapter()
        result = adapter._parse_submit_response(_BINANCE_EXPIRED_RESPONSE)
        assert result.status == OrderStatus.EXPIRED
        assert result.immediate_fills == []


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


class TestSessionLifecycle:

    @pytest.mark.asyncio
    async def test_context_manager_creates_and_closes_session(self) -> None:

        async with BinanceAdapter(_BASE_URL) as adapter:
            assert adapter._session is not None
        assert adapter._session is None

    @pytest.mark.asyncio
    async def test_close_cleans_up_session(self) -> None:

        adapter = BinanceAdapter(_BASE_URL)
        mock_session = AsyncMock()
        mock_session.closed = False
        adapter._session = mock_session
        await adapter.close()
        assert adapter._session is None
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_session_creates_if_none(self) -> None:

        adapter = BinanceAdapter(_BASE_URL)
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
        assert result.immediate_fills == []

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

        adapter = BinanceAdapter(_BASE_URL)
        with pytest.raises(AuthenticationError, match='No credentials'):
            await adapter.submit_order(
                'unknown', 'BTCUSDT', OrderSide.BUY, OrderType.MARKET,
                Decimal('1.0'),
            )

    @pytest.mark.asyncio
    async def test_network_error_raises_transient(self) -> None:

        adapter = _make_adapter()
        session = MagicMock()
        session.post = MagicMock(side_effect=aiohttp.ClientError())
        session.closed = False
        adapter._session = session
        with pytest.raises(TransientError, match='Request failed'):
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
