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
_DEFAULT_MIN_TOP20_DEPTH_BTC = Decimal('0.05')
_DEFAULT_MAX_STUCK_UPDATE_ID_POLLS = 5
_TOP_N_LEVELS = 20
_HTTP_OK = 200


class DepthPoller:

    '''Poll a hosted depth-N snapshot endpoint and feed an `OrderBook`.

    Owns a single `aiohttp.ClientSession` and a background poll task.
    On each successful poll the response is parsed and the bound
    `OrderBook` is replaced wholesale. Two timestamps come out of this:

      - `book.ts_ms` is set to the upstream `t` field — informational,
        useful for direct inspection / debugging / future metrics on
        the snapshot's source-side wall-clock.
      - `last_success_ts_ms` is set to local wall-clock
        (`int(time.time() * 1000)`) at receipt, NOT the upstream `t`.
        This is what the HTTP layer's staleness gate compares against;
        decoupling it from upstream-trusted data means a future-dated
        payload `t` (clock skew on the source, payload tampering) cannot
        silently make the book appear "newer than now" and bypass the
        gate.

    Failures (network, 5xx, malformed body, schema rejection) are
    logged and the loop continues at the same cadence — the staleness
    gate naturally surfaces persistent failure by observing
    `last_success_ts_ms` falling behind wall-clock.

    Beyond shape validation, two policy rejections also leave the book
    untouched and `last_success_ts_ms` unadvanced:

      - magnitude floor: a snapshot whose top-N depth on either side
        sums to less than `min_top20_depth_btc` is treated as
        pathological (truncated, cold-start, wrong-symbol, mirror-bug)
        and rejected. Real Binance BTCUSDT top-20 sits at multiple
        BTC per side; a sub-`0.05` BTC snapshot has historically
        meant a degraded upstream rather than a real market state.
      - stuck `lastUpdateId`: real Binance advances `lastUpdateId` on
        every diff, so an upstream that serves the identical id
        across `max_stuck_update_id_polls` consecutive polls has
        frozen even if shape- and magnitude-valid.

    Both rejection paths log at ERROR with the offending values, so a
    persistent upstream problem is louder than a flaky network and
    diagnosable from the binsim's own log surface.
    '''

    def __init__(
        self,
        book: OrderBook,
        url: str,
        token: str,
        poll_interval_ms: int = _DEFAULT_POLL_INTERVAL_MS,
        request_timeout_s: float = _DEFAULT_REQUEST_TIMEOUT_S,
        min_top20_depth_btc: Decimal = _DEFAULT_MIN_TOP20_DEPTH_BTC,
        max_stuck_update_id_polls: int = _DEFAULT_MAX_STUCK_UPDATE_ID_POLLS,
    ) -> None:

        if poll_interval_ms <= 0:
            raise ValueError(f'poll_interval_ms must be positive, got {poll_interval_ms}')

        if request_timeout_s <= 0:
            raise ValueError(f'request_timeout_s must be positive, got {request_timeout_s}')

        if not url:
            raise ValueError('url cannot be empty')

        if not token:
            raise ValueError('token cannot be empty')

        if not min_top20_depth_btc.is_finite() or min_top20_depth_btc <= 0:
            raise ValueError(
                f'min_top20_depth_btc must be a positive, finite Decimal, got {min_top20_depth_btc}'
            )

        if max_stuck_update_id_polls < 1:
            raise ValueError(
                f'max_stuck_update_id_polls must be >= 1, got {max_stuck_update_id_polls}'
            )

        self._book = book
        self._url = url
        self._token = token
        self._poll_interval_s = poll_interval_ms / 1000.0
        self._request_timeout = aiohttp.ClientTimeout(total=request_timeout_s)
        self._min_top20_depth_btc = min_top20_depth_btc
        self._max_stuck_update_id_polls = max_stuck_update_id_polls

        self._session: aiohttp.ClientSession | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._last_success_ts_ms = 0
        self._previous_last_update_id = 0
        self._stuck_update_id_count = 0

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

            # `content_type=None` skips aiohttp's Content-Type check so
            # a valid JSON body returned with a non-`application/json`
            # header parses normally. Shape validation happens in
            # `_parse_payload`, which surfaces malformed bodies at
            # ERROR (not WARNING) so a persistently broken upstream
            # is louder than a flaky network.
            payload = await response.json(content_type=None)

        ts_ms, last_update_id, bids, asks = self._parse_payload(payload)

        # Magnitude floor: an upstream snapshot whose top-N depth on
        # either side sums to less than `min_top20_depth_btc` is
        # treated as pathological (truncated, cold-start, wrong-symbol,
        # mirror-bug) and rejected without mutating the book or
        # `_last_success_ts_ms`. The HTTP staleness gate (in
        # `server._submit_order`) will fire after its threshold and
        # surface the upstream problem as `-1003` rejections, instead
        # of binsim walking a thin garbage book and producing a burst
        # of `insufficient book liquidity` rejections that look like
        # market signal to the health evaluator.
        ask_depth = sum((qty for _, qty in asks[:_TOP_N_LEVELS]), Decimal('0'))
        bid_depth = sum((qty for _, qty in bids[:_TOP_N_LEVELS]), Decimal('0'))

        if ask_depth < self._min_top20_depth_btc or bid_depth < self._min_top20_depth_btc:
            _log.error(
                'depth poll rejected — top-N magnitude below floor',
                ask_top_n_qty=str(ask_depth),
                bid_top_n_qty=str(bid_depth),
                floor=str(self._min_top20_depth_btc),
                top_n=_TOP_N_LEVELS,
                last_update_id=last_update_id,
                ts_ms=ts_ms,
            )

            return

        # Stuck-`last_update_id` detector: a real Binance depth-20
        # stream advances `lastUpdateId` on every diff. If the upstream
        # mirror serves the identical `lastUpdateId` across
        # `max_stuck_update_id_polls` consecutive polls, its book is
        # frozen even if shape- and magnitude-valid. Reject the
        # replace so the staleness gate fires the next time the gate
        # window elapses. The counter is updated unconditionally so a
        # poll arriving with a fresh id resets the suspicion.
        if last_update_id == self._previous_last_update_id:
            self._stuck_update_id_count += 1
        else:
            self._stuck_update_id_count = 0

        self._previous_last_update_id = last_update_id

        if self._stuck_update_id_count >= self._max_stuck_update_id_polls:
            _log.error(
                'depth poll rejected — last_update_id stuck across consecutive polls',
                last_update_id=last_update_id,
                stuck_count=self._stuck_update_id_count,
                threshold=self._max_stuck_update_id_polls,
                ts_ms=ts_ms,
            )

            return

        self._book.replace(bids, asks, last_update_id, ts_ms)
        # Record local wall-clock at receipt, NOT the upstream `t`.
        # The HTTP layer's staleness gate compares this against its
        # own `time.time()`; if we trusted upstream `t` directly, a
        # future-dated `t` (clock skew on the source, payload tampering)
        # would silently make the book appear "newer than now" and the
        # gate's `age_ms > threshold` check would pass forever.
        # `book.ts_ms` retains the upstream `t` as an informational
        # property on `OrderBook` (for direct operator inspection /
        # debugging / future metrics). Real Binance's `/api/v3/depth`
        # response does not carry a timestamp, so the binsim's depth
        # endpoint deliberately omits it too to keep the shape
        # exactly Binance-compatible.
        self._last_success_ts_ms = int(time.time() * 1000)

        # Per-poll success diagnostic: emit a single structured INFO
        # line every successful poll so operators can audit what
        # binsim served across time. Without this, a future
        # depth-source pathology produces only the resulting order
        # rejections in Praxis — the upstream cause is invisible.
        _log.info(
            'depth poll succeeded',
            ask_top_n_qty=str(ask_depth),
            bid_top_n_qty=str(bid_depth),
            best_ask_price=str(asks[0][0]),
            best_ask_qty=str(asks[0][1]),
            best_bid_price=str(bids[0][0]),
            best_bid_qty=str(bids[0][1]),
            last_update_id=last_update_id,
            ts_ms=ts_ms,
        )

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
            ValueError: payload (or its `d` sub-object) is not a dict,
                or a price/qty parses to a non-finite Decimal (NaN /
                Infinity slip through the bare `Decimal(...)` parse).
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
        bids = [(_finite_decimal(p, 'bid price'), _finite_decimal(q, 'bid qty')) for p, q in data['bids']]
        asks = [(_finite_decimal(p, 'ask price'), _finite_decimal(q, 'ask qty')) for p, q in data['asks']]

        return ts_ms, last_update_id, bids, asks


def _finite_decimal(raw: object, what: str) -> Decimal:

    '''Parse `raw` to a finite `Decimal`. NaN / Infinity raise ValueError.

    Bare `Decimal('NaN')` and `Decimal('Infinity')` are valid Decimal
    values that do NOT raise `InvalidOperation`, but every downstream
    comparison (`<= 0`, `> threshold`) silently returns False for NaN
    and unpredictably for Infinity. Reject at the parse boundary so
    these never leak into `OrderBook.replace` or further math.
    '''

    value = Decimal(raw if isinstance(raw, (str, int)) else str(raw))

    if not value.is_finite():
        raise ValueError(f'{what} must be a finite decimal, got {raw!r}')

    return value
