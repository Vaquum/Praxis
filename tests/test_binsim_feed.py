'''Render observation, source-clock, policy and regional recovery contracts.'''

from __future__ import annotations

import asyncio
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import Ledger
from praxis.binsim.server import make_app

_URL = 'https://binance-book-collector-a.onrender.com/latest/spot'
_TOKEN = 'test-token'
_FIXTURE = Path(__file__).parent / 'fixtures/render-top20/spot.ndjson'
_OBSERVATIONS = [json.loads(line) for line in _FIXTURE.read_bytes().splitlines()]
_PAYLOAD = _OBSERVATIONS[0]


@pytest.fixture(autouse=True)
def replay_clock(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    '''Replay time; never change original source clocks or market values.'''
    clock = [_PAYLOAD['observed_at'] + 100_000]
    monkeypatch.setattr('praxis.binsim.feed.time.time', lambda: clock[0] / 1_000_000)
    return clock


def _mock_response(status: int, data: Any | None = None) -> AsyncMock:
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=data if data is not None else {})
    response.request_info = MagicMock()
    response.history = ()
    return response


def _attach_mock_session(poller: DepthPoller, response: AsyncMock) -> MagicMock:
    session = MagicMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=context)
    session.close = AsyncMock()
    poller._session = session
    return session


def _make_poller(book: OrderBook | None = None) -> DepthPoller:
    return DepthPoller(book or OrderBook(), _URL, _TOKEN, poll_interval_ms=50)


@pytest.mark.asyncio
async def test_poll_once_preserves_original_values_clocks_and_cached_age(monkeypatch: pytest.MonkeyPatch) -> None:
    log = MagicMock()
    monkeypatch.setattr('praxis.binsim.feed._log', log)
    provenance = json.loads(_FIXTURE.with_name('provenance.json').read_text())
    assert hashlib.sha256(_FIXTURE.read_bytes()).hexdigest() == provenance['sha256']
    book = OrderBook()
    poller = _make_poller(book)
    response = _mock_response(200, _PAYLOAD)
    session = _attach_mock_session(poller, response)
    await poller.poll_once()
    await poller.poll_once()
    assert book.last_update_id == _PAYLOAD['update_id']
    assert book.ts_ms == _PAYLOAD['exchange_time'] // 1000
    assert poller.exchange_time_us == _PAYLOAD['exchange_time']
    assert poller.observed_at_us == _PAYLOAD['observed_at']
    assert poller.last_success_ts_ms == min(_PAYLOAD['exchange_time'], _PAYLOAD['observed_at']) // 1000
    assert book.bids == [(Decimal(p), Decimal(q)) for p, q in _PAYLOAD['bids']]
    assert book.asks == [(Decimal(p), Decimal(q)) for p, q in _PAYLOAD['asks']]
    assert session.get.call_args.args == (_URL,)
    assert session.get.call_args.kwargs['headers'] == {'Authorization': f'Bearer {_TOKEN}'}
    response.json.assert_called_with(content_type=None)
    diagnostic = log.info.call_args.kwargs
    assert diagnostic['last_update_id'] == _PAYLOAD['update_id']
    assert diagnostic['ask_levels_in_payload'] == diagnostic['bid_levels_in_payload'] == 20
    assert diagnostic['ask_top_n_qty'] == str(sum((Decimal(q) for _, q in _PAYLOAD['asks']), Decimal('0')))
    assert diagnostic['best_bid_price'] == _PAYLOAD['bids'][0][0]


