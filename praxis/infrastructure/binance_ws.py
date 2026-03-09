'''
Binance Spot user data stream lifecycle management.

Manage listen key creation, WebSocket connection, keepalive scheduling,
and stream shutdown for a single account.
'''

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import aiohttp

from praxis.infrastructure.venue_adapter import VenueError

if TYPE_CHECKING:
    from praxis.infrastructure.binance_adapter import BinanceAdapter


__all__ = ['BinanceUserStream']


_log = logging.getLogger(__name__)


_DEFAULT_KEEPALIVE_INTERVAL_SECONDS = 1800
_DEFAULT_RECONNECT_BASE_DELAY = 1.0
_DEFAULT_RECONNECT_MAX_DELAY = 60.0
_MAX_BACKOFF_EXPONENT = 30


class BinanceUserStream:

    '''
    Manage a single Binance user data WebSocket stream lifecycle.

    This class owns one listen key and one WebSocket connection for a single
    account_id. When on_message is provided, automatically reconnects with
    exponential backoff on disconnect.

    Args:
        adapter (BinanceAdapter): Binance REST adapter used for credentials,
            session access, and listen key REST calls
        account_id (str): Account identifier
        on_message (Callable[[dict], Awaitable[None]] | None): Async callback
            invoked with each parsed JSON frame from the stream
        keepalive_interval_seconds (int): Listen key keepalive interval
            in seconds
        reconnect_base_delay (float): Initial reconnect delay in seconds
        reconnect_max_delay (float): Maximum reconnect delay in seconds
    '''

    def __init__(
        self,
        adapter: BinanceAdapter,
        account_id: str,
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        keepalive_interval_seconds: int = _DEFAULT_KEEPALIVE_INTERVAL_SECONDS,
        reconnect_base_delay: float = _DEFAULT_RECONNECT_BASE_DELAY,
        reconnect_max_delay: float = _DEFAULT_RECONNECT_MAX_DELAY,
    ) -> None:

        '''
        Initialize stream lifecycle state.

        Args:
            adapter (BinanceAdapter): Binance REST adapter instance
            account_id (str): Account identifier
            on_message (Callable[[dict], Awaitable[None]] | None): Async
                callback for incoming JSON frames
            keepalive_interval_seconds (int): Keepalive interval in seconds
            reconnect_base_delay (float): Initial reconnect delay in seconds
            reconnect_max_delay (float): Maximum reconnect delay in seconds
        '''

        self._adapter = adapter
        self._account_id = account_id
        self._keepalive_interval_seconds = keepalive_interval_seconds
        self._listen_key: str | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
        self._on_message = on_message
        self._reconnect_task: asyncio.Task[None] | None = None
        self._reconnect_base_delay = reconnect_base_delay
        self._reconnect_max_delay = reconnect_max_delay

    @property
    def listen_key(self) -> str | None:

        '''
        Return the active listen key if connected.

        Returns:
            str | None: Active listen key, or None when disconnected
        '''

        return self._listen_key

    @property
    def websocket(self) -> aiohttp.ClientWebSocketResponse | None:

        '''
        Return the active WebSocket connection if connected.

        Returns:
            aiohttp.ClientWebSocketResponse | None: Active WebSocket,
                or None when disconnected
        '''

        return self._ws

    async def initiate_connection(self) -> None:

        '''
        Create listen key, open WebSocket, start keepalive and auto-reconnect loop.

        Auto-reconnect loop is only started when on_message callback is set.

        Raises:
            aiohttp.ClientError: If WebSocket connection fails
            TimeoutError: If network operations time out
            ValueError: If adapter WS base URL scheme is not wss
            VenueError: If listen key management fails via adapter methods
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
        Clean up stale state, create listen key, open WebSocket, start keepalive.

        Called by initiate_connection() on initial connection and by _auto_reconnect() on
        reconnection. Handles full teardown of previous connection state before
        setting up a new one.

        Raises:
            aiohttp.ClientError: If WebSocket connection fails
            TimeoutError: If network operations time out
            ValueError: If adapter WS base URL scheme is not wss
            VenueError: If listen key management fails via adapter methods
        '''

        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keepalive_task
            self._keepalive_task = None
        if self._ws is not None:
            with contextlib.suppress(aiohttp.ClientError):
                await self._ws.close()
            self._ws = None
        if self._listen_key is not None:
            with contextlib.suppress(VenueError):
                await self._adapter._close_listen_key(self._account_id, self._listen_key)
            self._listen_key = None

        listen_key = await self._adapter._create_listen_key(self._account_id)

        try:
            ws_url = self._build_ws_url(listen_key)
            session = await self._adapter._ensure_session()
            ws = await session.ws_connect(ws_url)
        except (aiohttp.ClientError, TimeoutError, ValueError):
            with contextlib.suppress(VenueError):
                await self._adapter._close_listen_key(self._account_id, listen_key)
            raise

        self._listen_key = listen_key
        self._ws = ws
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def close(self) -> None:

        '''
        Stop reconnect loop, keepalive, close WebSocket, and invalidate listen key.
        '''

        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None

        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keepalive_task
            self._keepalive_task = None

        if self._ws is not None:
            with contextlib.suppress(aiohttp.ClientError):
                await self._ws.close()
            self._ws = None

        if self._listen_key is not None:
            listen_key = self._listen_key
            self._listen_key = None
            with contextlib.suppress(VenueError):
                await self._adapter._close_listen_key(self._account_id, listen_key)

    async def __aenter__(self) -> BinanceUserStream:

        '''
        Connect on entering async context.

        Returns:
            BinanceUserStream: Connected stream manager
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

    async def _keepalive_loop(self) -> None:

        '''
        Periodically renew the active listen key until cancelled.
        '''

        while True:
            await asyncio.sleep(self._keepalive_interval_seconds)
            listen_key = self._listen_key

            if listen_key is None:
                return

            try:
                await self._adapter._keepalive_listen_key(self._account_id, listen_key)
            except (VenueError, aiohttp.ClientError, TimeoutError):
                _log.warning('keepalive failed for %s', self._account_id, exc_info=True)

    async def _auto_reconnect(self) -> None:

        '''
        Run receive loop with automatic reconnection on disconnect.

        Calls _receive_loop() to read frames. When _receive_loop() returns (WebSocket
        closed or errored), waits with exponential backoff and calls
        _clean_setup_connection() to reconnect. Resets attempt counter on successful
        reconnection. Exits cleanly on CancelledError from close().
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
        Read WebSocket frames and dispatch parsed JSON to the on_message callback.
        '''

        assert self._ws is not None
        assert self._on_message is not None

        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    _log.warning('non-JSON frame: %s', msg.data[:200])
                    continue
                try:
                    await self._on_message(data)
                except Exception:  # noqa: BLE001
                    _log.exception('on_message callback error')
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break

    def _build_ws_url(self, listen_key: str) -> str:

        '''
        Build user data stream WebSocket URL from adapter WS base URL.

        Args:
            listen_key (str): Active listen key

        Returns:
            str: WebSocket URL for the stream

        Raises:
            ValueError: If adapter WS base URL scheme is not wss
        '''

        ws_base_url = self._adapter._ws_base_url

        if not ws_base_url.startswith('wss://'):
            msg = f"Unsupported WS base URL scheme: {ws_base_url!r}"
            raise ValueError(msg)

        return f"{ws_base_url}/ws/{listen_key}"
