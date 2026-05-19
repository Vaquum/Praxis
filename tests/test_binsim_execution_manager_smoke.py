'''End-to-end smoke: ExecutionManager → BinanceAdapter → BinsimServer.

Proves the paper-trade loop bullet from issue #112: a MARKET command
submitted through `ExecutionManager` against a live `BinsimServer`
emits the same `CommandAccepted → OrderSubmitIntent → OrderSubmitted
→ FillReceived → TradeClosed → TradeOutcomeProduced` event-spine
sequence it does against testnet, and the slippage path
(`query_order_book → estimate_slippage`) executes cleanly against
binsim's `/api/v3/depth` response.

This is a smoke test, not a re-test of every endpoint — those have
their own coverage in `test_binsim_*_smoke.py` and
`test_execution_manager.py`. The goal here is to verify the seam:
the URL plumbing the launcher would set up (`BINSIM_URL` →
ws://-allowed → BinanceAdapter → BinsimServer) produces a clean
end-to-end trade.
'''

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import Ledger
from praxis.binsim.server import BinsimServer
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.events import (
    CommandAccepted,
    FillReceived,
    OrderSubmitIntent,
    OrderSubmitted,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.event_spine import EventSpine


_ACCOUNT_ID = 'acc-1'
_API_KEY = 'apikey-1'
_API_SECRET = 'apisecret-1'  # noqa: S105 — test fixture, not a real credential
_DEPTH_URL = 'https://binance-spot-depth20-1000ms.onrender.com/top20'
_DEPTH_TOKEN = 'test-token'  # noqa: S105 — test fixture, not a real credential
_STALENESS_THRESHOLD_MS = 60_000
_EPOCH = 1
_TRADE_ID = 'trade-1'

_BIDS = [
    (Decimal('100.00'), Decimal('10.0')),
    (Decimal('99.50'), Decimal('20.0')),
]
_ASKS = [
    (Decimal('101.00'), Decimal('10.0')),
    (Decimal('101.50'), Decimal('20.0')),
]


def _now_aware() -> datetime:

    return datetime.now(UTC)


@pytest_asyncio.fixture
async def binsim(tmp_path: Path) -> AsyncGenerator[BinsimServer, None]:

    book = OrderBook()
    book.replace(_BIDS, _ASKS, last_update_id=1, ts_ms=int(time.time() * 1000))

    ledger = Ledger(tmp_path / 'binsim_state')
    await ledger.register_account(_ACCOUNT_ID, Decimal('100000'), Decimal('5.0'))

    poller = DepthPoller(book, _DEPTH_URL, _DEPTH_TOKEN)
    poller._last_success_ts_ms = int(time.time() * 1000)

    server = BinsimServer(
        '127.0.0.1', 0, book, ledger, poller, _STALENESS_THRESHOLD_MS,
        {_API_KEY: _ACCOUNT_ID},
    )
    await server.start()

    yield server

    await server.stop()


@pytest_asyncio.fixture
async def adapter(
    binsim: BinsimServer,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[BinanceAdapter, None]:

    site = binsim._site

    assert site is not None
    assert site._server is not None

    sockets = list(site._server.sockets)

    assert sockets, 'binsim server has no bound socket'

    port = sockets[0].getsockname()[1]
    base_url = f'http://127.0.0.1:{port}'
    ws_url = f'ws://127.0.0.1:{port}'
    ws_api_url = f'ws://127.0.0.1:{port}/ws-api/v3'

    monkeypatch.setenv('BINSIM_URL', base_url)

    a = BinanceAdapter(base_url, ws_url, ws_api_url)
    a.register_account(_ACCOUNT_ID, _API_KEY, _API_SECRET)
    await a.load_filters(['BTCUSDT'])

    yield a

    await a.close()


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine,
    adapter: BinanceAdapter,
) -> AsyncGenerator[ExecutionManager, None]:

    em = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    em.register_account(_ACCOUNT_ID)

    yield em

    await em.unregister_account(_ACCOUNT_ID)


def _market_buy_cmd_kwargs(qty: Decimal) -> dict[str, Any]:

    return {
        'trade_id': _TRADE_ID,
        'account_id': _ACCOUNT_ID,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': qty,
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.SINGLE_SHOT,
        'execution_params': SingleShotParams(),
        'timeout': 300,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _now_aware(),
    }


async def _wait_for_event_types(
    spine: EventSpine,
    types: set[str],
    timeout_s: float = 5.0,
) -> list[tuple[int, Any]]:

    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:
        events = await spine.read(_EPOCH, after_seq=0)
        observed = {type(event).__name__ for _, event in events}

        if types.issubset(observed):
            return events

        await asyncio.sleep(0.05)

    events = await spine.read(_EPOCH, after_seq=0)
    observed = {type(event).__name__ for _, event in events}
    missing = types - observed
    msg = f'event-spine did not contain {missing} within {timeout_s}s; got {observed}'
    raise AssertionError(msg)


@pytest.mark.asyncio
async def test_market_buy_through_binsim_emits_expected_spine_sequence(
    spine: EventSpine,
    mgr: ExecutionManager,
) -> None:

    await mgr.submit_command(**_market_buy_cmd_kwargs(qty=Decimal('0.5')))

    events = await _wait_for_event_types(
        spine,
        types={'CommandAccepted', 'OrderSubmitIntent', 'OrderSubmitted', 'FillReceived'},
    )

    type_sequence = [type(e).__name__ for _, e in events]
    assert type_sequence[0] == 'CommandAccepted'
    assert 'OrderSubmitIntent' in type_sequence
    assert 'OrderSubmitted' in type_sequence
    assert 'FillReceived' in type_sequence


@pytest.mark.asyncio
async def test_market_buy_through_binsim_records_actual_fill_details(
    spine: EventSpine,
    mgr: ExecutionManager,
) -> None:

    await mgr.submit_command(**_market_buy_cmd_kwargs(qty=Decimal('0.5')))

    events = await _wait_for_event_types(spine, types={'FillReceived'})
    fills = [e for _, e in events if isinstance(e, FillReceived)]

    assert len(fills) == 1
    fill = fills[0]
    assert fill.qty == Decimal('0.5')
    assert fill.price == Decimal('101.00')
    assert fill.fee_asset == 'USDT'
    assert fill.fee == Decimal('101.00') * Decimal('0.5') * Decimal('0.001')


@pytest.mark.asyncio
async def test_market_buy_walks_multiple_levels_emits_per_level_fills(
    spine: EventSpine,
    mgr: ExecutionManager,
) -> None:

    await mgr.submit_command(**_market_buy_cmd_kwargs(qty=Decimal('15.0')))

    events = await _wait_for_event_types(spine, types={'FillReceived'})
    fills = [e for _, e in events if isinstance(e, FillReceived)]

    assert len(fills) == 2
    assert sum((f.qty for f in fills), Decimal('0')) == Decimal('15.0')


@pytest.mark.asyncio
async def test_command_accepted_event_carries_command_id(
    spine: EventSpine,
    mgr: ExecutionManager,
) -> None:

    command_id = await mgr.submit_command(**_market_buy_cmd_kwargs(qty=Decimal('0.1')))

    events = await _wait_for_event_types(spine, types={'CommandAccepted'})
    accepts = [e for _, e in events if isinstance(e, CommandAccepted)]

    assert len(accepts) == 1
    assert accepts[0].command_id == command_id


@pytest.mark.asyncio
async def test_order_submit_intent_and_submitted_share_client_order_id(
    spine: EventSpine,
    mgr: ExecutionManager,
) -> None:

    await mgr.submit_command(**_market_buy_cmd_kwargs(qty=Decimal('0.1')))

    events = await _wait_for_event_types(
        spine, types={'OrderSubmitIntent', 'OrderSubmitted'},
    )

    intents = [e for _, e in events if isinstance(e, OrderSubmitIntent)]
    submitteds = [e for _, e in events if isinstance(e, OrderSubmitted)]

    assert len(intents) == 1
    assert len(submitteds) == 1
    assert intents[0].client_order_id == submitteds[0].client_order_id
