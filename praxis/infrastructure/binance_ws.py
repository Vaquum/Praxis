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
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import aiohttp

from praxis.infrastructure.venue_adapter import VenueError

if TYPE_CHECKING:
    from praxis.infrastructure.binance_adapter import BinanceAdapter


__all__ = ['BinanceUserStream']


_log = logging.getLogger(__name__)


_DEFAULT_KEEPALIVE_INTERVAL_SECONDS = 1800


class BinanceUserStream:

    '''
    Manage a single Binance user data WebSocket stream lifecycle.

    This class owns one listen key and one WebSocket connection for a single
    account_id. Reconnection and event parsing are handled in later work items.

    Args:
        adapter (BinanceAdapter): Binance REST adapter used for credentials,
            session access, and listen key REST calls
        account_id (str): Account identifier
        on_message (Callable[[dict], Awaitable[None]] | None): Async callback
            invoked with each parsed JSON frame from the stream
        keepalive_interval_seconds (int): Listen key keepalive interval
            in seconds
    '''

    def __init__(
        self,
        adapter: BinanceAdapter,
        account_id: str,
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        keepalive_interval_seconds: int = _DEFAULT_KEEPALIVE_INTERVAL_SECONDS,
    ) -> None:

        '''
        Initialize stream lifecycle state.

        Args:
            adapter (BinanceAdapter): Binance REST adapter instance
            account_id (str): Account identifier
            on_message (Callable[[dict], Awaitable[None]] | None): Async
                callback for incoming JSON frames
            keepalive_interval_seconds (int): Keepalive interval in seconds
        '''

        self._adapter = adapter
        self._account_id = account_id
        self._keepalive_interval_seconds = keepalive_interval_seconds
        self._listen_key: str | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
        self._on_message = on_message
        self._listen_task: asyncio.Task[None] | None = None

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

    async def connect(self) -> None:

        '''
        Create listen key, open WebSocket, and start keepalive and listen loops.

        Raises:
            aiohttp.ClientError: If WebSocket connection fails
            TimeoutError: If network operations time out
            ValueError: If adapter base URL scheme is not https
            VenueError: If listen key management fails via adapter methods
        '''

        if self._ws is not None and not self._ws.closed:
            return

        if self._ws is not None and self._ws.closed:
            if self._listen_task is not None:
                self._listen_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._listen_task
                self._listen_task = None
            if self._keepalive_task is not None:
                self._keepalive_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._keepalive_task
                self._keepalive_task = None
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
        if self._on_message is not None:
            self._listen_task = asyncio.create_task(self._listen())

    async def close(self) -> None:

        '''
        Stop listen loop, keepalive, close WebSocket, and invalidate listen key.
        '''

        if self._listen_task is not None:
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

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

        await self.connect()
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

    async def _listen(self) -> None:

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
        Build user data stream WebSocket URL from adapter base URL.

        Args:
            listen_key (str): Active listen key

        Returns:
            str: WebSocket URL for the stream

        Raises:
            ValueError: If adapter base URL scheme is not https
        '''

        base_url = self._adapter._base_url

        if not base_url.startswith('https://'):
            msg = f"Unsupported base URL scheme: {base_url!r}"
            raise ValueError(msg)

        ws_base = f"wss://{base_url[len('https://') :]}"

        return f"{ws_base}/ws/{listen_key}"
