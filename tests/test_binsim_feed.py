'''Tests for praxis.binsim.feed.DepthPoller.'''

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller


_URL = 'https://binance-spot-depth20-1000ms.onrender.com/top20'
_TOKEN = 'test-token'  # noqa: S105 — test fixture, not a real credential

_PAYLOAD: dict[str, Any] = {
    't': 1_700_000_000_000,
    'd': {
        'lastUpdateId': 12345,
        'bids': [['100.00', '1.0'], ['99.50', '2.0']],
        'asks': [['101.00', '1.0'], ['101.50', '2.0']],
    },
}


def _mock_response(status: int, data: Any | None = None) -> AsyncMock:

    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data if data is not None else {})
    resp.request_info = MagicMock()
    resp.history = ()

    return resp


def _attach_mock_session(poller: DepthPoller, response: AsyncMock) -> MagicMock:

    session = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=ctx)
    session.close = AsyncMock()
    session.closed = False
    poller._session = session

    return session


def _make_poller(book: OrderBook | None = None) -> DepthPoller:

    return DepthPoller(book or OrderBook(), _URL, _TOKEN, poll_interval_ms=50)


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
async def test_poll_once_populates_book_and_updates_ts() -> None:

    import time as _t

    book = OrderBook()
    poller = _make_poller(book)
    _attach_mock_session(poller, _mock_response(200, _PAYLOAD))

    before_ms = int(_t.time() * 1000)
    await poller.poll_once()
    after_ms = int(_t.time() * 1000)

    assert book.last_update_id == 12345
    assert book.ts_ms == 1_700_000_000_000
    assert book.bids == [(Decimal('100.00'), Decimal('1.0')), (Decimal('99.50'), Decimal('2.0'))]
    assert book.asks == [(Decimal('101.00'), Decimal('1.0')), (Decimal('101.50'), Decimal('2.0'))]
    # last_success_ts_ms is local wall-clock at receipt, NOT the
    # upstream `t` (1.7e12 = 2023) — defense against future-dated `t`
    # bypassing the staleness gate.
    assert before_ms <= poller.last_success_ts_ms <= after_ms
    assert poller.last_success_ts_ms != 1_700_000_000_000


@pytest.mark.asyncio
async def test_poll_once_sends_bearer_auth_header() -> None:

    poller = _make_poller()
    session = _attach_mock_session(poller, _mock_response(200, _PAYLOAD))

    await poller.poll_once()

    call_kwargs = session.get.call_args.kwargs
    assert call_kwargs['headers'] == {'Authorization': f'Bearer {_TOKEN}'}


@pytest.mark.asyncio
async def test_poll_once_calls_configured_url() -> None:

    poller = _make_poller()
    session = _attach_mock_session(poller, _mock_response(200, _PAYLOAD))

    await poller.poll_once()

    assert session.get.call_args.args[0] == _URL


@pytest.mark.asyncio
async def test_poll_once_raises_on_non_200_and_leaves_ts_untouched() -> None:

    book = OrderBook()
    poller = _make_poller(book)
    _attach_mock_session(poller, _mock_response(503))

    with pytest.raises(aiohttp.ClientResponseError, match='depth poll non-200'):
        await poller.poll_once()

    assert poller.last_success_ts_ms == 0


@pytest.mark.asyncio
async def test_poll_once_raises_on_malformed_payload_missing_t() -> None:

    poller = _make_poller()
    _attach_mock_session(poller, _mock_response(200, {'d': _PAYLOAD['d']}))

    with pytest.raises(KeyError):
        await poller.poll_once()

    assert poller.last_success_ts_ms == 0


@pytest.mark.asyncio
async def test_poll_once_raises_on_malformed_payload_missing_d() -> None:

    poller = _make_poller()
    _attach_mock_session(poller, _mock_response(200, {'t': 1_700_000_000_000}))

    with pytest.raises(KeyError):
        await poller.poll_once()


@pytest.mark.asyncio
async def test_poll_once_raises_value_error_on_non_dict_payload() -> None:

    poller = _make_poller()
    _attach_mock_session(poller, _mock_response(200, [1, 2, 3]))

    with pytest.raises(ValueError, match='depth payload must be a JSON object'):
        await poller.poll_once()


@pytest.mark.asyncio
async def test_poll_once_raises_value_error_when_d_is_not_dict() -> None:

    poller = _make_poller()
    bad_payload = {'t': 1_700_000_000_000, 'd': 'not-a-dict'}
    _attach_mock_session(poller, _mock_response(200, bad_payload))

    with pytest.raises(ValueError, match="'d' must be a JSON object"):
        await poller.poll_once()


