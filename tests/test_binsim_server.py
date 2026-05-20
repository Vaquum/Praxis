'''Tests for praxis.binsim.server.BinsimServer + make_app.'''

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import Ledger
from praxis.binsim.server import (
    BOOK_KEY,
    LEDGER_KEY,
    POLLER_KEY,
    STALENESS_THRESHOLD_MS_KEY,
    BinsimServer,
    make_app,
)


_URL = 'https://binance-spot-depth20-1000ms.onrender.com/top20'
_TOKEN = 'test-token'  # noqa: S105 — test fixture, not a real credential
_THRESHOLD_MS = 5000

_ACCOUNT_ID = 'acc-1'
_SIGNATURE_PARAMS = {'signature': 'deadbeef'}

_BIDS = [
    (Decimal('100.00'), Decimal('1.0')),
    (Decimal('99.50'), Decimal('2.0')),
    (Decimal('99.00'), Decimal('3.0')),
]
_ASKS = [
    (Decimal('101.00'), Decimal('1.0')),
    (Decimal('101.50'), Decimal('2.0')),
    (Decimal('102.00'), Decimal('3.0')),
]
_UID = 12345
_TS = 1_700_000_000_000


def _seeded_book() -> OrderBook:

    book = OrderBook()
    book.replace(_BIDS, _ASKS, _UID, _TS)

    return book


def _make_components(tmp_path: Path) -> tuple[OrderBook, Ledger, DepthPoller]:

    book = _seeded_book()
    ledger = Ledger(tmp_path)
    poller = DepthPoller(book, _URL, _TOKEN)

    return book, ledger, poller


async def _make_client(
    tmp_path: Path,
) -> tuple[TestClient, OrderBook, Ledger, DepthPoller, dict[str, str]]:

    book, ledger, poller = _make_components(tmp_path)
    api_key = await ledger.register_account(_ACCOUNT_ID, Decimal('10000'), Decimal('0.5'))

    app = make_app(book, ledger, poller, _THRESHOLD_MS)
    client = TestClient(TestServer(app))
    await client.start_server()

    signed_headers = {'X-MBX-APIKEY': api_key}

    return client, book, ledger, poller, signed_headers


@pytest.mark.parametrize('threshold', [0, -1, -1000])
def test_make_app_rejects_non_positive_threshold(tmp_path: Path, threshold: int) -> None:

    book, ledger, poller = _make_components(tmp_path)

    with pytest.raises(ValueError, match='staleness_threshold_ms must be positive'):
        make_app(book, ledger, poller, threshold)


