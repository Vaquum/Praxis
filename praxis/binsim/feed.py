'''Background depth-snapshot poller for the binsim order book.'''

from __future__ import annotations

import asyncio
import contextlib
import time
from decimal import Decimal
from typing import Any

import aiohttp

from praxis.binsim.book import OrderBook
from praxis.infrastructure.observability import get_logger


__all__ = ['DepthPoller']


_log = get_logger(__name__)

_DEFAULT_POLL_INTERVAL_MS = 1000
_DEFAULT_REQUEST_TIMEOUT_S = 5.0
_HTTP_OK = 200


class DepthPoller:

    '''Poll a hosted depth-N snapshot endpoint and feed an `OrderBook`.

    Owns a single `aiohttp.ClientSession` and a background poll task.
    On each successful poll the response is parsed and the bound
    `OrderBook` is replaced wholesale; the wall-clock `t` from the
    successful poll captures the local wall-clock as
    `last_success_ts_ms` so the HTTP layer's staleness gate can query
    freshness without subscribing to events and without trusting any
    timestamp from the upstream payload.

    Failures (network, 5xx, malformed body, schema rejection) are
    logged and the loop continues at the same cadence — the staleness
    gate naturally surfaces persistent failure by observing
    `last_success_ts_ms` falling behind wall-clock.
    '''

    def __init__(
        self,
        book: OrderBook,
        url: str,
        token: str,
        poll_interval_ms: int = _DEFAULT_POLL_INTERVAL_MS,
        request_timeout_s: float = _DEFAULT_REQUEST_TIMEOUT_S,
    ) -> None:

        if poll_interval_ms <= 0:
            raise ValueError(f'poll_interval_ms must be positive, got {poll_interval_ms}')

        if request_timeout_s <= 0:
            raise ValueError(f'request_timeout_s must be positive, got {request_timeout_s}')

        if not url:
            raise ValueError('url cannot be empty')

        if not token:
            raise ValueError('token cannot be empty')

        self._book = book
        self._url = url
        self._token = token
        self._poll_interval_s = poll_interval_ms / 1000.0
        self._request_timeout = aiohttp.ClientTimeout(total=request_timeout_s)

        self._session: aiohttp.ClientSession | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._last_success_ts_ms = 0

    @property
    def last_success_ts_ms(self) -> int:

        return self._last_success_ts_ms

    @property
    def is_running(self) -> bool:

        return self._task is not None and not self._task.done()

    async def start(self) -> None:

        '''Open the HTTP session and start the background poll task.'''

        if self.is_running:
            raise RuntimeError('DepthPoller already running')

        self._stop_event.clear()
        self._session = aiohttp.ClientSession(timeout=self._request_timeout)
        self._task = asyncio.create_task(self._poll_loop(), name='binsim-depth-poller')

    async def stop(self) -> None:

        '''Signal the poll task to exit, await it, and close the session.'''

        self._stop_event.set()

        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

            self._task = None

        if self._session is not None:
            await self._session.close()
            self._session = None

    async def poll_once(self) -> None:

        '''Perform a single poll cycle.

        Exposed for tests and for forcing an initial snapshot before
        `start()` enters the steady-state loop. Raises on any failure
        so callers can distinguish first-poll success from a doomed
        steady-state loop.
        '''

        if self._session is None:
            raise RuntimeError('DepthPoller session not initialised; call start() first')

        headers = {'Authorization': f'Bearer {self._token}'}

        async with self._session.get(self._url, headers=headers) as response:
            if response.status != _HTTP_OK:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f'depth poll non-200: {response.status}',
                )

            payload = await response.json()

        ts_ms, last_update_id, bids, asks = self._parse_payload(payload)
        self._book.replace(bids, asks, last_update_id, ts_ms)
        # Record local wall-clock at receipt, NOT the upstream `t`.
        # The HTTP layer's staleness gate compares this against its
        # own `time.time()`; if we trusted upstream `t` directly, a
        # future-dated `t` (clock skew on the source, payload tampering)
        # would silently make the book appear "newer than now" and the
        # gate's `age_ms > threshold` check would pass forever.
        # `book.ts_ms` retains the upstream `t` for informational use
        # in `GET /api/v3/depth`.
        self._last_success_ts_ms = int(time.time() * 1000)

    async def _poll_loop(self) -> None:

        while not self._stop_event.is_set():
            try:
                await self.poll_once()
            except (aiohttp.ClientError, TimeoutError) as exc:
                _log.warning(
                    'depth poll failed (transient)',
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                # Covers every shape failure `_parse_payload` can
                # surface: non-dict body (TypeError), missing field
                # (KeyError), unparseable int (ValueError),
                # malformed Decimal (ArithmeticError →
                # decimal.InvalidOperation), and `OrderBook.replace`
                # validation rejections (ValueError). The task must
                # NOT crash on any of these — staleness gate would
                # eventually trip but the operator would lose the
                # log signal explaining why.
                _log.error(
                    'depth poll failed (malformed upstream payload)',
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

            try:
                await asyncio.wait_for(self._stop_event.wait(), self._poll_interval_s)
            except TimeoutError:
                continue

    @staticmethod
    def _parse_payload(
        payload: Any,
    ) -> tuple[int, int, list[tuple[Decimal, Decimal]], list[tuple[Decimal, Decimal]]]:

        '''Extract (ts_ms, last_update_id, bids, asks) from the source body.

        Source shape: `{t: <unix-ms>, d: {lastUpdateId, bids: [[p, q], ...], asks: [[p, q], ...]}}`.
        Prices and quantities arrive as strings (Binance convention)
        and are coerced to `Decimal` at this boundary so downstream
        math is exact.

        Raises:
            ValueError: payload (or its `d` sub-object) is not a dict.
            KeyError: a required field is missing.
            ArithmeticError: a price/qty string is not a valid Decimal.
            TypeError: bids/asks entries cannot unpack to (price, qty).
        '''

        if not isinstance(payload, dict):
            raise ValueError(f'depth payload must be a JSON object, got {type(payload).__name__}')

        data = payload['d']

        if not isinstance(data, dict):
            raise ValueError(f"depth payload 'd' must be a JSON object, got {type(data).__name__}")

        ts_ms = int(payload['t'])
        last_update_id = int(data['lastUpdateId'])
        bids = [(Decimal(p), Decimal(q)) for p, q in data['bids']]
        asks = [(Decimal(p), Decimal(q)) for p, q in data['asks']]

        return ts_ms, last_update_id, bids, asks
