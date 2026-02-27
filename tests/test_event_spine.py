'''
Tests for praxis.infrastructure.event_spine.EventSpine.
'''

from __future__ import annotations
from dataclasses import replace

from datetime import datetime, timezone
from decimal import Decimal

import aiosqlite
import pytest
import pytest_asyncio

from praxis.core.domain.enums import OrderSide, OrderType
from praxis.core.domain.events import (
    CommandAccepted,
    FillReceived,
    OrderAcked,
    OrderCanceled,
    OrderExpired,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    TradeClosed,
)
from praxis.infrastructure.event_spine import EventSpine

_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
_ACCT = 'acc-1'
_CMD = 'cmd-1'
_TRADE = 'trade-1'
_ORDER = 'ord-1'
_SYMBOL = 'BTCUSDT'
_VORD = 'vo-001'
_VTRD = 'vt-001'
_EPOCH = 1

_ALL_EVENTS = [

    CommandAccepted(
        account_id=_ACCT, timestamp=_TS,
        command_id=_CMD, trade_id=_TRADE,
    ),

    OrderSubmitIntent(
        account_id=_ACCT, timestamp=_TS,
        command_id=_CMD, trade_id=_TRADE,
        client_order_id=_ORDER, symbol=_SYMBOL,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        qty=Decimal('1.5'), price=Decimal('50000.25'),
    ),

    OrderSubmitted(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, venue_order_id=_VORD,
    ),

    OrderSubmitFailed(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, reason='insufficient balance',
    ),

    OrderAcked(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, venue_order_id=_VORD,
    ),

    FillReceived(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, venue_order_id=_VORD,
        venue_trade_id=_VTRD, trade_id=_TRADE,
        command_id=_CMD, symbol=_SYMBOL,
        side=OrderSide.BUY, qty=Decimal('1.5'),
        price=Decimal('50000.25'), fee=Decimal('0.001'),
        fee_asset='USDT', is_maker=True,
    ),

    OrderRejected(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, venue_order_id=_VORD,
        reason='price too far',
    ),

    OrderCanceled(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, venue_order_id=None,
        reason=None,
    ),

    OrderExpired(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, venue_order_id=None,
    ),

    TradeClosed(
        account_id=_ACCT, timestamp=_TS,
        trade_id=_TRADE, command_id=_CMD,
    ),

]

_FILL = FillReceived(
    account_id=_ACCT, timestamp=_TS,
    client_order_id=_ORDER, venue_order_id=_VORD,
    venue_trade_id=_VTRD, trade_id=_TRADE,
    command_id=_CMD, symbol=_SYMBOL,
    side=OrderSide.BUY, qty=Decimal('1.5'),
    price=Decimal('50000.25'), fee=Decimal('0.001'),
    fee_asset='USDT', is_maker=True,
)

@pytest_asyncio.fixture
async def spine():

    async with aiosqlite.connect(':memory:') as conn:
        s = EventSpine(conn)
        await s.ensure_schema()
        yield s


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'event',
    _ALL_EVENTS,
    ids=[type(e).__name__ for e in _ALL_EVENTS],
)
async def test_event_spine_round_trip(event: object, spine: EventSpine):

    seq = await spine.append(event, epoch_id=_EPOCH)
    results = await spine.read(epoch_id=_EPOCH)
    assert len(results) == 1
    assert results[0][0] == seq
    hydrated = results[0][1]
    assert type(hydrated) is type(event)
    assert hydrated == event


@pytest.mark.asyncio
async def test_event_spine_epoch_isolation(spine: EventSpine):

    e = _ALL_EVENTS[0]
    await spine.append(e, epoch_id=1)
    await spine.append(e, epoch_id=2)

    r1 = await spine.read(epoch_id=1)
    r2 = await spine.read(epoch_id=2)
    assert len(r1) == 1
    assert len(r2) == 1
    assert r1[0][0] != r2[0][0]


@pytest.mark.asyncio
async def test_event_spine_ordering(spine: EventSpine):

    for event in _ALL_EVENTS:
        await spine.append(event, epoch_id=_EPOCH)

    results = await spine.read(epoch_id=_EPOCH)
    seqs = [r[0] for r in results]
    assert seqs == sorted(seqs)
    assert len(results) == len(_ALL_EVENTS)


@pytest.mark.asyncio
async def test_event_spine_last_event_seq(spine: EventSpine):

    assert await spine.last_event_seq(_EPOCH) is None

    e = _ALL_EVENTS[0]
    seq = await spine.append(e, epoch_id=_EPOCH)
    seq1 = await spine.last_event_seq(_EPOCH)
    assert seq1 == seq

    seq2 = await spine.append(e, epoch_id=_EPOCH)
    assert await spine.last_event_seq(_EPOCH) == seq2


@pytest.mark.asyncio
async def test_event_spine_last_event_seq_empty_epoch(spine: EventSpine):

    await spine.append(_ALL_EVENTS[0], epoch_id=1)
    assert await spine.last_event_seq(99) is None


