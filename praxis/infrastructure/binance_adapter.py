'''
Binance Spot REST adapter for order submission via the VenueAdapter protocol.

Handle authentication, request signing, order submission, and response
normalization for the Binance Spot API. All Binance-specific logic is
encapsulated here.
'''

from __future__ import annotations

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import aiohttp

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.infrastructure.venue_adapter import (
    AuthenticationError,
    ImmediateFill,
    OrderRejectedError,
    RateLimitError,
    SubmitResult,
    TransientError,
)

__all__ = ['BinanceAdapter']

_API_KEY_HEADER = 'X-MBX-APIKEY'
_SESSION_TIMEOUT = aiohttp.ClientTimeout(total=30)
_HTTP_BAD_REQUEST = 400
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_TEAPOT = 418
_HTTP_TOO_MANY = 429
_HTTP_SERVER_ERROR = 500

_BINANCE_STATUS_MAP: dict[str, OrderStatus] = {
    'NEW': OrderStatus.OPEN,
    'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
    'FILLED': OrderStatus.FILLED,
    'CANCELED': OrderStatus.CANCELED,
    'REJECTED': OrderStatus.REJECTED,
    'EXPIRED': OrderStatus.EXPIRED,
    'EXPIRED_IN_MATCH': OrderStatus.EXPIRED,
}

