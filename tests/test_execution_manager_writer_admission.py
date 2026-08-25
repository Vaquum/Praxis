'''
Tests for the ExecutionManager writer-admission primitive (WP-Praxis-0010):
`admit` appends and projects an external event in one serialized writer turn,
closing the append-then-defer gap that `enqueue_ws_event` leaves open.
'''

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide, OrderType
from praxis.core.domain.events import (
    FillReceived,
    OrderCanceled,
    OrderSubmitIntent,
    OrderSubmitted,
)
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import (
    AccountNotRegisteredError,
    ExecutionManager,
)
from praxis.infrastructure.event_spine import EventSpine

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_EPOCH = 1
_TRADE = 't1'
_CMD = 'cmd-1'
_COID = 'coid-1'


def _manager(spine: EventSpine, outcomes: list[TradeOutcome]) -> ExecutionManager:
    async def _capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    return ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=None,
        on_trade_outcome=_capture,
        clock=lambda: _T0,
    )


def _fill(qty: Decimal, venue_trade_id: str = 'vt-1') -> FillReceived:
    return FillReceived(
        account_id=_ACCT, timestamp=_T0, client_order_id=_COID,
        venue_order_id='v-1', venue_trade_id=venue_trade_id, trade_id=_TRADE,
        command_id=_CMD, symbol='BTCUSDT', side=OrderSide.BUY, qty=qty,
        price=Decimal('100'), fee=Decimal('0'), fee_asset='USDT', is_maker=False,
    )


def _open_order(runtime: object) -> None:
    runtime.trading_state.apply(OrderSubmitIntent(
        account_id=_ACCT, timestamp=_T0, command_id=_CMD, trade_id=_TRADE,
        client_order_id=_COID, symbol='BTCUSDT', side=OrderSide.BUY,
        order_type=OrderType.LIMIT, qty=Decimal('1'), price=Decimal('100'),
    ))
    runtime.trading_state.apply(OrderSubmitted(
        account_id=_ACCT, timestamp=_T0, client_order_id=_COID, venue_order_id='v-1',
    ))


