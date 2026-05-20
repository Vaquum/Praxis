'''Shape-conformance smoke test: BinanceAdapter against a live BinsimServer.

The goal is **not** to re-test individual endpoints — each has its own
unit tests against `aiohttp.test_utils.TestClient`. The goal is to
prove that the JSON Praxis's `BinanceAdapter` actually parses on the
wire matches what binsim emits, end-to-end, across every endpoint
binsim claims to serve. If any field name drifts (camelCase vs
snake_case, missing field, wrong type), the adapter raises here.
'''

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import Ledger
from praxis.binsim.server import BinsimServer
from praxis.core.domain.enums import OrderSide, OrderType
from praxis.infrastructure.binance_adapter import BinanceAdapter, NotFoundError


_ACCOUNT_ID = 'acc-1'
_API_SECRET = 'apisecret-1'  # noqa: S105 — test fixture, not a real credential
_DEPTH_URL = 'https://binance-spot-depth20-1000ms.onrender.com/top20'
_DEPTH_TOKEN = 'test-token'  # noqa: S105 — test fixture, not a real credential
_THRESHOLD_MS = 60_000

_BIDS = [
    (Decimal('100.00'), Decimal('10.0')),
    (Decimal('99.50'), Decimal('20.0')),
]
_ASKS = [
    (Decimal('101.00'), Decimal('10.0')),
    (Decimal('101.50'), Decimal('20.0')),
]


@pytest_asyncio.fixture
async def binsim_server(tmp_path: Path) -> AsyncGenerator[tuple[BinsimServer, str], None]:

    book = OrderBook()
    book.replace(_BIDS, _ASKS, last_update_id=1, ts_ms=int(time.time() * 1000))

    ledger = Ledger(tmp_path)
    api_key = await ledger.register_account(_ACCOUNT_ID, Decimal('100000'), Decimal('5.0'))

    poller = DepthPoller(book, _DEPTH_URL, _DEPTH_TOKEN)
    poller._last_success_ts_ms = int(time.time() * 1000)

    server = BinsimServer(
        '127.0.0.1', 0, book, ledger, poller, _THRESHOLD_MS,
    )
    await server.start()

    yield server, api_key

    await server.stop()


@pytest_asyncio.fixture
async def adapter(
    binsim_server: tuple[BinsimServer, str],
) -> AsyncGenerator[BinanceAdapter, None]:

    server, api_key = binsim_server
    site = server._site

    assert site is not None

    sockets = list(site._server.sockets) if site._server is not None else []

    assert sockets, 'binsim server has no bound socket'

    port = sockets[0].getsockname()[1]
    base_url = f'http://127.0.0.1:{port}'

    a = BinanceAdapter(base_url, base_url, base_url)
    a.register_account(_ACCOUNT_ID, api_key, _API_SECRET)

    yield a

    await a.close()


@pytest.mark.asyncio
async def test_adapter_load_filters_parses_exchangeinfo(adapter: BinanceAdapter) -> None:

    await adapter.load_filters(['BTCUSDT'])

    filters = adapter._filters.get('BTCUSDT')

    assert filters is not None
    assert filters.tick_size == Decimal('0.01000000')
    assert filters.lot_step == Decimal('0.00001000')
    assert filters.lot_min == Decimal('0.00001000')
    assert filters.lot_max == Decimal('9000.00000000')
    assert filters.min_notional == Decimal('5.00000000')


@pytest.mark.asyncio
async def test_adapter_query_order_book_parses_depth(adapter: BinanceAdapter) -> None:

    snapshot = await adapter.query_order_book('BTCUSDT')

    assert snapshot.last_update_id == 1
    assert len(snapshot.bids) == 2
    assert len(snapshot.asks) == 2
    assert snapshot.bids[0].price == Decimal('100.00')
    assert snapshot.bids[0].qty == Decimal('10.0')
    assert snapshot.asks[0].price == Decimal('101.00')


@pytest.mark.asyncio
async def test_adapter_query_balance_parses_account(adapter: BinanceAdapter) -> None:

    balances = await adapter.query_balance(_ACCOUNT_ID, frozenset({'USDT', 'BTC'}))

    by_asset = {b.asset: b for b in balances}
    assert by_asset['USDT'].free == Decimal('100000')
    assert by_asset['USDT'].locked == Decimal('0')
    assert by_asset['BTC'].free == Decimal('5.0')
    assert by_asset['BTC'].locked == Decimal('0')


@pytest.mark.asyncio
async def test_adapter_query_open_orders_parses_empty_list(adapter: BinanceAdapter) -> None:

    orders = await adapter.query_open_orders(_ACCOUNT_ID, 'BTCUSDT')

    assert orders == []


@pytest.mark.asyncio
async def test_adapter_query_trades_parses_empty_list(adapter: BinanceAdapter) -> None:

    trades = await adapter.query_trades(_ACCOUNT_ID, 'BTCUSDT')

    assert trades == []


@pytest.mark.asyncio
async def test_adapter_query_venue_order_raises_not_found(adapter: BinanceAdapter) -> None:

    with pytest.raises(NotFoundError):
        await adapter.query_order(
            _ACCOUNT_ID, 'BTCUSDT', venue_order_id='999',
        )


@pytest.mark.asyncio
async def test_adapter_submit_order_parses_market_buy_response(adapter: BinanceAdapter) -> None:

    await adapter.load_filters(['BTCUSDT'])

    result = await adapter.submit_order(
        account_id=_ACCOUNT_ID,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('0.5'),
        client_order_id='smoke-cid-1',
    )

    assert result.venue_order_id != ''
    assert result.status.value == 'FILLED'

    fills = list(result.immediate_fills)

    assert len(fills) == 1
    assert fills[0].price == Decimal('101.00')
    assert fills[0].qty == Decimal('0.5')
    assert fills[0].fee == Decimal('101.00') * Decimal('0.5') * Decimal('0.001')
    assert fills[0].fee_asset == 'USDT'
    assert fills[0].is_maker is False


@pytest.mark.asyncio
async def test_adapter_submit_order_walks_multiple_levels(adapter: BinanceAdapter) -> None:

    await adapter.load_filters(['BTCUSDT'])

    result = await adapter.submit_order(
        account_id=_ACCOUNT_ID,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('15.0'),
        client_order_id='smoke-cid-2',
    )

    fills = list(result.immediate_fills)

    assert len(fills) == 2
    assert sum((f.qty for f in fills), Decimal('0')) == Decimal('15.0')


@pytest.mark.asyncio
async def test_adapter_submit_order_then_balance_reflects_fill(adapter: BinanceAdapter) -> None:

    await adapter.load_filters(['BTCUSDT'])
    await adapter.submit_order(
        account_id=_ACCOUNT_ID,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('0.5'),
        client_order_id='smoke-cid-3',
    )

    balances = await adapter.query_balance(_ACCOUNT_ID, frozenset({'USDT', 'BTC'}))
    by_asset = {b.asset: b for b in balances}

    expected_notional = Decimal('101.00') * Decimal('0.5')
    expected_fee = expected_notional * Decimal('0.001')

    assert by_asset['USDT'].free == Decimal('100000') - expected_notional - expected_fee
    assert by_asset['BTC'].free == Decimal('5.0') + Decimal('0.5')