@pytest.mark.parametrize('fault', [
    'non-object', 'missing-clock', 'wrong-market', 'wrong-symbol', 'float-clock',
    'future-exchange', 'future-receipt', 'missing-side', 'truncated',
    'malformed-decimal', 'non-finite', 'crossed', 'regressed-id',
])
@pytest.mark.asyncio
async def test_protocol_fault_leaves_last_accepted_book_unchanged(fault: str) -> None:
    '''Deliberate protocol faults derived from one genuine observation.'''
    book = OrderBook()
    poller = _make_poller(book)
    _attach_mock_session(poller, _mock_response(200, _PAYLOAD))
    await poller.poll_once()
    before = (book.bids, book.asks, book.last_update_id, poller.last_success_ts_ms)
    bad = deepcopy(_PAYLOAD)
    if fault == 'non-object':
        bad = []
    elif fault == 'missing-clock':
        del bad['observed_at']
    elif fault == 'wrong-market':
        bad['market'] = 'perp'
    elif fault == 'wrong-symbol':
        bad['symbol'] = 'ETHUSDT'
    elif fault == 'float-clock':
        bad['exchange_time'] = float(bad['exchange_time'])
    elif fault == 'future-exchange':
        bad['exchange_time'] += 1_000_000
    elif fault == 'future-receipt':
        bad['observed_at'] += 1_000_000
    elif fault == 'missing-side':
        del bad['asks']
    elif fault == 'truncated':
        bad['bids'].pop()
    elif fault == 'malformed-decimal':
        bad['asks'][0][1] = 'invalid'
    elif fault == 'non-finite':
        bad['asks'][0][1] = 'NaN'
    elif fault == 'crossed':
        bad['bids'][0][0] = bad['asks'][0][0]
    else:
        bad['update_id'] -= 1
    _attach_mock_session(poller, _mock_response(200, bad))
    with pytest.raises((ValueError, KeyError, ArithmeticError)):
        await poller.poll_once()
    assert (book.bids, book.asks, book.last_update_id, poller.last_success_ts_ms) == before


@pytest.mark.asyncio
async def test_quantity_floor_accepts_exact_captured_boundary() -> None:
    floor = min(sum((Decimal(q) for _, q in _PAYLOAD[side]), Decimal('0')) for side in ('bids', 'asks'))
    poller = DepthPoller(OrderBook(), _URL, _TOKEN, min_top20_depth_btc=floor)
    _attach_mock_session(poller, _mock_response(200, _PAYLOAD))
    await poller.poll_once()
    assert poller.last_success_ts_ms == _PAYLOAD['exchange_time'] // 1000


@pytest.mark.parametrize('side', ['bids', 'asks'])
@pytest.mark.asyncio
async def test_quantity_floor_rejects_protocol_fault_without_refresh(side: str) -> None:
    '''Deliberately zero one captured side; retain the existing magnitude policy.'''
    bad = deepcopy(_PAYLOAD)
    for level in bad[side]:
        level[1] = '0'
    book = OrderBook()
    poller = _make_poller(book)
    _attach_mock_session(poller, _mock_response(200, bad))
    await poller.poll_once()
    assert book.bids == [] and poller.last_success_ts_ms == 0


@pytest.mark.asyncio
async def test_stuck_threshold_and_real_next_observation_reset(replay_clock: list[int]) -> None:
    book = OrderBook()
    poller = DepthPoller(book, _URL, _TOKEN, max_stuck_update_id_polls=3)
    _attach_mock_session(poller, _mock_response(200, _PAYLOAD))
    for _ in range(4):
        await poller.poll_once()
    assert poller._stuck_update_id_count == 4
    assert book.last_update_id == _PAYLOAD['update_id']
    next_observation = _OBSERVATIONS[1]
    replay_clock[0] = next_observation['observed_at'] + 100_000
    _attach_mock_session(poller, _mock_response(200, next_observation))
    await poller.poll_once()
    assert book.last_update_id == next_observation['update_id']
    assert poller._stuck_update_id_count == 1