@pytest.mark.asyncio
async def test_admit_projects_synchronously_and_queues_dispatch(
    spine: EventSpine,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]

    seq = await em.admit(_ACCT, _fill(Decimal('0.4')))

    assert seq is not None
    assert runtime.trading_state.positions[(_TRADE, _ACCT)].qty == Decimal('0.4')
    assert runtime.dispatch_queue.qsize() == 1

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_dispatch_runs_on_writer_without_double_projecting(
    spine: EventSpine,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]

    await em.admit(_ACCT, _fill(Decimal('0.4')))
    assert runtime.dispatch_queue.qsize() == 1

    em.finish_account_startup(_ACCT)
    await asyncio.sleep(0.3)

    assert runtime.dispatch_queue.empty()
    assert runtime.trading_state.positions[(_TRADE, _ACCT)].qty == Decimal('0.4')

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_closes_the_projection_gap_enqueue_leaves_open(
    spine: EventSpine,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]

    enqueued = FillReceived(
        account_id=_ACCT, timestamp=_T0, client_order_id='coid-2',
        venue_order_id='v-2', venue_trade_id='vt-2', trade_id='t2',
        command_id='cmd-2', symbol='BTCUSDT', side=OrderSide.BUY,
        qty=Decimal('0.5'), price=Decimal('100'), fee=Decimal('0'),
        fee_asset='USDT', is_maker=False,
    )
    await spine.append(enqueued, _EPOCH)
    em.enqueue_ws_event(_ACCT, enqueued)

    await em.admit(_ACCT, _fill(Decimal('0.4')))

    assert runtime.trading_state.positions[(_TRADE, _ACCT)].qty == Decimal('0.4')
    assert ('t2', _ACCT) not in runtime.trading_state.positions

    await em._drain_ws_events(runtime)

    assert runtime.trading_state.positions[('t2', _ACCT)].qty == Decimal('0.5')

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_deduplicates_without_double_projecting(
    spine: EventSpine,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]

    first = await em.admit(_ACCT, _fill(Decimal('0.4'), venue_trade_id='vt-dup'))
    second = await em.admit(_ACCT, _fill(Decimal('0.4'), venue_trade_id='vt-dup'))

    assert first is not None
    assert second is None
    assert runtime.trading_state.positions[(_TRADE, _ACCT)].qty == Decimal('0.4')
    assert runtime.dispatch_queue.qsize() == 1

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_preserves_a_fill_that_precedes_a_terminal(
    spine: EventSpine,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]
    _open_order(runtime)

    await em.admit(_ACCT, _fill(Decimal('0.4')))
    await em.admit(_ACCT, OrderCanceled(
        account_id=_ACCT, timestamp=_T0, client_order_id=_COID,
        venue_order_id='v-1', reason='reconciled from venue',
    ))

    closed = runtime.trading_state.closed_orders[_COID]
    assert closed.filled_qty == Decimal('0.4')
    assert _COID not in runtime.trading_state.orders

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_raises_when_account_poisoned(spine: EventSpine) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    em._accounts[_ACCT].poisoned = True

    with pytest.raises(RuntimeError, match='poisoned'):
        await em.admit(_ACCT, _fill(Decimal('0.4')))

    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_raises_when_poisoned_during_append(spine: EventSpine) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]
    original_append = spine.append

    async def _append_then_poison(event: object, epoch: int) -> int | None:
        seq = await original_append(event, epoch)
        runtime.poisoned = True
        return seq

    spine.append = _append_then_poison

    with pytest.raises(RuntimeError, match='poisoned'):
        await em.admit(_ACCT, _fill(Decimal('0.4')))

    assert (_TRADE, _ACCT) not in runtime.trading_state.positions
    assert runtime.dispatch_queue.empty()

    spine.append = original_append
    runtime.poisoned = False
    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_fails_stop_even_when_poisoned_append_deduplicates(
    spine: EventSpine,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]
    fill = _fill(Decimal('0.4'), venue_trade_id='vt-dedup-poison')
    await em.admit(_ACCT, fill)

    original_append = spine.append

    async def _dedup_then_poison(event: object, epoch: int) -> int | None:
        seq = await original_append(event, epoch)
        runtime.poisoned = True
        return seq

    spine.append = _dedup_then_poison

    with pytest.raises(RuntimeError, match='poisoned'):
        await em.admit(_ACCT, fill)

    spine.append = original_append
    runtime.poisoned = False
    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_raises_when_account_detached_during_append(
    spine: EventSpine,
) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    runtime = em._accounts[_ACCT]
    original_append = spine.append

    async def _append_then_detach(event: object, epoch: int) -> int | None:
        seq = await original_append(event, epoch)
        em._accounts[_ACCT] = object()
        return seq

    spine.append = _append_then_detach

    with pytest.raises(AccountNotRegisteredError):
        await em.admit(_ACCT, _fill(Decimal('0.4')))

    assert (_TRADE, _ACCT) not in runtime.trading_state.positions
    assert runtime.dispatch_queue.empty()

    spine.append = original_append
    em._accounts[_ACCT] = runtime
    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_admit_rejects_calls_off_the_loop_thread(spine: EventSpine) -> None:
    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    em._loop_thread_id = -1

    with pytest.raises(RuntimeError, match='non-event-loop thread'):
        await em.admit(_ACCT, _fill(Decimal('0.4')))

    em._loop_thread_id = None
    await em.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_cross_path_fill_delivery_dedups_and_replays_equal(
    spine: EventSpine,
) -> None:
    '''The same trade delivered by two live paths counts once and replays equal.

    A fill reaches Praxis from the WebSocket stream and again from reconnect
    trade backfill; both carry the same venue trade id (Binance's per-symbol
    trade identifier) but differ in other fields. Dedup keys on
    `(epoch, account, symbol, venue_trade_id)`, so the second admit
    deduplicates and never projects: the position is booked once, the spine
    holds a single `FillReceived`, and a fresh account replaying the whole
    spine lands on the identical position.
    '''

    outcomes: list[TradeOutcome] = []
    em = _manager(spine, outcomes)
    em.register_account(_ACCT, booting=True)
    live = em._accounts[_ACCT]

    ws_fill = _fill(Decimal('0.5'), venue_trade_id='99')
    backfill_fill = FillReceived(
        account_id=_ACCT, timestamp=_T0, client_order_id=_COID,
        venue_order_id='rest-order', venue_trade_id='99', trade_id=_TRADE,
        command_id=_CMD, symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('0.5'),
        price=Decimal('100'), fee=Decimal('0'), fee_asset='USDT', is_maker=True,
    )

    replay_em: ExecutionManager | None = None
    try:
        ws_seq = await em.admit(_ACCT, ws_fill)
        backfill_seq = await em.admit(_ACCT, backfill_fill)

        assert ws_seq is not None
        assert backfill_seq is None
        live_position = live.trading_state.positions[(_TRADE, _ACCT)]
        assert live_position.qty == Decimal('0.5')

        full = await spine.read(epoch_id=_EPOCH)
        fills = [event for _seq, event in full if isinstance(event, FillReceived)]
        assert fills == [ws_fill]

        replay_em = _manager(spine, [])
        replay_em.register_account(_ACCT, booting=True)
        replay_em.replay_events(_ACCT, full)
        replay_position = replay_em._accounts[_ACCT].trading_state.positions[
            (_TRADE, _ACCT)
        ]

        assert replay_position == live_position
    finally:
        for manager in (em, replay_em):
            if manager is not None and _ACCT in manager._accounts:
                await manager.unregister_account(_ACCT)
