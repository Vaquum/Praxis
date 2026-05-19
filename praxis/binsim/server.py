'''aiohttp server that exposes the binsim's REST surface.'''

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final

from aiohttp import web

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import (
    DuplicateClientOrderIdError,
    InsufficientBalanceError,
    Ledger,
)
from praxis.core.domain.enums import OrderSide
from praxis.infrastructure.observability import get_logger


__all__ = [
    'API_KEYS_KEY',
    'BOOK_KEY',
    'LEDGER_KEY',
    'POLLER_KEY',
    'STALENESS_THRESHOLD_MS_KEY',
    'WS_SUBSCRIPTION_COUNTER_KEY',
    'BinsimServer',
    'make_app',
]


_log = get_logger(__name__)

BOOK_KEY: web.AppKey[OrderBook] = web.AppKey('binsim.book', OrderBook)
LEDGER_KEY: web.AppKey[Ledger] = web.AppKey('binsim.ledger', Ledger)
POLLER_KEY: web.AppKey[DepthPoller] = web.AppKey('binsim.poller', DepthPoller)
STALENESS_THRESHOLD_MS_KEY: web.AppKey[int] = web.AppKey(
    'binsim.staleness_threshold_ms', int,
)
API_KEYS_KEY: web.AppKey[Mapping[str, str]] = web.AppKey(
    'binsim.api_keys', Mapping[str, str],
)


@dataclass
class _WsSubscriptionCounter:

    '''Monotonic per-process counter for WS-API subscription IDs.

    Praxis's `BinanceWS._clean_setup_connection` rejects an ack whose
    `subscriptionId` is not a real `int`, so we hand out distinct
    integers per `userDataStream.subscribe.signature` call. IDs reset
    on restart — Binance itself makes no cross-reconnect promise, and
    the client treats every subscribe as a fresh handshake.
    '''

    next_id: int = 1

    def take(self) -> int:

        value = self.next_id
        self.next_id += 1

        return value


WS_SUBSCRIPTION_COUNTER_KEY: web.AppKey[_WsSubscriptionCounter] = web.AppKey(
    'binsim.ws_subscription_counter', _WsSubscriptionCounter,
)

_MAX_PORT = 65535
_DEFAULT_DEPTH_LIMIT = 100
_MAX_DEPTH_LIMIT = 5000

_TAKER_FEE_RATE: Final[Decimal] = Decimal('0.001')

_HTTP_BAD_REQUEST = 400
_HTTP_SERVICE_UNAVAILABLE = 503

_BINANCE_CODE_BOOK_STALE = -1003
_BINANCE_CODE_BAD_REQUEST = -1100
_BINANCE_CODE_UNKNOWN_SYMBOL = -1121
_BINANCE_CODE_ORDER_REJECTED = -2010
_BINANCE_CODE_NO_SUCH_ORDER = -2013

_VALID_SIDES = ('BUY', 'SELL')
_VALID_TYPES = ('MARKET',)

_WS_HEARTBEAT_SECONDS = 180.0
_WS_OK_STATUS = 200
_WS_UNAUTHORIZED_STATUS = 401
_WS_BAD_REQUEST_STATUS = 400
_WS_BINANCE_CODE_BAD_SIG = -1022
_WS_BINANCE_CODE_BAD_API_KEY = -2014
_WS_METHOD_SUBSCRIBE = 'userDataStream.subscribe.signature'

_SYMBOL: Final[str] = 'BTCUSDT'
_BASE_ASSET: Final[str] = 'BTC'
_QUOTE_ASSET: Final[str] = 'USDT'

_FILTERS_PAYLOAD: Final[dict[str, object]] = {
    'symbol': _SYMBOL,
    'status': 'TRADING',
    'baseAsset': _BASE_ASSET,
    'quoteAsset': _QUOTE_ASSET,
    'filters': [
        {'filterType': 'PRICE_FILTER', 'tickSize': '0.01000000'},
        {
            'filterType': 'LOT_SIZE',
            'stepSize': '0.00001000',
            'minQty': '0.00001000',
            'maxQty': '9000.00000000',
        },
        {'filterType': 'NOTIONAL', 'minNotional': '5.00000000'},
    ],
}