@pytest.mark.asyncio
async def test_poll_loop_recovers_from_http_and_schema_failures() -> None:
    poller = _make_poller()
    responses = [_mock_response(503), _mock_response(200, []), _mock_response(200, _PAYLOAD)]
    session = MagicMock()
    contexts = []
    for response in responses:
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=False)
        contexts.append(context)
    session.get = MagicMock(side_effect=contexts)
    poller._session = session
    poller._task = asyncio.create_task(poller._poll_loop())
    try:
        for _ in range(50):
            await asyncio.sleep(0.02)
            if poller.last_success_ts_ms:
                break
    finally:
        poller._stop_event.set()
        await poller._task
    assert poller.last_success_ts_ms == _PAYLOAD['exchange_time'] // 1000


@pytest.mark.asyncio
async def test_regional_http_recovery_order_age_and_reader_restart(
    tmp_path: Path, replay_clock: list[int],
) -> None:
    '''Real HTTP boundaries; only peer availability and the replay clock are controlled.'''
    calls: list[tuple[str, str]] = []
    state = {'a_status': 503, 'row': 0}

    async def source(request: web.Request) -> web.Response:
        region = request.match_info['region']
        calls.append((region, request.headers['Authorization']))
        if region == 'a' and state['a_status'] != 200:
            return web.Response(status=state['a_status'])
        return web.json_response(_OBSERVATIONS[state['row']])

    app = web.Application()
    app.router.add_get('/{region}/latest/spot', source)
    sources = TestServer(app)
    await sources.start_server()
    book = OrderBook()
    ledger = Ledger(tmp_path)
    api_key = await ledger.register_account('recorded-book-proof', Decimal('10000'), Decimal('0'))
    poller = DepthPoller(book, str(sources.make_url('/a/latest/spot')), 'a-read',
                         fallback_url=str(sources.make_url('/b/latest/spot')), fallback_token='b-read')
    poller._session = aiohttp.ClientSession()
    reader = TestClient(TestServer(make_app(book, ledger, poller, 5000)))
    await reader.start_server()
    try:
        await poller.poll_once()
        assert calls == [('a', 'Bearer a-read'), ('b', 'Bearer b-read')]
        await poller.poll_once()
        assert [region for region, _ in calls] == ['a', 'b', 'b']
        depth = await reader.get('/api/v3/depth?symbol=BTCUSDT&limit=20')
        assert depth.status == 200
        assert (await depth.json())['lastUpdateId'] == _PAYLOAD['update_id']
        order_url = '/api/v3/order?symbol=BTCUSDT&side=BUY&type=MARKET&quantity=0.001&newClientOrderId=recorded-book-proof&signature=local-proof'
        accepted = await reader.post(order_url, headers={'X-MBX-APIKEY': api_key})
        assert accepted.status == 200
        assert (await accepted.json())['status'] == 'FILLED'
        original_age = poller.last_success_ts_ms
        state['a_status'] = 200  # Peer recovers with the same cached original.
        replay_clock[0] += 6_000_000
        with pytest.raises(ValueError, match='stale'):
            await poller.poll_once()
        assert poller.last_success_ts_ms == original_age
        rejected = await reader.post(order_url, headers={'X-MBX-APIKEY': api_key})
        assert rejected.status == 503 and (await rejected.json())['code'] == -1003
        state.update(a_status=200, row=2)
        replay_clock[0] = _OBSERVATIONS[2]['observed_at'] + 100_000
        await poller.stop()
        restarted = DepthPoller(book, str(sources.make_url('/a/latest/spot')), 'a-read',
                                fallback_url=str(sources.make_url('/b/latest/spot')), fallback_token='b-read')
        restarted._session = aiohttp.ClientSession()
        try:
            await restarted.poll_once()
            assert book.last_update_id == _OBSERVATIONS[2]['update_id']
            restored = Ledger(tmp_path)
            await restored.load()
            assert await restored.accounts() == await ledger.accounts()
            assert await restored.balance('recorded-book-proof') == await ledger.balance('recorded-book-proof')
        finally:
            await restarted.stop()
    finally:
        await poller.stop()
        await reader.close()
        await sources.close()