@pytest.mark.asyncio
async def test_event_spine_decimal_precision(spine: EventSpine):

    event = FillReceived(
        account_id=_ACCT, timestamp=_TS,
        client_order_id=_ORDER, venue_order_id=_VORD,
        venue_trade_id=_VTRD, trade_id=_TRADE,
        command_id=_CMD, symbol=_SYMBOL,
        side=OrderSide.BUY,
        qty=Decimal('0.00000001'),
        price=Decimal('99999.99999999'),
        fee=Decimal('0.00000000001'),
        fee_asset='USDT', is_maker=False,
    )
    await spine.append(event, epoch_id=_EPOCH)
    results = await spine.read(epoch_id=_EPOCH)
    hydrated = results[0][1]
    assert isinstance(hydrated, FillReceived)
    assert hydrated.qty == Decimal('0.00000001')
    assert hydrated.price == Decimal('99999.99999999')
    assert hydrated.fee == Decimal('0.00000000001')


@pytest.mark.asyncio
async def test_event_spine_datetime_timezone_preserved(spine: EventSpine):

    event = CommandAccepted(
        account_id=_ACCT, timestamp=_TS,
        command_id=_CMD, trade_id=_TRADE,
    )
    await spine.append(event, epoch_id=_EPOCH)
    results = await spine.read(epoch_id=_EPOCH)
    hydrated = results[0][1]
    assert isinstance(hydrated, CommandAccepted)
    assert hydrated.timestamp == _TS
    assert hydrated.timestamp.tzinfo is not None
    assert hydrated.timestamp.utcoffset() is not None


@pytest.mark.asyncio
async def test_event_spine_enum_preserved(spine: EventSpine):

    event = OrderSubmitIntent(
        account_id=_ACCT, timestamp=_TS,
        command_id=_CMD, trade_id=_TRADE,
        client_order_id=_ORDER, symbol=_SYMBOL,
        side=OrderSide.SELL, order_type=OrderType.STOP_LIMIT,
        qty=Decimal('1'),
    )
    await spine.append(event, epoch_id=_EPOCH)
    results = await spine.read(epoch_id=_EPOCH)
    hydrated = results[0][1]
    assert isinstance(hydrated, OrderSubmitIntent)
    assert hydrated.side is OrderSide.SELL
    assert hydrated.order_type is OrderType.STOP_LIMIT


@pytest.mark.asyncio
async def test_event_spine_empty_read(spine: EventSpine):

    results = await spine.read(epoch_id=_EPOCH)
    assert results == []


@pytest.mark.asyncio
async def test_event_spine_after_seq_filtering(spine: EventSpine):

    for event in _ALL_EVENTS[:5]:
        await spine.append(event, epoch_id=_EPOCH)

    seqs = [r[0] for r in await spine.read(epoch_id=_EPOCH)]
    results = await spine.read(epoch_id=_EPOCH, after_seq=seqs[2])
    assert len(results) == len(seqs) - 3
    assert results[0][0] == seqs[3]
    assert results[1][0] == seqs[4]


@pytest.mark.asyncio
async def test_fill_dedup_first_append_returns_seq(spine: EventSpine):

    seq = await spine.append(_FILL, epoch_id=_EPOCH)
    assert isinstance(seq, int)


@pytest.mark.asyncio
async def test_fill_dedup_duplicate_returns_none(spine: EventSpine):

    await spine.append(_FILL, epoch_id=_EPOCH)
    result = await spine.append(_FILL, epoch_id=_EPOCH)
    assert result is None
    events = await spine.read(epoch_id=_EPOCH)
    assert len(events) == 1


@pytest.mark.asyncio
async def test_fill_dedup_different_trade_ids_both_append(spine: EventSpine):

    fill_b = replace(_FILL, venue_trade_id='vt-002')
    seq_a = await spine.append(_FILL, epoch_id=_EPOCH)
    seq_b = await spine.append(fill_b, epoch_id=_EPOCH)
    assert isinstance(seq_a, int)
    assert isinstance(seq_b, int)
    events = await spine.read(epoch_id=_EPOCH)
    assert len(events) == 2


@pytest.mark.asyncio
async def test_fill_dedup_same_trade_id_different_accounts(spine: EventSpine):

    fill_b = replace(_FILL, account_id='acc-2', side=OrderSide.SELL, is_maker=False)
    seq_a = await spine.append(_FILL, epoch_id=_EPOCH)
    seq_b = await spine.append(fill_b, epoch_id=_EPOCH)
    assert isinstance(seq_a, int)
    assert isinstance(seq_b, int)
    events = await spine.read(epoch_id=_EPOCH)
    assert len(events) == 2


@pytest.mark.asyncio
async def test_fill_dedup_epoch_scoped(spine: EventSpine):

    seq_1 = await spine.append(_FILL, epoch_id=1)
    seq_2 = await spine.append(_FILL, epoch_id=2)
    assert isinstance(seq_1, int)
    assert isinstance(seq_2, int)


@pytest.mark.asyncio
async def test_fill_dedup_non_fill_events_unaffected(spine: EventSpine):

    event = CommandAccepted(
        account_id=_ACCT, timestamp=_TS,
        command_id=_CMD, trade_id=_TRADE,
    )
    seq_1 = await spine.append(event, epoch_id=_EPOCH)
    seq_2 = await spine.append(event, epoch_id=_EPOCH)
    assert isinstance(seq_1, int)
    assert isinstance(seq_2, int)
    events = await spine.read(epoch_id=_EPOCH)
    assert len(events) == 2


@pytest.mark.asyncio
async def test_fill_dedup_table_populated(spine: EventSpine):

    await spine.append(_FILL, epoch_id=_EPOCH)
    cursor = await spine._conn.execute(
        'SELECT epoch_id, account_id, dedup_key FROM fill_dedup'
    )
    rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0] == (_EPOCH, _ACCT, _VTRD)