_EXCHANGE_INFO_PAYLOAD: Final[dict[str, object]] = {
    'timezone': 'UTC',
    'symbols': [_FILTERS_PAYLOAD],
}


def make_app(
    book: OrderBook,
    ledger: Ledger,
    poller: DepthPoller,
    staleness_threshold_ms: int,
    api_keys: Mapping[str, str],
) -> web.Application:

    '''Build the aiohttp application with all binsim routes wired.

    The deps are stored on the application instance (`app[<key>]`) so
    request handlers can fetch them via `request.app[<key>]` without
    relying on module-level state. This keeps the server testable —
    tests construct an app with whatever combination of real and stub
    components they want.

    `api_keys` maps an `X-MBX-APIKEY` header value to the binsim
    account_id it controls. Signed endpoints reject requests with an
    unknown key.
    '''

    if staleness_threshold_ms <= 0:
        raise ValueError(
            f'staleness_threshold_ms must be positive, got {staleness_threshold_ms}'
        )

    app = web.Application()
    app[BOOK_KEY] = book
    app[LEDGER_KEY] = ledger
    app[POLLER_KEY] = poller
    app[STALENESS_THRESHOLD_MS_KEY] = staleness_threshold_ms
    app[API_KEYS_KEY] = api_keys
    app[WS_SUBSCRIPTION_COUNTER_KEY] = _WsSubscriptionCounter()

    app.add_routes([
        web.get('/healthz', _healthz),
        web.get('/api/v3/time', _time),
        web.get('/api/v3/exchangeInfo', _exchange_info),
        web.get('/api/v3/depth', _depth),
        web.get('/api/v3/account', _account),
        web.get('/api/v3/order', _order_stub),
        web.get('/api/v3/openOrders', _open_orders_stub),
        web.get('/api/v3/myTrades', _my_trades_stub),
        web.post('/api/v3/order', _submit_order),
        web.get('/ws-api/v3', _ws_api),
        web.get('/stream', _ws_stream),
    ])

    return app


async def _healthz(request: web.Request) -> web.Response:

    del request

    return web.json_response({'status': 'ok'})


async def _time(request: web.Request) -> web.Response:

    del request

    return web.json_response({'serverTime': int(time.time() * 1000)})


async def _exchange_info(request: web.Request) -> web.Response:

    del request

    return web.json_response(_EXCHANGE_INFO_PAYLOAD)


async def _depth(request: web.Request) -> web.Response:

    symbol = request.query.get('symbol')

    if symbol is None:
        raise web.HTTPBadRequest(reason='missing symbol query param')

    if symbol != _SYMBOL:
        raise web.HTTPBadRequest(reason=f'unsupported symbol: {symbol!r}')

    limit = _parse_depth_limit(request.query.get('limit'))
    book = request.app[BOOK_KEY]

    bids = [[str(p), str(q)] for p, q in book.bids[:limit]]
    asks = [[str(p), str(q)] for p, q in book.asks[:limit]]

    return web.json_response({
        'bids': bids,
        'asks': asks,
        'lastUpdateId': book.last_update_id,
    })


async def _account(request: web.Request) -> web.Response:

    account_id = _require_signed_caller(request)
    ledger = request.app[LEDGER_KEY]

    try:
        usdt, btc = await ledger.balance(account_id)
    except KeyError as exc:
        raise web.HTTPUnauthorized(reason=f'unknown account: {account_id}') from exc

    return web.json_response({
        'balances': [
            {'asset': _QUOTE_ASSET, 'free': str(usdt), 'locked': '0'},
            {'asset': _BASE_ASSET, 'free': str(btc), 'locked': '0'},
        ],
    })


async def _order_stub(request: web.Request) -> web.Response:

    _require_signed_caller(request)

    body = json.dumps({
        'code': _BINANCE_CODE_NO_SUCH_ORDER,
        'msg': 'Order does not exist (binsim does not retain non-terminal orders).',
    })
    raise web.HTTPNotFound(text=body, content_type='application/json')


