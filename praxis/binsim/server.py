'''aiohttp server that exposes the binsim's REST surface.'''

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Final

from aiohttp import web

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import Ledger
from praxis.infrastructure.observability import get_logger


__all__ = [
    'API_KEYS_KEY',
    'BOOK_KEY',
    'LEDGER_KEY',
    'POLLER_KEY',
    'STALENESS_THRESHOLD_MS_KEY',
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

_MAX_PORT = 65535
_DEFAULT_DEPTH_LIMIT = 100
_MAX_DEPTH_LIMIT = 5000

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

    app.add_routes([
        web.get('/healthz', _healthz),
        web.get('/api/v3/time', _time),
        web.get('/api/v3/exchangeInfo', _exchange_info),
        web.get('/api/v3/depth', _depth),
        web.get('/api/v3/account', _account),
        web.get('/api/v3/order', _order_stub),
        web.get('/api/v3/openOrders', _open_orders_stub),
        web.get('/api/v3/myTrades', _my_trades_stub),
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

    raise web.HTTPNotFound(reason='order lookup not supported by binsim')


async def _open_orders_stub(request: web.Request) -> web.Response:

    _require_signed_caller(request)

    return web.json_response([])


async def _my_trades_stub(request: web.Request) -> web.Response:

    _require_signed_caller(request)

    return web.json_response([])


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
