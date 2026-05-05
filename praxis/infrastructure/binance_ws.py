'''
Binance Spot user data stream lifecycle management via the WebSocket API.

Manage WebSocket connection, signed `userDataStream.subscribe.signature`
subscription, and stream shutdown for a single account.
'''

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import logging
import random
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import aiohttp
import orjson

from praxis.infrastructure.venue_adapter import VenueError

if TYPE_CHECKING:
    from praxis.infrastructure.binance_adapter import BinanceAdapter


__all__ = ['BinanceUserStream']


_log = logging.getLogger(__name__)


_DEFAULT_RECONNECT_BASE_DELAY = 1.0
_DEFAULT_RECONNECT_MAX_DELAY = 60.0
_MAX_BACKOFF_EXPONENT = 30
_SUBSCRIBE_RECV_WINDOW_MS = 5000
_SUBSCRIBE_ACK_TIMEOUT_SECONDS = 10.0
_OK_STATUS = 200


class BinanceUserStream:

    '''
    Manage a single Binance user data WebSocket-API session lifecycle.

    Owns one WS-API connection per account_id. Subscribes via
    `userDataStream.subscribe.signature` and consumes pushed user-data
    events on the same connection. Auto-reconnects with exponential
    backoff on disconnect when on_message is set.

    Args:
        adapter (BinanceAdapter): Binance adapter; provides credentials,
            shared aiohttp session, and the WS-API base URL
        account_id (str): Account identifier
        on_message (Callable[[dict], Awaitable[None]] | None): Async
            callback invoked with each pushed event payload (the inner
            object of the WS-API `event` envelope)
        reconnect_base_delay (float): Initial reconnect delay in seconds
        reconnect_max_delay (float): Maximum reconnect delay in seconds
    '''

    def __init__(
        self,
        adapter: BinanceAdapter,
        account_id: str,
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        reconnect_base_delay: float = _DEFAULT_RECONNECT_BASE_DELAY,
        reconnect_max_delay: float = _DEFAULT_RECONNECT_MAX_DELAY,
    ) -> None:

        self._adapter = adapter
        self._account_id = account_id
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._on_message = on_message
        self._reconnect_task: asyncio.Task[None] | None = None
        self._reconnect_base_delay = reconnect_base_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._subscription_id: int | None = None

    @property
    def websocket(self) -> aiohttp.ClientWebSocketResponse | None:

        '''
        Return the active WebSocket connection if connected.
        '''

        return self._ws

    @property
    def subscription_id(self) -> int | None:

        '''
        Return the active user-data-stream subscription id if subscribed.
        '''

        return self._subscription_id

    async def initiate_connection(self) -> None:

        '''
        Open WS-API connection, subscribe to user-data-stream, start
        auto-reconnect loop. Auto-reconnect is only started when
        on_message is set.

        Raises:
            aiohttp.ClientError: If WebSocket connection fails
            TimeoutError: If subscription ack times out
            ValueError: If WS-API URL scheme is not wss
            VenueError: If subscription is rejected by the venue
        '''

        if self._ws is not None and not self._ws.closed:
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return

        await self._clean_setup_connection()
        if self._on_message is not None:
            self._reconnect_task = asyncio.create_task(self._auto_reconnect())

    async def _clean_setup_connection(self) -> None:

        '''
        Tear down stale WS, open new WS-API connection, send signed
        `userDataStream.subscribe.signature` frame, await ack.

        Raises:
            aiohttp.ClientError: If WebSocket connection fails
            TimeoutError: If subscription ack times out
            ValueError: If WS-API URL scheme is not wss
            VenueError: If subscription is rejected by the venue
        '''

        if self._ws is not None:
            with contextlib.suppress(aiohttp.ClientError):
                await self._ws.close()
            self._ws = None
        self._subscription_id = None

        ws_api_url = self._adapter._ws_api_url
        if not ws_api_url.startswith('wss://'):
            msg = f"Unsupported WS-API URL scheme: {ws_api_url!r}"
            raise ValueError(msg)

        credentials = self._adapter._credentials.get(self._account_id)
        if credentials is None:
            msg = f"No credentials registered for account {self._account_id!r}"
            raise VenueError(msg)
        api_key, api_secret = credentials

        session = await self._adapter._ensure_session()
        ws = await session.ws_connect(ws_api_url)

        try:
            await self._subscribe(ws, api_key, api_secret)
        except (aiohttp.ClientError, TimeoutError, VenueError):
            with contextlib.suppress(aiohttp.ClientError):
                await ws.close()
            raise

        self._ws = ws

    async def _subscribe(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        api_key: str,
        api_secret: str,
    ) -> None:

        '''
        Send the signed `userDataStream.subscribe.signature` frame and
        validate the ack. The signature covers the alphabetically-sorted
        params (`apiKey`, `recvWindow`, `timestamp`) joined as
        `key=value&...` and HMAC-SHA256-signed with `api_secret`.

        Raises:
            TimeoutError: If ack does not arrive within the timeout
            VenueError: If ack status is non-200 or response is malformed
        '''

        timestamp = int(time.time() * 1000)
        params: dict[str, str | int] = {
            'apiKey': api_key,
            'recvWindow': _SUBSCRIBE_RECV_WINDOW_MS,
            'timestamp': timestamp,
        }
        qs = '&'.join(f'{k}={params[k]}' for k in sorted(params))
        signature = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        params['signature'] = signature

        request = {
            'id': str(uuid.uuid4()),
            'method': 'userDataStream.subscribe.signature',
            'params': params,
        }
        await ws.send_str(orjson.dumps(request).decode('utf-8'))

        try:
            ack = await asyncio.wait_for(
                ws.receive(), timeout=_SUBSCRIBE_ACK_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            text = f"WS-API subscribe ack timed out for account {self._account_id!r}"
            raise TimeoutError(text) from exc

        if ack.type != aiohttp.WSMsgType.TEXT:
            text = (
                f"WS-API subscribe returned non-text frame for account "
                f"{self._account_id!r}: type={ack.type.name}"
            )
            raise VenueError(text)

        try:
            response = orjson.loads(ack.data.encode('utf-8'))
        except orjson.JSONDecodeError as exc:
            text = (
                f"WS-API subscribe returned non-JSON frame for account "
                f"{self._account_id!r}: {ack.data[:200]}"
            )
            raise VenueError(text) from exc

        status = response.get('status') if isinstance(response, dict) else None
        if status != _OK_STATUS:
            text = (
                f"WS-API subscribe failed for account {self._account_id!r}: "
                f"{response}"
            )
            raise VenueError(text)

        result = response.get('result')
        sub_id = result.get('subscriptionId') if isinstance(result, dict) else None
        if not isinstance(sub_id, int) or isinstance(sub_id, bool):
            text = (
                f"WS-API subscribe ack missing subscriptionId for account "
                f"{self._account_id!r}: {response}"
            )
            raise VenueError(text)

        self._subscription_id = sub_id

    async def close(self) -> None:

        '''
        Stop reconnect loop, send unsubscribe frame (best-effort), close
        the WS connection.
        '''

        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None

        if self._ws is not None:
            ws = self._ws
            sub_id = self._subscription_id
            self._ws = None
            self._subscription_id = None
            with contextlib.suppress(aiohttp.ClientError, TimeoutError):
                request: dict[str, Any] = {
                    'id': str(uuid.uuid4()),
                    'method': 'userDataStream.unsubscribe',
                }
                if sub_id is not None:
                    request['params'] = {'subscriptionId': sub_id}
                await ws.send_str(orjson.dumps(request).decode('utf-8'))
            with contextlib.suppress(aiohttp.ClientError):
                await ws.close()

    async def __aenter__(self) -> BinanceUserStream:

        '''
        Connect on entering async context.
        '''

        await self.initiate_connection()
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: object | None,
    ) -> None:

        '''
        Close stream resources on context exit.
        '''

        await self.close()

    async def _auto_reconnect(self) -> None:

        '''
        Run receive loop with automatic reconnection on disconnect.

        Calls _receive_loop() to read frames. When _receive_loop() returns
        (WebSocket closed or errored), waits with exponential backoff and
        calls _clean_setup_connection() to reconnect. Resets attempt
        counter on successful reconnection. Exits cleanly on
        CancelledError from close().
        '''

        attempts = 0
        while True:
            await self._receive_loop()
            attempts += 1
            while True:
                delay = min(
                    self._reconnect_base_delay * (2 ** min(attempts - 1, _MAX_BACKOFF_EXPONENT)),
                    self._reconnect_max_delay,
                ) * (0.5 + random.random() * 0.5)
                _log.warning(
                    'WebSocket disconnected for %s, reconnecting in %.1fs (attempt %d)',
                    self._account_id, delay, attempts,
                )
                await asyncio.sleep(delay)
                try:
                    await self._clean_setup_connection()
                    attempts = 0
                    break
                except (VenueError, aiohttp.ClientError, TimeoutError):
                    _log.warning(
                        'reconnect failed for %s (attempt %d)',
                        self._account_id, attempts, exc_info=True,
                    )
                    attempts += 1

    async def _receive_loop(self) -> None:

        '''
        Read WS-API frames and dispatch pushed user-data events to the
        on_message callback. WS-API push events are wrapped in an
        `event` envelope; non-event frames (e.g. unsolicited acks for
        in-flight requests) are ignored.
        '''

        assert self._ws is not None
        assert self._on_message is not None

        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = orjson.loads(msg.data.encode('utf-8'))
                except orjson.JSONDecodeError:
                    _log.warning('non-JSON frame: %s', msg.data[:200])
                    continue
                event = data.get('event') if isinstance(data, dict) else None
                if not isinstance(event, dict):
                    _log.debug('non-event frame: %s', str(data)[:200])
                    continue
                try:
                    await self._on_message(event)
                except Exception:  # noqa: BLE001
                    _log.exception('on_message callback error')
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break