async def _open_orders_stub(request: web.Request) -> web.Response:

    _require_signed_caller(request)

    return web.json_response([])


async def _my_trades_stub(request: web.Request) -> web.Response:

    _require_signed_caller(request)

    return web.json_response([])


async def _submit_order(request: web.Request) -> web.Response:

    '''Handle `POST /api/v3/order` — the binsim's hot path.

    Flow: HMAC presence → staleness gate → param validation →
    book walk → ledger settle → Binance-shaped FULL response.

    Errors are returned as Binance-shaped `{code, msg}` bodies with
    HTTP status the adapter's `_raise_on_error` recognises:
    503 → `TransientError` (book stale), 400 → `OrderRejectedError`
    (rejected for any other reason).
    '''

    account_id = _require_signed_caller(request)
    poller = request.app[POLLER_KEY]
    threshold_ms = request.app[STALENESS_THRESHOLD_MS_KEY]
    book = request.app[BOOK_KEY]
    ledger = request.app[LEDGER_KEY]

    now_ms = int(time.time() * 1000)
    age_ms = now_ms - poller.last_success_ts_ms

    if poller.last_success_ts_ms == 0 or age_ms > threshold_ms:
        raise _binance_error(
            status=_HTTP_SERVICE_UNAVAILABLE, code=_BINANCE_CODE_BOOK_STALE,
            msg=f'book is stale (age {age_ms}ms exceeds threshold {threshold_ms}ms)',
        )

    symbol = request.query.get('symbol')
    side_raw = request.query.get('side')
    type_raw = request.query.get('type')
    qty_raw = request.query.get('quantity')
    client_order_id = request.query.get('newClientOrderId')

    if symbol != _SYMBOL:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_UNKNOWN_SYMBOL,
            msg=f'unsupported symbol: {symbol!r}',
        )

    if side_raw not in _VALID_SIDES:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_BAD_REQUEST,
            msg=f'invalid side: {side_raw!r}',
        )

    if type_raw not in _VALID_TYPES:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_BAD_REQUEST,
            msg=f'unsupported order type for binsim MMVP: {type_raw!r} (only MARKET)',
        )

    if not client_order_id:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_BAD_REQUEST,
            msg='missing newClientOrderId',
        )

    qty = _parse_decimal_param(qty_raw, 'quantity')

    if qty <= 0:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_BAD_REQUEST,
            msg=f'quantity must be positive, got {qty_raw!r}',
        )

    side = OrderSide(side_raw)

    try:
        walk = book.consume_qty_for_market_order(side, qty)
    except RuntimeError as exc:
        raise _binance_error(
            status=_HTTP_SERVICE_UNAVAILABLE, code=_BINANCE_CODE_BOOK_STALE,
            msg=f'order book not initialised: {exc}',
        ) from exc

    filled_qty = sum((q for _, q in walk), Decimal('0'))

    if filled_qty < qty:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_ORDER_REJECTED,
            msg=(
                f'insufficient book liquidity: requested {qty}, visible {filled_qty} '
                f'across {len(walk)} levels'
            ),
        )

    fills_with_fees = [
        (price, level_qty, level_qty * price * _TAKER_FEE_RATE)
        for price, level_qty in walk
    ]

    try:
        order_id, records = await ledger.apply_order(
            account_id, side, fills_with_fees,
            client_order_id=client_order_id,
        )
    except DuplicateClientOrderIdError as exc:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_ORDER_REJECTED,
            msg=f'duplicate newClientOrderId: {client_order_id!r}',
        ) from exc
    except InsufficientBalanceError as exc:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_ORDER_REJECTED,
            msg=f'account has insufficient balance: {exc}',
        ) from exc

    cumulative_quote = sum((price * level_qty for price, level_qty, _ in fills_with_fees), Decimal('0'))

    return web.json_response({
        'symbol': _SYMBOL,
        'orderId': order_id,
        'orderListId': -1,
        'clientOrderId': client_order_id,
        'transactTime': now_ms,
        'price': '0.00000000',
        'origQty': str(qty),
        'executedQty': str(filled_qty),
        'cummulativeQuoteQty': str(cumulative_quote),
        'status': 'FILLED',
        'timeInForce': 'GTC',
        'type': 'MARKET',
        'side': side.value,
        'fills': [
            {
                'tradeId': int(record.trade_id),
                'price': str(record.price),
                'qty': str(record.qty),
                'commission': str(record.fee),
                'commissionAsset': record.fee_asset,
            }
            for record in records
        ],
    })