@pytest.mark.parametrize('interval', [0, -1, -1000])
def test_constructor_rejects_non_positive_poll_interval(interval: int) -> None:

    with pytest.raises(ValueError, match='poll_interval_ms must be positive'):
        DepthPoller(OrderBook(), _URL, _TOKEN, poll_interval_ms=interval)


@pytest.mark.parametrize('timeout', [0.0, -0.1, -10.0])
def test_constructor_rejects_non_positive_request_timeout(timeout: float) -> None:

    with pytest.raises(ValueError, match='request_timeout_s must be positive'):
        DepthPoller(OrderBook(), _URL, _TOKEN, request_timeout_s=timeout)


def test_constructor_rejects_empty_url() -> None:

    with pytest.raises(ValueError, match='url cannot be empty'):
        DepthPoller(OrderBook(), '', _TOKEN)


def test_constructor_rejects_empty_token() -> None:

    with pytest.raises(ValueError, match='token cannot be empty'):
        DepthPoller(OrderBook(), _URL, '')


def test_initial_last_success_ts_ms_is_zero() -> None:

    poller = _make_poller()

    assert poller.last_success_ts_ms == 0


def test_is_running_false_before_start() -> None:

    poller = _make_poller()

    assert poller.is_running is False


@pytest.mark.asyncio
async def test_poll_once_raises_without_started_session() -> None:

    poller = _make_poller()

    with pytest.raises(RuntimeError, match='session not initialised'):
        await poller.poll_once()


@pytest.mark.asyncio
async def test_start_creates_session_and_task() -> None:

    poller = _make_poller()
    await poller.start()

    try:
        assert poller.is_running is True
        assert poller._session is not None
    finally:
        await poller.stop()


@pytest.mark.asyncio
async def test_start_twice_raises() -> None:

    poller = _make_poller()
    await poller.start()

    try:
        with pytest.raises(RuntimeError, match='already running'):
            await poller.start()
    finally:
        await poller.stop()


@pytest.mark.asyncio
async def test_stop_closes_session_and_clears_task() -> None:

    poller = _make_poller()
    await poller.start()
    await poller.stop()

    assert poller.is_running is False
    assert poller._session is None
    assert poller._task is None


@pytest.mark.asyncio
async def test_stop_is_idempotent() -> None:

    poller = _make_poller()
    await poller.start()
    await poller.stop()
    await poller.stop()

    assert poller.is_running is False


@pytest.mark.parametrize('floor', [Decimal('0'), Decimal('-0.1'), Decimal('-1')])
def test_constructor_rejects_non_positive_min_top20_depth(floor: Decimal) -> None:

    with pytest.raises(ValueError, match='min_top20_depth_btc must be a positive'):
        DepthPoller(OrderBook(), _URL, _TOKEN, min_top20_depth_btc=floor)


@pytest.mark.parametrize('raw', ['NaN', 'Infinity', '-Infinity'])
def test_constructor_rejects_non_finite_min_top20_depth(raw: str) -> None:

    with pytest.raises(ValueError, match='min_top20_depth_btc must be a positive'):
        DepthPoller(OrderBook(), _URL, _TOKEN, min_top20_depth_btc=Decimal(raw))


@pytest.mark.parametrize('limit', [0, -1, 1])
def test_constructor_rejects_meaningless_stuck_polls(limit: int) -> None:
    '''Pin: the meaningful minimum is 2 (baseline + one repeat).

    `limit=1` would brick the feed: the first poll sets the
    counter to 1 (else branch, since `_previous_last_update_id`
    starts at 0), the threshold check `1 >= 1` immediately
    rejects, the book never primes, and the rejection log
    misleadingly claims the id is "stuck across consecutive polls"
    — even though only one poll has been observed.
    '''

    with pytest.raises(ValueError, match='max_stuck_update_id_polls must be >= 2'):
        DepthPoller(OrderBook(), _URL, _TOKEN, max_stuck_update_id_polls=limit)
