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
# Minimum meaningful threshold: a counter that goes 0→1 on the
# first observation needs `>= 2` to allow at least one accept
# before the gate can trip, otherwise the very first poll
# rejects and the book never primes.
_MIN_STUCK_UPDATE_ID_POLLS = 2
# The hosted depth source serves exactly 20 levels per side
# (the regional Render collectors), and the magnitude
# floor name + env var both bake "TOP20" in to lock the operator's
# mental model to that width. If the gate width ever needs to
# change, the env var name, default constant, and class docstring
# all move together.
_TOP_20_LEVELS = 20
_HTTP_OK = 200


class DepthPoller:

    '''Poll authenticated Render top20 observations in the existing loop.

    Keep original exchange/receipt microseconds. The existing order-age gate uses
    the older source clock, so repeated HTTP delivery cannot refresh a cached book.
    A configured second region is tried after an unavailable or rejected response;
    the successful region remains first until it fails. Matching policy is unchanged.
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
        fallback_url: str = '',
        fallback_token: str = '',
        staleness_threshold_ms: int = 5000,
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

        if max_stuck_update_id_polls < _MIN_STUCK_UPDATE_ID_POLLS:
            raise ValueError(
                f'max_stuck_update_id_polls must be >= {_MIN_STUCK_UPDATE_ID_POLLS} '
                f'(baseline + one repeat), got {max_stuck_update_id_polls}'
            )

        if staleness_threshold_ms <= 0:
            raise ValueError('staleness_threshold_ms must be positive')

        if bool(fallback_url) != bool(fallback_token):
            raise ValueError('fallback_url and fallback_token must be configured together')

        self._book = book
        self._endpoints = [(url, token)] + ([(fallback_url, fallback_token)] if fallback_url else [])
        self._preferred = 0
        self._staleness_threshold_us = staleness_threshold_ms * 1000
        self.exchange_time_us = 0
        self.observed_at_us = 0
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

        for offset in range(len(self._endpoints)):
            index = (self._preferred + offset) % len(self._endpoints)
            url, token = self._endpoints[index]
            try:
                payload = await self._fetch(url, token)
                if self._accept_payload(payload):
                    self._preferred = index
                    return
            except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                if offset == len(self._endpoints) - 1:
                    raise
                _log.warning('depth region failed; trying peer', url=url, error_type=type(exc).__name__)

    async def _fetch(self, url: str, token: str) -> Any:
        assert self._session is not None
        headers = {'Authorization': f'Bearer {token}'}

        async with self._session.get(url, headers=headers) as response:
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

        return payload

    def _accept_payload(self, payload: Any) -> bool:
        exchange_us, observed_us, last_update_id, bids, asks = self._parse_payload(payload)
        now_us = int(time.time() * 1_000_000)
        if exchange_us > now_us or observed_us > now_us:
            raise ValueError('depth source clock is in the future')
        if now_us - min(exchange_us, observed_us) > self._staleness_threshold_us:
            raise ValueError('depth source clock is stale')
        ts_ms = exchange_us // 1000

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
        ask_depth = sum((qty for _, qty in asks[:_TOP_20_LEVELS]), Decimal('0'))
        bid_depth = sum((qty for _, qty in bids[:_TOP_20_LEVELS]), Decimal('0'))

        if ask_depth < self._min_top20_depth_btc or bid_depth < self._min_top20_depth_btc:
            _log.error(
                'depth poll rejected — top-N magnitude below floor',
                ask_top_n_qty=str(ask_depth),
                bid_top_n_qty=str(bid_depth),
                ask_levels_in_payload=len(asks),
                bid_levels_in_payload=len(bids),
                floor=str(self._min_top20_depth_btc),
                top_n=_TOP_20_LEVELS,
                last_update_id=last_update_id,
                ts_ms=ts_ms,
            )

            return False

        # Stuck-`last_update_id` detector: a real Binance depth-20
        # stream advances `lastUpdateId` on every diff. If the upstream
        # mirror serves the identical `lastUpdateId` across
        # `max_stuck_update_id_polls` consecutive polls (counting the
        # first observation as the first poll), its book is frozen
        # even if shape- and magnitude-valid. Reject the replace so
        # the staleness gate fires the next time the gate window
        # elapses. The else branch resets the counter to `1` — not
        # `0` — so a fresh id counts as observation 1 of itself and
        # `max_stuck_update_id_polls=N` means "reject on the Nth
        # consecutive identical poll", matching the operator's
        # natural reading of the env-var name.
        if last_update_id == self._previous_last_update_id:
            self._stuck_update_id_count += 1
        else:
            self._stuck_update_id_count = 1

        self._previous_last_update_id = last_update_id

        if self._stuck_update_id_count >= self._max_stuck_update_id_polls:
            _log.error(
                'depth poll rejected — last_update_id stuck across consecutive polls',
                last_update_id=last_update_id,
                stuck_count=self._stuck_update_id_count,
                threshold=self._max_stuck_update_id_polls,
                ts_ms=ts_ms,
            )

            return False

        self._book.replace(bids, asks, last_update_id, ts_ms)
        self.exchange_time_us = exchange_us
        self.observed_at_us = observed_us
        self._last_success_ts_ms = min(exchange_us, observed_us) // 1000

        # Per-poll success diagnostic: emit a single structured INFO
        # line every successful poll so operators can audit what
        # binsim served across time. Without this, a future
        # depth-source pathology produces only the resulting order
        # rejections in Praxis — the upstream cause is invisible.
        _log.info(
            'depth poll succeeded',
            ask_top_n_qty=str(ask_depth),
            bid_top_n_qty=str(bid_depth),
            ask_levels_in_payload=len(asks),
            bid_levels_in_payload=len(bids),
            best_ask_price=str(asks[0][0]),
            best_ask_qty=str(asks[0][1]),
            best_bid_price=str(bids[0][0]),
            best_bid_qty=str(bids[0][1]),
            last_update_id=last_update_id,
            ts_ms=ts_ms,
        )

        return True

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
    ) -> tuple[int, int, int, list[tuple[Decimal, Decimal]], list[tuple[Decimal, Decimal]]]:
        if not isinstance(payload, dict):
            raise ValueError(f'depth payload must be a JSON object, got {type(payload).__name__}')
        if payload['market'] != 'spot' or payload['symbol'] != 'BTCUSDT':
            raise ValueError('depth source must be BTCUSDT Spot')
        exchange_us, observed_us, update_id = (
            payload[name] for name in ('exchange_time', 'observed_at', 'update_id')
        )
        if any(type(value) is not int or value <= 0 for value in (exchange_us, observed_us, update_id)):
            raise ValueError('depth source clocks and update_id must be positive integers')
        bids = [(_finite_decimal(p, 'bid price'), _finite_decimal(q, 'bid qty')) for p, q in payload['bids']]
        asks = [(_finite_decimal(p, 'ask price'), _finite_decimal(q, 'ask qty')) for p, q in payload['asks']]
        if len(bids) != _TOP_20_LEVELS or len(asks) != _TOP_20_LEVELS:
            raise ValueError('depth source must carry twenty levels per side')
        return exchange_us, observed_us, update_id, bids, asks


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