def _parse_decimal_param(raw: str | None, name: str) -> Decimal:

    if raw is None:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_BAD_REQUEST,
            msg=f'missing {name}',
        )

    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise _binance_error(
            status=_HTTP_BAD_REQUEST, code=_BINANCE_CODE_BAD_REQUEST,
            msg=f'{name} is not a valid decimal: {raw!r}',
        ) from exc


def _binance_error(status: int, code: int, msg: str) -> web.HTTPException:

    '''Build a Binance-shaped `{code, msg}` HTTP error.

    Praxis's `BinanceAdapter._raise_on_error` reads `body['code']` +
    `body['msg']` from 4xx responses and raises `OrderRejectedError`
    with the venue_code preserved. 5xx responses are mapped to
    `TransientError` regardless of body.
    '''

    body = json.dumps({'code': code, 'msg': msg})

    if status == _HTTP_BAD_REQUEST:
        return web.HTTPBadRequest(text=body, content_type='application/json')

    if status == _HTTP_SERVICE_UNAVAILABLE:
        return web.HTTPServiceUnavailable(text=body, content_type='application/json')

    raise ValueError(f'unsupported binance-error status: {status}')


def _parse_depth_limit(raw: str | None) -> int:

    if raw is None:
        return _DEFAULT_DEPTH_LIMIT

    try:
        limit = int(raw)
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=f'limit must be an integer, got {raw!r}') from exc

    if limit <= 0 or limit > _MAX_DEPTH_LIMIT:
        raise web.HTTPBadRequest(reason=f'limit must be in 1..{_MAX_DEPTH_LIMIT}, got {limit}')

    return limit


def _require_signed_caller(request: web.Request) -> str:

    '''Resolve the calling account_id from a signed request.

    Per the issue's MMVP spec, the binsim does a presence check on
    `X-MBX-APIKEY` + the `signature` query param rather than a full
    HMAC verify. The api_key is then resolved against the registered
    mapping to obtain the account_id.

    Raises:
        web.HTTPUnauthorized: header or signature missing, or key not
            registered.
    '''

    api_key = request.headers.get('X-MBX-APIKEY')

    if not api_key:
        raise web.HTTPUnauthorized(reason='missing X-MBX-APIKEY header')

    if 'signature' not in request.query:
        raise web.HTTPUnauthorized(reason='missing signature query param')

    api_keys = request.app[API_KEYS_KEY]
    account_id = api_keys.get(api_key)

    if account_id is None:
        raise web.HTTPUnauthorized(reason='unknown API key')

    return account_id


async def _ws_api(request: web.Request) -> web.WebSocketResponse:

    '''Handle the WS-API user-data stream.

    Praxis's `BinanceWS._clean_setup_connection` opens this connection
    at launcher start, sends one `userDataStream.subscribe.signature`
    frame, and refuses to start if the ack is missing or malformed.
    The binsim MMVP path satisfies that handshake and then sits idle —
    fills come back inline from `POST /api/v3/order`, so there is
    nothing to push.

    Heartbeat: aiohttp sends a PING every `_WS_HEARTBEAT_SECONDS` and
    closes the connection if no PONG arrives within the same window.
    Binance idles the connection after a few minutes of silence, so
    we mirror the keepalive cadence.
    '''

    api_keys = request.app[API_KEYS_KEY]
    counter = request.app[WS_SUBSCRIPTION_COUNTER_KEY]

    ws = web.WebSocketResponse(heartbeat=_WS_HEARTBEAT_SECONDS)
    await ws.prepare(request)

    async for msg in ws:
        if msg.type != web.WSMsgType.TEXT:
            continue

        await _handle_ws_api_frame(ws, msg.data, api_keys, counter)

    return ws