@pytest.mark.asyncio
async def test_poll_once_raises_arithmetic_error_on_malformed_decimal() -> None:

    from decimal import InvalidOperation

    poller = _make_poller()
    bad_payload = {
        't': 1_700_000_000_000,
        'd': {
            'lastUpdateId': 1,
            'bids': [['not-a-decimal', '1.0']],
            'asks': [['101.00', '1.0']],
        },
    }
    _attach_mock_session(poller, _mock_response(200, bad_payload))

    with pytest.raises((ArithmeticError, InvalidOperation)):
        await poller.poll_once()


@pytest.mark.asyncio
async def test_poll_loop_does_not_crash_on_non_dict_payload() -> None:

    book = OrderBook()
    poller = _make_poller(book)

    bad_resp = _mock_response(200, ['not', 'a', 'dict'])
    ok_resp = _mock_response(200, _PAYLOAD)

    session = MagicMock()
    bad_ctx = MagicMock()
    bad_ctx.__aenter__ = AsyncMock(return_value=bad_resp)
    bad_ctx.__aexit__ = AsyncMock(return_value=False)
    ok_ctx = MagicMock()
    ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
    ok_ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(side_effect=[bad_ctx, ok_ctx, ok_ctx, ok_ctx])
    session.close = AsyncMock()
    session.closed = False
    poller._session = session

    poller._task = asyncio.create_task(poller._poll_loop())

    for _ in range(50):
        await asyncio.sleep(0.02)
        if poller.last_success_ts_ms > 0:
            break

    poller._stop_event.set()
    await poller._task

    assert poller.last_success_ts_ms > 0


@pytest.mark.asyncio
async def test_poll_once_propagates_orderbook_validation_error() -> None:

    crossed_payload = {
        't': 1_700_000_000_000,
        'd': {
            'lastUpdateId': 1,
            'bids': [['102.00', '1.0']],
            'asks': [['101.00', '1.0']],
        },
    }
    poller = _make_poller()
    _attach_mock_session(poller, _mock_response(200, crossed_payload))

    with pytest.raises(ValueError, match='book is crossed'):
        await poller.poll_once()

    assert poller.last_success_ts_ms == 0


@pytest.mark.asyncio
async def test_poll_loop_recovers_after_transient_failure() -> None:

    book = OrderBook()
    poller = _make_poller(book)

    fail_resp = _mock_response(503)
    ok_resp = _mock_response(200, _PAYLOAD)

    session = MagicMock()
    fail_ctx = MagicMock()
    fail_ctx.__aenter__ = AsyncMock(return_value=fail_resp)
    fail_ctx.__aexit__ = AsyncMock(return_value=False)
    ok_ctx = MagicMock()
    ok_ctx.__aenter__ = AsyncMock(return_value=ok_resp)
    ok_ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(side_effect=[fail_ctx, ok_ctx, ok_ctx, ok_ctx])
    session.close = AsyncMock()
    session.closed = False
    poller._session = session

    poller._task = asyncio.create_task(poller._poll_loop())

    for _ in range(50):
        await asyncio.sleep(0.02)
        if poller.last_success_ts_ms > 0:
            break

    poller._stop_event.set()
    await poller._task

    assert poller.last_success_ts_ms > 0
    assert book.last_update_id == 12345


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


@pytest.mark.asyncio
async def test_poll_once_accepts_non_application_json_content_type() -> None:
    book = OrderBook()
    poller = _make_poller(book)

    # response.json() with the default content_type would raise
    # aiohttp.ContentTypeError on text/plain; content_type=None
    # bypasses that check and lets _parse_payload run.
    resp = AsyncMock()
    resp.status = 200
    resp.json = AsyncMock(return_value=_PAYLOAD)
    resp.request_info = MagicMock()
    resp.history = ()
    _attach_mock_session(poller, resp)

    await poller.poll_once()

    # poll succeeded → book populated
    assert book.last_update_id == 12345
    # confirm json was called with content_type=None
    resp.json.assert_called_once_with(content_type=None)


@pytest.mark.asyncio
async def test_poll_once_raises_on_non_finite_decimal_in_book() -> None:
    poller = _make_poller()
    bad = {
        't': 1_700_000_000_000,
        'd': {
            'lastUpdateId': 1,
            'bids': [['NaN', '1.0']],
            'asks': [['101.00', '1.0']],
        },
    }
    _attach_mock_session(poller, _mock_response(200, bad))

    with pytest.raises(ValueError, match='must be a finite decimal'):
        await poller.poll_once()