class BinanceAdapter:

    '''
    Binance Spot REST adapter implementing submit_order from VenueAdapter.

    Args:
        base_url (str): Binance REST API base URL (testnet or mainnet)
        credentials (dict[str, tuple[str, str]]): Mapping of account_id
            to (api_key, api_secret) pairs
    '''

    def __init__(
        self,
        base_url: str,
        credentials: dict[str, tuple[str, str]] | None = None,
    ) -> None:

        '''
        Store configuration and initialise empty session.

        Args:
            base_url (str): Binance REST API base URL
            credentials (dict[str, tuple[str, str]] | None): Initial
                account credentials, defaults to empty
        '''

        self._base_url = base_url.rstrip('/')
        self._credentials: dict[str, tuple[str, str]] = dict(credentials or {})
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> BinanceAdapter:

        '''
        Create the HTTP session on context manager entry.

        Returns:
            BinanceAdapter: Self for use in async with block
        '''

        self._session = aiohttp.ClientSession(timeout=_SESSION_TIMEOUT)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:

        '''Close the HTTP session on context manager exit.'''

        await self.close()

    async def close(self) -> None:

        '''Close the HTTP session if it exists.'''

        if self._session:
            session = self._session
            self._session = None
            if not session.closed:
                await session.close()

    def register_account(
        self,
        account_id: str,
        api_key: str,
        api_secret: str,
    ) -> None:

        '''
        Register credentials for an account.

        Args:
            account_id (str): Account identifier
            api_key (str): Binance API key
            api_secret (str): Binance API secret
        '''

        self._credentials[account_id] = (api_key, api_secret)

    def unregister_account(self, account_id: str) -> None:

        '''
        Remove credentials for an account.

        Args:
            account_id (str): Account identifier

        Raises:
            KeyError: If account_id is not registered
        '''

        del self._credentials[account_id]

    def _get_credentials(self, account_id: str) -> tuple[str, str]:

        '''
        Look up credentials for an account.

        Args:
            account_id (str): Account identifier

        Returns:
            tuple[str, str]: (api_key, api_secret) pair

        Raises:
            AuthenticationError: If account_id is not registered
        '''

        try:
            return self._credentials[account_id]
        except KeyError:
            msg = f"No credentials registered for account '{account_id}'"
            raise AuthenticationError(msg) from None

    async def _ensure_session(self) -> aiohttp.ClientSession:

        '''
        Return existing session or create a new one lazily.

        Returns:
            aiohttp.ClientSession: Active HTTP session
        '''

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_SESSION_TIMEOUT)
        return self._session

    def _sign_params(
        self,
        params: dict[str, str],
        api_secret: str,
    ) -> dict[str, str]:

        '''
        Compute signed query parameters for an authenticated request.

        Args:
            params (dict[str, str]): Request parameters to sign
            api_secret (str): API secret used as HMAC key

        Returns:
            dict[str, str]: Parameters with timestamp and signature appended
        '''

        signed = dict(params)
        signed['timestamp'] = str(int(time.time() * 1000))
        query = urlencode(signed)
        signed['signature'] = hmac.new(
            api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signed

    def _auth_headers(self, account_id: str) -> dict[str, str]:

        '''
        Compute HTTP headers for an authenticated request.

        Args:
            account_id (str): Account identifier for credential lookup

        Returns:
            dict[str, str]: Headers with API key set
        '''

        api_key, _ = self._get_credentials(account_id)
        return {_API_KEY_HEADER: api_key}

    def _build_order_params(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: Decimal,
        *,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
        time_in_force: str | None = None,
    ) -> dict[str, str]:

        '''
        Build Binance-formatted order parameters from domain types.

        Args:
            symbol (str): Trading pair symbol
            side (OrderSide): Order direction
            order_type (OrderType): Order type
            qty (Decimal): Order quantity
            price (Decimal | None): Limit price
            stop_price (Decimal | None): Stop trigger price
            client_order_id (str | None): Client order identifier
            time_in_force (str | None): Time-in-force policy

        Returns:
            dict[str, str]: Binance API query parameters
        '''

        params: dict[str, str] = {
            'symbol': symbol,
            'side': side.value,
            'quantity': str(qty),
            'newOrderRespType': 'FULL',
        }

        if order_type == OrderType.MARKET:
            params['type'] = 'MARKET'

        elif order_type == OrderType.LIMIT:
            params['type'] = 'LIMIT'
            if price is None:
                msg = 'price is required for LIMIT orders'
                raise ValueError(msg)
            params['price'] = str(price)
            params['timeInForce'] = time_in_force or 'GTC'

        elif order_type == OrderType.LIMIT_IOC:
            params['type'] = 'LIMIT'
            if price is None:
                msg = 'price is required for LIMIT_IOC orders'
                raise ValueError(msg)
            params['price'] = str(price)
            params['timeInForce'] = 'IOC'

        else:
            msg = f"Unsupported order type: {order_type}"
            raise ValueError(msg)

        if stop_price is not None:
            msg = 'stop_price is not supported for MARKET, LIMIT, or LIMIT_IOC orders'
            raise ValueError(msg)

        if client_order_id is not None:
            params['newClientOrderId'] = client_order_id

        return params

    def _map_order_status(self, binance_status: str) -> OrderStatus:

        '''
        Map a Binance order status string to an OrderStatus enum.

        Args:
            binance_status (str): Binance status value

        Returns:
            OrderStatus: Corresponding domain status
        '''

        try:
            return _BINANCE_STATUS_MAP[binance_status]
        except KeyError:
            msg = f"Unknown Binance order status: '{binance_status}'"
            raise ValueError(msg) from None

    def _parse_submit_response(self, data: dict[str, Any]) -> SubmitResult:

        '''
        Parse a Binance FULL order response into a SubmitResult.

        Args:
            data (dict[str, Any]): Binance JSON response body

        Returns:
            SubmitResult: Normalised submission result
        '''

        fills = tuple(
            ImmediateFill(
                venue_trade_id=str(f['tradeId']),
                qty=Decimal(f['qty']),
                price=Decimal(f['price']),
                fee=Decimal(f['commission']),
                fee_asset=f['commissionAsset'],
                is_maker=False,
            )
            for f in data.get('fills', [])
        )
        return SubmitResult(
            venue_order_id=str(data['orderId']),
            status=self._map_order_status(data['status']),
            immediate_fills=fills,
        )

    async def _raise_on_error(self, response: aiohttp.ClientResponse) -> None:

        '''
        Raise a VenueError subclass if the HTTP response indicates failure.

        Args:
            response (aiohttp.ClientResponse): HTTP response to inspect
        '''

        if response.status < _HTTP_BAD_REQUEST:
            return

        if response.status == _HTTP_UNAUTHORIZED:
            msg = f"Authentication failed: HTTP {response.status}"
            raise AuthenticationError(msg)

        if response.status in (_HTTP_FORBIDDEN, _HTTP_TEAPOT, _HTTP_TOO_MANY):
            msg = f"Rate limited: HTTP {response.status}"
            raise RateLimitError(msg)

        if response.status >= _HTTP_SERVER_ERROR:
            msg = f"Venue server error: HTTP {response.status}"
            raise TransientError(msg)

        try:
            body = await response.json(content_type=None)
            venue_code = int(body['code'])
            reason = str(body['msg'])
        except (ValueError, KeyError, TypeError):
            venue_code = -1
            reason = f"HTTP {response.status}"

        msg = f"Order rejected: {reason} (code {venue_code})"
        raise OrderRejectedError(msg, venue_code=venue_code, reason=reason)

    async def submit_order(
        self,
        account_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: Decimal,
        *,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
        time_in_force: str | None = None,
    ) -> SubmitResult:

        '''
        Submit an order to the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            side (OrderSide): Order direction
            order_type (OrderType): Order type
            qty (Decimal): Order quantity
            price (Decimal | None): Limit price, required for limit orders
            stop_price (Decimal | None): Stop trigger price
            client_order_id (str | None): Deterministic client order identifier
            time_in_force (str | None): Time-in-force policy

        Returns:
            SubmitResult: Venue response with order ID, status, and immediate fills
        '''

        session = await self._ensure_session()
        _, api_secret = self._get_credentials(account_id)
        params = self._build_order_params(
            symbol, side, order_type, qty,
            price=price, stop_price=stop_price,
            client_order_id=client_order_id,
            time_in_force=time_in_force,
        )
        signed = self._sign_params(params, api_secret)
        headers = self._auth_headers(account_id)

        try:
            async with session.post(
                f"{self._base_url}/api/v3/order",
                params=signed,
                headers=headers,
            ) as response:
                await self._raise_on_error(response)
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            msg = f"Request failed: {exc}"
            raise TransientError(msg) from exc

        return self._parse_submit_response(data)