async def _handle_ws_api_frame(
    ws: web.WebSocketResponse,
    data: str,
    api_keys: Mapping[str, str],
    counter: _WsSubscriptionCounter,
) -> None:

    try:
        request_obj = json.loads(data)
    except json.JSONDecodeError:
        return

    if not isinstance(request_obj, dict):
        return

    req_id = request_obj.get('id', '')
    method = request_obj.get('method')

    if method != _WS_METHOD_SUBSCRIBE:
        await ws.send_str(json.dumps({
            'id': req_id,
            'status': _WS_BAD_REQUEST_STATUS,
            'error': {
                'code': _BINANCE_CODE_BAD_REQUEST,
                'msg': f'unsupported method: {method!r}',
            },
        }))

        return

    params = request_obj.get('params') or {}
    api_key = params.get('apiKey') if isinstance(params, dict) else None
    signature = params.get('signature') if isinstance(params, dict) else None

    if not api_key or not signature:
        await ws.send_str(json.dumps({
            'id': req_id,
            'status': _WS_UNAUTHORIZED_STATUS,
            'error': {
                'code': _WS_BINANCE_CODE_BAD_SIG,
                'msg': 'missing apiKey or signature',
            },
        }))

        return

    if api_key not in api_keys:
        await ws.send_str(json.dumps({
            'id': req_id,
            'status': _WS_UNAUTHORIZED_STATUS,
            'error': {
                'code': _WS_BINANCE_CODE_BAD_API_KEY,
                'msg': 'unknown apiKey',
            },
        }))

        return

    sub_id = counter.take()

    await ws.send_str(json.dumps({
        'id': req_id,
        'status': _WS_OK_STATUS,
        'result': {'subscriptionId': sub_id},
    }))


async def _ws_stream(request: web.Request) -> web.WebSocketResponse:

    '''Accept the market-data stream connection and idle.

    Binance's `wss://stream.binance.com:9443/stream` ships diff
    snapshots, depth updates, klines etc. The binsim does not need
    any of that — its `OrderBook` is poll-driven from a separate
    hosted source. We accept the connect so client code does not
    explode trying to open it, drain any incoming frames (the client
    may send subscribe/unsubscribe lifecycle messages it expects
    silently ignored), and close when the client closes.
    '''

    ws = web.WebSocketResponse(heartbeat=_WS_HEARTBEAT_SECONDS)
    await ws.prepare(request)

    async for msg in ws:
        if msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.ERROR):
            break

    return ws


class BinsimServer:

    '''Lifecycle wrapper around the binsim aiohttp app.

    Owns the `AppRunner` + `TCPSite` so the launcher can call
    `start()` / `stop()` without touching aiohttp internals. The app
    itself is built via `make_app()` and is also exposed as
    `BinsimServer.app` for in-process callers (e.g. tests using
    `aiohttp.test_utils.TestClient`).
    '''

    def __init__(
        self,
        host: str,
        port: int,
        book: OrderBook,
        ledger: Ledger,
        poller: DepthPoller,
        staleness_threshold_ms: int,
        api_keys: Mapping[str, str],
    ) -> None:

        if not host:
            raise ValueError('host cannot be empty')

        if port < 0 or port > _MAX_PORT:
            raise ValueError(f'port must be in 0..{_MAX_PORT}, got {port}')

        self._host = host
        self._port = port
        self._app = make_app(book, ledger, poller, staleness_threshold_ms, api_keys)
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def app(self) -> web.Application:

        return self._app

    @property
    def is_running(self) -> bool:

        return self._site is not None

    async def start(self) -> None:

        if self.is_running:
            raise RuntimeError('BinsimServer already running')

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

    async def stop(self) -> None:

        if self._site is not None:
            await self._site.stop()
            self._site = None

        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
