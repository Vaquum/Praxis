'''
Binance Spot REST adapter for order submission via the VenueAdapter protocol.

Handle authentication, request signing, order submission, and response
normalization for the Binance Spot API. All Binance-specific logic is
encapsulated here.
'''

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import random
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import aiohttp

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.infrastructure.venue_adapter import (
    AuthenticationError,
    BalanceEntry,
    CancelResult,
    ImmediateFill,
    NotFoundError,
    OrderRejectedError,
    RateLimitError,
    SubmitResult,
    TransientError,
    VenueError,
    VenueOrder,
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
_UNKNOWN_VENUE_CODE = -1
_MS_PER_SECOND = 1000
_NOT_FOUND_CODES = frozenset({-2013, -2011})
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.5

_log = logging.getLogger(__name__)

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
        credentials (dict[str, tuple[str, str]] | None): Mapping of account_id
            to (api_key, api_secret) pairs, defaults to empty
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

        await self._ensure_session()
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
    ) -> str:

        '''
        Build a signed query string for an authenticated request.

        Computes the full URL-encoded query string including timestamp and
        HMAC-SHA256 signature. The caller must embed this directly in the
        request URL to avoid re-encoding by the HTTP client.

        Args:
            params (dict[str, str]): Request parameters to sign
            api_secret (str): API secret used as HMAC key

        Returns:
            str: URL-encoded query string with timestamp and signature appended
        '''

        signed = dict(params)
        signed['timestamp'] = str(int(time.time() * _MS_PER_SECOND))
        query = urlencode(signed)
        signature = hmac.new(
            api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f'{query}&signature={signature}'

    async def _signed_request(
        self,
        method: str,
        path: str,
        params: dict[str, str],
        account_id: str,
    ) -> Any:

        '''
        Execute a signed HTTP request against the Binance REST API.

        Handles credential lookup, query string signing, URL construction,
        HTTP dispatch, error checking, and JSON parsing. Retries on
        TransientError with exponential backoff and jitter.

        Args:
            method (str): HTTP method (GET, POST, DELETE)
            path (str): API endpoint path
            params (dict[str, str]): Request parameters to sign and send
            account_id (str): Account identifier for credential lookup

        Returns:
            Any: Parsed JSON response body

        Raises:
            TransientError: After all retry attempts are exhausted
        '''

        session = await self._ensure_session()
        api_key, api_secret = self._get_credentials(account_id)
        headers = {_API_KEY_HEADER: api_key}
        last_error: TransientError | None = None

        for attempt in range(_MAX_RETRIES):
            query_string = self._sign_params(params, api_secret)

            try:
                async with session.request(
                    method,
                    f"{self._base_url}{path}?{query_string}",
                    headers=headers,
                ) as response:
                    await self._raise_on_error(response)
                    data: Any = await response.json()
                    return data
            except TransientError as exc:
                last_error = exc
                if attempt + 1 == _MAX_RETRIES:
                    break
                delay = random.uniform(0, _RETRY_BASE_DELAY * 2 ** attempt)
                _log.warning(
                    'Transient error on %s %s (attempt %d/%d), retrying in %.2fs: %s',
                    method, path, attempt + 1, _MAX_RETRIES, delay, exc,
                )
                await asyncio.sleep(delay)
            except VenueError:
                raise
            except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
                msg = f"Request failed: {exc}"
                last_error = TransientError(msg)
                if attempt + 1 == _MAX_RETRIES:
                    break
                delay = random.uniform(0, _RETRY_BASE_DELAY * 2 ** attempt)
                _log.warning(
                    'Transport error on %s %s (attempt %d/%d), retrying in %.2fs: %s',
                    method, path, attempt + 1, _MAX_RETRIES, delay, exc,
                )
                await asyncio.sleep(delay)

        _log.error(
            'All %d attempts exhausted on %s %s: %s',
            _MAX_RETRIES, method, path, last_error,
        )
        assert last_error is not None
        raise last_error

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
            'quantity': format(qty, 'f'),
            'newOrderRespType': 'FULL',
        }

        if order_type == OrderType.MARKET:
            params['type'] = 'MARKET'

        elif order_type == OrderType.LIMIT:
            params['type'] = 'LIMIT'
            if price is None:
                msg = 'price is required for LIMIT orders'
                raise ValueError(msg)
            params['price'] = format(price, 'f')
            params['timeInForce'] = time_in_force or 'GTC'

        elif order_type == OrderType.LIMIT_IOC:
            params['type'] = 'LIMIT'
            if price is None:
                msg = 'price is required for LIMIT_IOC orders'
                raise ValueError(msg)
            params['price'] = format(price, 'f')
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

    def _map_order_type(self, binance_type: str, time_in_force: str) -> OrderType:

        '''
        Map a Binance order type and time-in-force to an OrderType enum.

        Args:
            binance_type (str): Binance order type value
            time_in_force (str): Binance time-in-force value

        Returns:
            OrderType: Corresponding domain order type
        '''

        if binance_type == 'MARKET':
            return OrderType.MARKET
        if binance_type == 'LIMIT':
            if time_in_force == 'IOC':
                return OrderType.LIMIT_IOC
            return OrderType.LIMIT
        msg = f"Unknown Binance order type: '{binance_type}'"
        raise ValueError(msg)

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

    def _parse_venue_order(self, data: dict[str, Any]) -> VenueOrder:

        '''
        Parse a Binance order query response into a VenueOrder.

        Args:
            data (dict[str, Any]): Binance JSON response body

        Returns:
            VenueOrder: Normalised order representation
        '''

        order_type = self._map_order_type(data['type'], data.get('timeInForce', ''))
        price = None if order_type == OrderType.MARKET else Decimal(data['price'])

        return VenueOrder(
            venue_order_id=str(data['orderId']),
            client_order_id=str(data['clientOrderId']),
            status=self._map_order_status(data['status']),
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            order_type=order_type,
            qty=Decimal(data['origQty']),
            filled_qty=Decimal(data['executedQty']),
            price=price,
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
            venue_code = _UNKNOWN_VENUE_CODE
            reason = f"HTTP {response.status}"

        if venue_code in _NOT_FOUND_CODES:
            msg = f"Not found: {reason} (code {venue_code})"
            raise NotFoundError(msg)

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

        params = self._build_order_params(
            symbol, side, order_type, qty,
            price=price, stop_price=stop_price,
            client_order_id=client_order_id,
            time_in_force=time_in_force,
        )
        data = await self._signed_request('POST', '/api/v3/order', params, account_id)
        return self._parse_submit_response(data)

    async def cancel_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:

        '''
        Cancel an open order on the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            venue_order_id (str | None): Venue-assigned order identifier
            client_order_id (str | None): Deterministic client order identifier

        Returns:
            CancelResult: Venue response with order ID and terminal status
        '''

        if venue_order_id is None and client_order_id is None:
            msg = 'At least one of venue_order_id or client_order_id must be provided'
            raise ValueError(msg)

        params: dict[str, str] = {'symbol': symbol}

        if venue_order_id is not None:
            params['orderId'] = venue_order_id

        if client_order_id is not None:
            params['origClientOrderId'] = client_order_id

        data = await self._signed_request('DELETE', '/api/v3/order', params, account_id)
        return CancelResult(
            venue_order_id=str(data['orderId']),
            status=self._map_order_status(data['status']),
        )

    async def query_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> VenueOrder:

        '''
        Query the current state of an order on the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            venue_order_id (str | None): Venue-assigned order identifier
            client_order_id (str | None): Deterministic client order identifier

        Returns:
            VenueOrder: Current order state from the venue
        '''

        if venue_order_id is None and client_order_id is None:
            msg = 'At least one of venue_order_id or client_order_id must be provided'
            raise ValueError(msg)

        params: dict[str, str] = {'symbol': symbol}

        if venue_order_id is not None:
            params['orderId'] = venue_order_id

        if client_order_id is not None:
            params['origClientOrderId'] = client_order_id

        data = await self._signed_request('GET', '/api/v3/order', params, account_id)
        return self._parse_venue_order(data)

    async def query_open_orders(
        self,
        account_id: str,
        symbol: str,
    ) -> list[VenueOrder]:

        '''
        Query all open orders for a symbol on the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol

        Returns:
            list[VenueOrder]: Open orders from the venue
        '''

        params: dict[str, str] = {'symbol': symbol}
        data = await self._signed_request('GET', '/api/v3/openOrders', params, account_id)

        return [self._parse_venue_order(entry) for entry in data]

    async def query_balance(
        self,
        account_id: str,
        assets: frozenset[str],
    ) -> list[BalanceEntry]:

        '''
        Query account balances for specific assets from the venue.

        Args:
            account_id (str): Account identifier for API key routing
            assets (frozenset[str]): Asset symbols to retrieve balances for

        Returns:
            list[BalanceEntry]: Per-asset balance entries for requested assets
        '''

        if not assets:
            return []

        data = await self._signed_request('GET', '/api/v3/account', {}, account_id)

        return [
            BalanceEntry(
                asset=entry['asset'],
                free=Decimal(entry['free']),
                locked=Decimal(entry['locked']),
            )
            for entry in data['balances']
            if entry['asset'] in assets
        ]