@pytest.mark.asyncio
async def test_healthz_returns_status_ok(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/healthz')
        assert resp.status == 200
        assert await resp.json() == {'status': 'ok'}
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_time_returns_unix_ms(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/time')
        assert resp.status == 200

        payload = await resp.json()
        assert isinstance(payload['serverTime'], int)
        assert payload['serverTime'] > 1_700_000_000_000
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_exchange_info_returns_btcusdt_filters(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/exchangeInfo')
        assert resp.status == 200

        payload = await resp.json()
        symbols = payload['symbols']
        assert len(symbols) == 1
        assert symbols[0]['symbol'] == 'BTCUSDT'

        filters = {f['filterType']: f for f in symbols[0]['filters']}
        assert filters['PRICE_FILTER']['tickSize'] == '0.01000000'
        assert filters['LOT_SIZE']['stepSize'] == '0.00001000'
        assert filters['LOT_SIZE']['minQty'] == '0.00001000'
        assert filters['LOT_SIZE']['maxQty'] == '9000.00000000'
        assert filters['NOTIONAL']['minNotional'] == '5.00000000'
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_depth_returns_book_snapshot(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/depth', params={'symbol': 'BTCUSDT'})
        assert resp.status == 200

        payload = await resp.json()
        assert payload['lastUpdateId'] == _UID
        assert payload['bids'] == [
            ['100.00', '1.0'],
            ['99.50', '2.0'],
            ['99.00', '3.0'],
        ]
        assert payload['asks'] == [
            ['101.00', '1.0'],
            ['101.50', '2.0'],
            ['102.00', '3.0'],
        ]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_depth_truncates_to_limit(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/depth', params={'symbol': 'BTCUSDT', 'limit': '2'})
        assert resp.status == 200

        payload = await resp.json()
        assert len(payload['bids']) == 2
        assert len(payload['asks']) == 2
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_depth_rejects_missing_symbol(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/depth')
        assert resp.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_depth_rejects_unsupported_symbol(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/depth', params={'symbol': 'ETHUSDT'})
        assert resp.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('bad_limit', ['0', '-1', '5001', 'abc'])
async def test_depth_rejects_invalid_limit(tmp_path: Path, bad_limit: str) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/depth', params={'symbol': 'BTCUSDT', 'limit': bad_limit})
        assert resp.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_returns_balances_in_binance_shape(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.get(
            '/api/v3/account',
            headers=signed_headers,
            params=_SIGNATURE_PARAMS,
        )
        assert resp.status == 200

        payload = await resp.json()
        balances = {b['asset']: b for b in payload['balances']}
        assert balances['USDT']['free'] == '10000'
        assert balances['USDT']['locked'] == '0'
        assert balances['BTC']['free'] == '0.5'
        assert balances['BTC']['locked'] == '0'
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_reflects_post_fill_balances(tmp_path: Path) -> None:

    client, _, ledger, _, signed_headers = await _make_client(tmp_path)

    try:
        from praxis.core.domain.enums import OrderSide
        await ledger.apply_fill(
            _ACCOUNT_ID, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0.01'),
        )

        resp = await client.get(
            '/api/v3/account',
            headers=signed_headers,
            params=_SIGNATURE_PARAMS,
        )
        payload = await resp.json()
        balances = {b['asset']: b for b in payload['balances']}
        assert Decimal(balances['USDT']['free']) == Decimal('10000') - Decimal('10') - Decimal('0.01')
        assert Decimal(balances['BTC']['free']) == Decimal('0.6')
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_rejects_missing_api_key(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/account', params=_SIGNATURE_PARAMS)
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_rejects_missing_signature(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/account', headers=signed_headers)
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_rejects_unknown_api_key(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get(
            '/api/v3/account',
            headers={'X-MBX-APIKEY': 'apikey-not-registered'},
            params=_SIGNATURE_PARAMS,
        )
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_order_get_stub_returns_404(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.get(
            '/api/v3/order',
            headers=signed_headers,
            params={'symbol': 'BTCUSDT', 'signature': 'x'},
        )
        assert resp.status == 404
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_order_get_stub_still_enforces_signed_caller(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/order', params={'symbol': 'BTCUSDT'})
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_open_orders_stub_returns_empty_list(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.get(
            '/api/v3/openOrders',
            headers=signed_headers,
            params={'symbol': 'BTCUSDT', 'signature': 'x'},
        )
        assert resp.status == 200
        assert await resp.json() == []
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_my_trades_stub_returns_empty_list(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.get(
            '/api/v3/myTrades',
            headers=signed_headers,
            params={'symbol': 'BTCUSDT', 'signature': 'x'},
        )
        assert resp.status == 200
        assert await resp.json() == []
    finally:
        await client.close()


def test_constructor_rejects_empty_host(tmp_path: Path) -> None:

    book, ledger, poller = _make_components(tmp_path)

    with pytest.raises(ValueError, match='host cannot be empty'):
        BinsimServer('', 8080, book, ledger, poller, _THRESHOLD_MS)


@pytest.mark.parametrize('port', [-1, 65536, 100_000])
def test_constructor_rejects_invalid_port(tmp_path: Path, port: int) -> None:

    book, ledger, poller = _make_components(tmp_path)

    with pytest.raises(ValueError, match=r'port must be in 0\.\.65535'):
        BinsimServer('127.0.0.1', port, book, ledger, poller, _THRESHOLD_MS)


def test_constructor_accepts_port_zero_for_ephemeral_binding(tmp_path: Path) -> None:

    book, ledger, poller = _make_components(tmp_path)
    server = BinsimServer('127.0.0.1', 0, book, ledger, poller, _THRESHOLD_MS)

    assert server is not None


@pytest.mark.asyncio
async def test_server_start_stop_lifecycle(tmp_path: Path) -> None:

    book, ledger, poller = _make_components(tmp_path)
    server = BinsimServer('127.0.0.1', 0, book, ledger, poller, _THRESHOLD_MS)

    assert server.is_running is False

    await server.start()

    try:
        assert server.is_running is True
    finally:
        await server.stop()

    assert server.is_running is False


@pytest.mark.asyncio
async def test_server_start_twice_raises(tmp_path: Path) -> None:

    book, ledger, poller = _make_components(tmp_path)
    server = BinsimServer('127.0.0.1', 0, book, ledger, poller, _THRESHOLD_MS)
    await server.start()

    try:
        with pytest.raises(RuntimeError, match='already running'):
            await server.start()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_server_stop_is_idempotent(tmp_path: Path) -> None:

    book, ledger, poller = _make_components(tmp_path)
    server = BinsimServer('127.0.0.1', 0, book, ledger, poller, _THRESHOLD_MS)
    await server.start()
    await server.stop()
    await server.stop()

    assert server.is_running is False


@pytest.mark.asyncio
async def test_server_app_is_accessible(tmp_path: Path) -> None:

    book, ledger, poller = _make_components(tmp_path)
    server = BinsimServer('127.0.0.1', 0, book, ledger, poller, _THRESHOLD_MS)

    assert server.app is not None
    assert server.app[BOOK_KEY] is book
    assert server.app[LEDGER_KEY] is ledger
    assert server.app[POLLER_KEY] is poller
    assert server.app[STALENESS_THRESHOLD_MS_KEY] == _THRESHOLD_MS


async def _make_client_with_fresh_book(
    tmp_path: Path,
    book_ts_ms: int | None = None,
) -> tuple[TestClient, OrderBook, Ledger, DepthPoller, dict[str, str]]:

    client, book, ledger, poller, signed_headers = await _make_client(tmp_path)

    if book_ts_ms is None:
        import time as _t
        book_ts_ms = int(_t.time() * 1000)

    poller._last_success_ts_ms = book_ts_ms

    return client, book, ledger, poller, signed_headers


_POST_BASE_PARAMS = {
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'MARKET',
    'quantity': '0.5',
    'newClientOrderId': 'cid-1',
    'signature': 'deadbeef',
}


@pytest.mark.asyncio
async def test_post_order_buy_fills_walks_book_returns_fills(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        resp = await client.post(
            '/api/v3/order',
            headers=signed_headers,
            params=_POST_BASE_PARAMS,
        )
        assert resp.status == 200

        payload = await resp.json()
        assert payload['symbol'] == 'BTCUSDT'
        assert payload['status'] == 'FILLED'
        assert payload['side'] == 'BUY'
        assert payload['type'] == 'MARKET'
        assert payload['clientOrderId'] == 'cid-1'
        assert isinstance(payload['orderId'], int)
        assert payload['executedQty'] == '0.5'

        fills = payload['fills']
        assert len(fills) == 1
        assert fills[0]['price'] == '101.00'
        assert fills[0]['qty'] == '0.5'
        assert fills[0]['commissionAsset'] == 'USDT'
        assert Decimal(fills[0]['commission']) == Decimal('101.00') * Decimal('0.5') * Decimal('0.001')
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_walks_multiple_levels(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': '4.5'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 200

        payload = await resp.json()
        fills = payload['fills']
        assert len(fills) == 3
        assert [f['price'] for f in fills] == ['101.00', '101.50', '102.00']
        assert sum(Decimal(f['qty']) for f in fills) == Decimal('4.5')
        trade_ids = [f['tradeId'] for f in fills]
        assert trade_ids == sorted(trade_ids)
        assert all(isinstance(tid, int) for tid in trade_ids)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_sell_walks_bids(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'side': 'SELL', 'quantity': '0.25'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 200

        payload = await resp.json()
        assert payload['side'] == 'SELL'
        assert payload['fills'][0]['price'] == '100.00'
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_updates_ledger_balances(tmp_path: Path) -> None:

    client, _, ledger, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        resp = await client.post(
            '/api/v3/order',
            headers=signed_headers,
            params=_POST_BASE_PARAMS,
        )
        assert resp.status == 200

        usdt, btc = await ledger.balance(_ACCOUNT_ID)
        expected_notional = Decimal('101.00') * Decimal('0.5')
        expected_fee = expected_notional * Decimal('0.001')
        assert usdt == Decimal('10000') - expected_notional - expected_fee
        assert btc == Decimal('0.5') + Decimal('0.5')
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_when_book_stale(tmp_path: Path) -> None:

    stale_ts = int(__import__('time').time() * 1000) - (_THRESHOLD_MS + 1000)
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path, book_ts_ms=stale_ts)

    try:
        resp = await client.post('/api/v3/order', headers=signed_headers, params=_POST_BASE_PARAMS)
        assert resp.status == 503

        payload = await resp.json()
        assert payload['code'] == -1003
        assert 'stale' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_when_book_never_polled(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.post('/api/v3/order', headers=signed_headers, params=_POST_BASE_PARAMS)
        assert resp.status == 503

        payload = await resp.json()
        assert payload['code'] == -1003
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_missing_api_key(tmp_path: Path) -> None:

    client, _, _, _, _ = await _make_client_with_fresh_book(tmp_path)

    try:
        resp = await client.post('/api/v3/order', params=_POST_BASE_PARAMS)
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_wrong_symbol(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'symbol': 'ETHUSDT'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1121
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_wrong_type(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'type': 'LIMIT'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
        assert 'MARKET' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_wrong_side(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'side': 'HOLD'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_missing_quantity(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {k: v for k, v in _POST_BASE_PARAMS.items() if k != 'quantity'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_zero_quantity(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': '0'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_malformed_quantity(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': 'not-a-number'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_missing_client_order_id(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {k: v for k, v in _POST_BASE_PARAMS.items() if k != 'newClientOrderId'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_duplicate_client_order_id(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        resp1 = await client.post('/api/v3/order', headers=signed_headers, params=_POST_BASE_PARAMS)
        assert resp1.status == 200

        resp2 = await client.post('/api/v3/order', headers=signed_headers, params=_POST_BASE_PARAMS)
        assert resp2.status == 400

        payload = await resp2.json()
        assert payload['code'] == -2010
        assert 'duplicate' in payload['msg'].lower()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_when_book_insufficient(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': '99'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -2010
        assert 'liquidity' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_when_balance_insufficient(tmp_path: Path) -> None:

    book, _, poller = _make_components(tmp_path)
    ledger = Ledger(tmp_path)
    api_key = await ledger.register_account(_ACCOUNT_ID, Decimal('5'))
    poller._last_success_ts_ms = int(__import__('time').time() * 1000)

    app = make_app(book, ledger, poller, _THRESHOLD_MS)
    client = TestClient(TestServer(app))
    await client.start_server()

    signed_headers = {'X-MBX-APIKEY': api_key}

    try:
        resp = await client.post('/api/v3/order', headers=signed_headers, params=_POST_BASE_PARAMS)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -2010
        assert 'insufficient balance' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_response_fills_sum_matches_executed_qty(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': '2.5'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        payload = await resp.json()

        fills_qty_sum = sum(Decimal(f['qty']) for f in payload['fills'])
        assert fills_qty_sum == Decimal(payload['executedQty'])
        assert fills_qty_sum == Decimal('2.5')
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_response_cumulative_quote_matches_walk(tmp_path: Path) -> None:

    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': '2.5'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        payload = await resp.json()

        expected_quote = Decimal('101.00') * Decimal('1.0') + Decimal('101.50') * Decimal('1.5')
        assert Decimal(payload['cummulativeQuoteQty']) == expected_quote
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_returns_400_when_ledger_account_missing(tmp_path: Path) -> None:
    book = _seeded_book()
    poller = DepthPoller(book, _URL, _TOKEN)
    poller._last_success_ts_ms = int(__import__('time').time() * 1000)

    ledger = Ledger(tmp_path)
    api_key = await ledger.register_account(_ACCOUNT_ID, Decimal('10000'))
    ledger._accounts.pop(_ACCOUNT_ID)

    app = make_app(book, ledger, poller, _THRESHOLD_MS)
    client = TestClient(TestServer(app))
    await client.start_server()

    signed_headers = {'X-MBX-APIKEY': api_key}

    try:
        resp = await client.post('/api/v3/order', headers=signed_headers, params=_POST_BASE_PARAMS)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -2010
        assert 'not registered' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_missing_symbol_with_bad_request_code(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {k: v for k, v in _POST_BASE_PARAMS.items() if k != 'symbol'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
        assert 'missing symbol' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_missing_side_with_bad_request_code(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {k: v for k, v in _POST_BASE_PARAMS.items() if k != 'side'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
        assert payload['msg'] == 'missing side'
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_missing_type_with_bad_request_code(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {k: v for k, v in _POST_BASE_PARAMS.items() if k != 'type'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
        assert payload['msg'] == 'missing type'
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_rejects_empty_signature(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/account', headers=signed_headers, params={'signature': ''})
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_rejects_whitespace_signature(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client(tmp_path)

    try:
        resp = await client.get('/api/v3/account', headers=signed_headers, params={'signature': '   '})
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_whitespace_client_order_id(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'newClientOrderId': '   '}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
        assert 'newClientOrderId' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_account_rejects_whitespace_api_key_header(tmp_path: Path) -> None:
    client, _, _, _, _ = await _make_client(tmp_path)

    try:
        resp = await client.get(
            '/api/v3/account',
            headers={'X-MBX-APIKEY': '   '},
            params=_SIGNATURE_PARAMS,
        )
        assert resp.status == 401
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_server_start_failure_cleans_up_runner_state(tmp_path: Path) -> None:
    book, ledger, poller = _make_components(tmp_path)
    await ledger.register_account(_ACCOUNT_ID, Decimal('1'))

    server_a = BinsimServer('127.0.0.1', 0, book, ledger, poller, _THRESHOLD_MS)
    await server_a.start()

    port = next(iter(server_a._site._server.sockets)).getsockname()[1]

    try:
        server_b = BinsimServer('127.0.0.1', port, book, ledger, poller, _THRESHOLD_MS)

        with pytest.raises(OSError):
            await server_b.start()

        assert server_b.is_running is False
        assert server_b._site is None
        assert server_b._runner is None
    finally:
        await server_a.stop()


@pytest.mark.asyncio
async def test_post_order_rejects_when_last_success_ts_is_in_future(tmp_path: Path) -> None:
    import time as _t

    future_ts = int(_t.time() * 1000) + 24 * 60 * 60 * 1000  # one day in the future
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(
        tmp_path, book_ts_ms=future_ts,
    )

    try:
        resp = await client.post('/api/v3/order', headers=signed_headers, params=_POST_BASE_PARAMS)
        assert resp.status == 503

        payload = await resp.json()
        assert payload['code'] == -1003
        assert 'stale' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_nan_quantity(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': 'NaN'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
        assert 'finite' in payload['msg']
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_post_order_rejects_infinity_quantity(tmp_path: Path) -> None:
    client, _, _, _, signed_headers = await _make_client_with_fresh_book(tmp_path)

    try:
        params = {**_POST_BASE_PARAMS, 'quantity': 'Infinity'}
        resp = await client.post('/api/v3/order', headers=signed_headers, params=params)
        assert resp.status == 400

        payload = await resp.json()
        assert payload['code'] == -1100
    finally:
        await client.close()
