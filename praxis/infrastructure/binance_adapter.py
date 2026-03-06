'''
Binance Spot REST adapter for order submission via the VenueAdapter protocol.

Handle authentication, request signing, order submission, and response
normalization for the Binance Spot API. All Binance-specific logic is
encapsulated here.
'''

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import logging
import random
import time
from collections.abc import Sequence
from datetime import datetime, timezone
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
    SymbolFilters,
    TransientError,
    VenueError,
    VenueOrder,
    VenueTrade,
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
_DEFAULT_WEIGHT_LIMIT = 6000
_DEFAULT_ORDER_COUNT_LIMIT = 10
_RATE_LIMIT_WARN_THRESHOLD = 0.2
_WEIGHT_INTERVAL_NUM = 1
_ORDER_COUNT_INTERVAL_NUM = 10

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

_BINANCE_TYPE_MAP: dict[str, OrderType] = {
    'MARKET': OrderType.MARKET,
    'LIMIT_MAKER': OrderType.LIMIT,
    'STOP_LOSS': OrderType.STOP,
    'STOP_LOSS_LIMIT': OrderType.STOP_LIMIT,
    'TAKE_PROFIT': OrderType.TAKE_PROFIT,
    'TAKE_PROFIT_LIMIT': OrderType.TP_LIMIT,
    'OCO': OrderType.OCO,
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
        self._filters: dict[str, SymbolFilters] = {}
        self._used_weight: int = 0
        self._weight_limit: int = _DEFAULT_WEIGHT_LIMIT
        self._order_count: dict[str, int] = {}
        self._order_count_limit: int = _DEFAULT_ORDER_COUNT_LIMIT
        self._prev_headroom_above_threshold: bool = True

    @property
    def weight_headroom(self) -> float:

        '''
        Remaining request weight as a fraction of the limit.

        Returns:
            float: Value between 0.0 (exhausted) and 1.0 (fully available)
        '''

        if self._weight_limit <= 0:
            return 1.0

        return max(0.0, (self._weight_limit - self._used_weight) / self._weight_limit)

    def order_count_headroom(self, account_id: str) -> float:

        '''
        Remaining order count as a fraction of the limit for an account.

        Args:
            account_id (str): Account identifier

        Returns:
            float: Value between 0.0 (exhausted) and 1.0 (fully available)
        '''

        used = self._order_count.get(account_id, 0)

        if self._order_count_limit <= 0:
            return 1.0

        return max(0.0, (self._order_count_limit - used) / self._order_count_limit)

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
                    self._update_weight_from_headers(response, account_id)
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
            except RateLimitError as exc:
                if attempt + 1 == _MAX_RETRIES:
                    raise
                delay = exc.retry_after if exc.retry_after is not None else _RETRY_BASE_DELAY * 2 ** attempt
                _log.warning(
                    'Rate limited on %s %s (attempt %d/%d), retrying in %.2fs',
                    method, path, attempt + 1, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except VenueError:
                raise
            except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
                msg = f"Request failed: {exc}"
                last_error = TransientError(msg)
                last_error.__cause__ = exc
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
        if last_error is None:
            raise TransientError(f"All {_MAX_RETRIES} attempts exhausted on {method} {path}")
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

        if binance_type == 'LIMIT':
            # FOK mapped to LIMIT_IOC: no dedicated enum value; both are non-resting
            if time_in_force in ('IOC', 'FOK'):
                return OrderType.LIMIT_IOC
            return OrderType.LIMIT

        result = _BINANCE_TYPE_MAP.get(binance_type)
        if result is not None:
            return result

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
                is_maker=False,  # Binance FULL fills omit isMaker; always taker
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

    def _parse_venue_trade(self, data: dict[str, Any]) -> VenueTrade:

        '''
        Parse a Binance myTrades response entry into a VenueTrade.

        Args:
            data (dict[str, Any]): Single trade entry from Binance myTrades response

        Returns:
            VenueTrade: Normalised trade representation
        '''

        return VenueTrade(
            venue_trade_id=str(data['id']),
            venue_order_id=str(data['orderId']),
            client_order_id=str(data['clientOrderId']),
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            qty=Decimal(data['qty']),
            price=Decimal(data['price']),
            fee=Decimal(data['commission']),
            fee_asset=data['commissionAsset'],
            is_maker=data['isMaker'],
            timestamp=datetime.fromtimestamp(
                data['time'] / _MS_PER_SECOND, tz=timezone.utc,
            ),
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
            raw = response.headers.get('Retry-After')
            retry_after: float | None = None

            if raw is not None:
                with contextlib.suppress(ValueError, OverflowError):
                    retry_after = float(raw)

            msg = f"Rate limited: HTTP {response.status}"
            raise RateLimitError(msg, retry_after=retry_after)

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

    def _validate_order(
        self,
        symbol: str,
        order_type: OrderType,
        qty: Decimal,
        price: Decimal | None,
    ) -> None:

        '''
        Validate order parameters against cached venue filters.

        Checks quantity step and quantity range for all orders, and price
        tick and minimum notional only for priced, non-market orders.
        Logs a warning and returns without validation if filters are not
        cached for the symbol.

        Args:
            symbol (str): Trading pair symbol
            order_type (OrderType): Order type
            qty (Decimal): Order quantity
            price (Decimal | None): Limit price
        '''

        filters = self._filters.get(symbol)

        if filters is None:
            _log.warning('No cached filters for %s, skipping validation', symbol)
            return

        if qty % filters.lot_step != 0:
            msg = f"qty {qty} is not a multiple of lot step {filters.lot_step}"
            raise ValueError(msg)

        if qty < filters.lot_min:
            msg = f"qty {qty} is below lot minimum {filters.lot_min}"
            raise ValueError(msg)

        if qty > filters.lot_max:
            msg = f"qty {qty} is above lot maximum {filters.lot_max}"
            raise ValueError(msg)

        if price is not None and order_type != OrderType.MARKET:
            if price % filters.tick_size != 0:
                msg = f"price {price} is not a multiple of tick size {filters.tick_size}"
                raise ValueError(msg)

            if price * qty < filters.min_notional:
                msg = f"notional {price * qty} is below minimum {filters.min_notional}"
                raise ValueError(msg)


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

        self._validate_order(symbol, order_type, qty, price)

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

    async def query_trades(
        self,
        account_id: str,
        symbol: str,
        *,
        start_time: datetime | None = None,
    ) -> list[VenueTrade]:

        '''
        Query historical trade records from the venue.

        Args:
            account_id (str): Account identifier for API key routing
            symbol (str): Trading pair symbol
            start_time (datetime | None): Return trades after this time, must be timezone-aware

        Returns:
            list[VenueTrade]: Trade records from the venue
        '''

        if start_time is not None and (start_time.tzinfo is None or start_time.utcoffset() is None):
            msg = 'start_time must be timezone-aware'
            raise ValueError(msg)

        params: dict[str, str] = {'symbol': symbol}

        if start_time is not None:
            params['startTime'] = str(int(start_time.timestamp() * _MS_PER_SECOND))

        data = await self._signed_request('GET', '/api/v3/myTrades', params, account_id)

        return [self._parse_venue_trade(entry) for entry in data]

    async def load_filters(self, symbols: Sequence[str]) -> None:

        '''
        Pre-load trading filters for one or more symbols.

        Calls get_exchange_info for each symbol and caches the result.
        Intended to be called once on startup before trading begins.
        Raises on first failure to ensure filters are available.

        Args:
            symbols (Sequence[str]): Trading pair symbols to load
        '''

        if isinstance(symbols, str):
            msg = 'load_filters expects a sequence of symbols, not a single string'
            raise TypeError(msg)

        for symbol in symbols:
            self._filters[symbol] = await self.get_exchange_info(symbol)

    async def get_exchange_info(self, symbol: str) -> SymbolFilters:

        '''
        Query trading filters for a symbol from the venue.

        Fetches symbol filters from the unauthenticated exchangeInfo
        endpoint. Parses PRICE_FILTER, LOT_SIZE, and NOTIONAL filters.

        Args:
            symbol (str): Trading pair symbol

        Returns:
            SymbolFilters: Venue-imposed trading constraints
        '''

        session = await self._ensure_session()

        try:
            async with session.request(
                'GET',
                f"{self._base_url}/api/v3/exchangeInfo",
                params={'symbol': symbol},
            ) as response:
                self._update_weight_from_headers(response)
                await self._raise_on_error(response)
                data: Any = await response.json()
        except OrderRejectedError as exc:
            msg = f"exchangeInfo failed for {symbol!r}: {exc}"
            raise VenueError(msg) from exc
        except VenueError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            msg = f"Request failed: {exc}"
            raise TransientError(msg) from exc

        self._parse_rate_limits(data)

        symbols_list = data.get('symbols') if isinstance(data, dict) else None

        if not isinstance(symbols_list, list) or not symbols_list:
            msg = f"Unexpected exchangeInfo payload for {symbol!r}: missing or empty 'symbols'"
            raise VenueError(msg)

        symbol_info = symbols_list[0]
        filters_list = symbol_info.get('filters') if isinstance(symbol_info, dict) else None

        if not isinstance(filters_list, list) or not filters_list:
            msg = f"Unexpected exchangeInfo payload for {symbol!r}: missing or empty 'filters'"
            raise VenueError(msg)

        filters: dict[str, dict[str, Any]] = {
            f['filterType']: f
            for f in filters_list
            if isinstance(f, dict) and 'filterType' in f
        }

        required = ('PRICE_FILTER', 'LOT_SIZE', 'NOTIONAL')
        missing = [name for name in required if name not in filters]

        if missing:
            msg = f"Missing required filters for {symbol}: {', '.join(missing)}"
            raise VenueError(msg)

        try:
            return SymbolFilters(
                symbol=symbol,
                tick_size=Decimal(filters['PRICE_FILTER']['tickSize']),
                lot_step=Decimal(filters['LOT_SIZE']['stepSize']),
                lot_min=Decimal(filters['LOT_SIZE']['minQty']),
                lot_max=Decimal(filters['LOT_SIZE']['maxQty']),
                min_notional=Decimal(filters['NOTIONAL']['minNotional']),
            )
        except (KeyError, ArithmeticError) as exc:
            msg = f"Malformed exchangeInfo payload for {symbol!r}: {exc}"
            raise VenueError(msg) from exc

    def _update_weight_from_headers(
        self,
        response: aiohttp.ClientResponse,
        account_id: str | None = None,
    ) -> None:

        '''
        Update rate limit counters from response headers.

        Reads X-MBX-USED-WEIGHT-1M (per-IP) and X-MBX-ORDER-COUNT-10S
        (per-API-key, keyed by account_id). Logs a warning when
        weight headroom drops below the configured threshold.
        Silently ignores missing or unparseable headers.

        Args:
            response (aiohttp.ClientResponse): HTTP response
            account_id (str | None): Account identifier for order count tracking
        '''

        weight_raw = response.headers.get('X-MBX-USED-WEIGHT-1M')

        if weight_raw is not None:
            with contextlib.suppress(ValueError):
                self._used_weight = int(weight_raw)

        if account_id is not None:
            order_raw = response.headers.get('X-MBX-ORDER-COUNT-10S')

            if order_raw is not None:
                with contextlib.suppress(ValueError):
                    self._order_count[account_id] = int(order_raw)

        if self._weight_limit > 0:
            headroom = (self._weight_limit - self._used_weight) / self._weight_limit
            below = headroom < _RATE_LIMIT_WARN_THRESHOLD

            if below and self._prev_headroom_above_threshold:
                log_headroom = max(0.0, headroom)
                _log.warning(
                    'Rate limit headroom low: %d/%d used (%.1f%% remaining)',
                    self._used_weight, self._weight_limit, log_headroom * 100,
                )

            self._prev_headroom_above_threshold = not below

    def _parse_rate_limits(self, data: Any) -> None:

        '''
        Parse rateLimits array from exchangeInfo response.

        Extracts REQUEST_WEIGHT and ORDERS limits and updates
        the cached limit values when successfully parsed. Warns
        and leaves existing cached values unchanged on parse failure.

        Args:
            data (Any): Parsed exchangeInfo JSON payload
        '''

        rate_limits = data.get('rateLimits') if isinstance(data, dict) else None

        if not isinstance(rate_limits, list):
            _log.warning('exchangeInfo missing rateLimits array, using defaults')
            return

        for entry in rate_limits:
            if not isinstance(entry, dict):
                continue

            limit_type = entry.get('rateLimitType')
            interval = entry.get('interval')
            limit_val = entry.get('limit')
            interval_num = entry.get('intervalNum')

            if not isinstance(limit_val, int):
                continue

            if (
                limit_type == 'REQUEST_WEIGHT'
                and interval == 'MINUTE'
                and interval_num == _WEIGHT_INTERVAL_NUM
            ):
                self._weight_limit = limit_val

            if (
                limit_type == 'ORDERS'
                and interval == 'SECOND'
                and interval_num == _ORDER_COUNT_INTERVAL_NUM
            ):
                self._order_count_limit = limit_val
