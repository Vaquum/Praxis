'''Stress test for PT-FIX-10: positions snapshot is thread-safe.

Pre-fix: `pull_positions` iterated `runtime.trading_state.positions.items()`
on the Nexus thread while the asyncio account loop mutated the same
dict on the loop thread. CPython's GIL makes single ops atomic but not
iteration; under load, intermittent
`RuntimeError: dictionary changed size during iteration` could fire
during startup reconciliation.

Post-fix: `TradingState.snapshot_positions()` iterates under
`_positions_lock`. `_update_position_on_fill` and `_on_trade_closed`
take the same lock around the dict-size mutations (insert and pop).
This stress test races a writer thread against many reader threads
and asserts no `RuntimeError` ever escapes.
'''

from __future__ import annotations

import threading
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived, TradeClosed
from praxis.core.domain.position import Position
from praxis.core.trading_state import TradingState

_TS = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)


def _fill(account_id: str, trade_id: str, qty: Decimal) -> FillReceived:
    return FillReceived(
        account_id=account_id,
        timestamp=_TS,
        venue_trade_id=f'venue-{trade_id}',
        venue_order_id=f'venue-order-{trade_id}',
        client_order_id=f'client-{trade_id}',
        trade_id=trade_id,
        command_id=f'cmd-{trade_id}',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        price=Decimal('100'),
        fee=Decimal('0'),
        fee_asset='USDT',
        is_maker=False,
    )


def _close(account_id: str, trade_id: str) -> TradeClosed:
    return TradeClosed(
        account_id=account_id,
        timestamp=_TS,
        trade_id=trade_id,
        command_id=f'cmd-{trade_id}',
    )


def test_snapshot_positions_under_concurrent_mutation() -> None:

    state = TradingState(account_id='acct-1')

    iterations = 500
    reader_count = 6

    errors: list[BaseException] = []
    error_lock = threading.Lock()
    stop_event = threading.Event()

    def writer() -> None:
        try:
            for i in range(iterations):
                trade_id = f'trade-{i}'
                state.apply(_fill('acct-1', trade_id, Decimal('1')))
                state.apply(_close('acct-1', trade_id))
        except BaseException as exc:
            with error_lock:
                errors.append(exc)
        finally:
            stop_event.set()

    def reader() -> None:
        try:
            while not stop_event.is_set():
                snapshot = state.snapshot_positions()
                for key, position in snapshot.items():
                    _ = position.symbol
                    _ = key
        except BaseException as exc:
            with error_lock:
                errors.append(exc)

    threads = [threading.Thread(target=reader, daemon=True) for _ in range(reader_count)]
    threads.append(threading.Thread(target=writer, daemon=True))

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f'concurrent access raised: {errors}'


def test_snapshot_returns_independent_copies() -> None:

    state = TradingState(account_id='acct-1')
    state.apply(_fill('acct-1', 'trade-1', Decimal('1')))

    snapshot = state.snapshot_positions()
    key = next(iter(snapshot))

    snapshot[key].qty = Decimal('999')

    assert state.positions[key].qty == Decimal('1')


def test_snapshot_after_close_excludes_closed_trade() -> None:

    state = TradingState(account_id='acct-1')
    state.apply(_fill('acct-1', 'trade-1', Decimal('1')))
    state.apply(_close('acct-1', 'trade-1'))

    snapshot = state.snapshot_positions()

    assert snapshot == {}


def _fill_at_price(account_id: str, trade_id: str, price: int) -> FillReceived:
    return FillReceived(
        account_id=account_id,
        timestamp=_TS,
        venue_trade_id=f'venue-{trade_id}-{price}',
        venue_order_id=f'venue-order-{trade_id}-{price}',
        client_order_id=f'client-{trade_id}-{price}',
        trade_id=trade_id,
        command_id=f'cmd-{trade_id}-{price}',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal(price),
        fee=Decimal('0'),
        fee_asset='USDT',
        is_maker=False,
    )


def test_field_update_branch_holds_positions_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    '''PT-FIX-23: `_update_position_on_fill` must hold `_positions_lock`
    around the field-mutation branch, not just the dict-insert branch.
    Pre-fix the lock was released after `self.positions.get(key)`, so
    a concurrent `snapshot_positions` could complete (and return a
    detached `copy.copy`) between the writer's `pos.avg_entry_price`
    assignment and `pos.qty` assignment — exposing a torn
    `(qty, avg_entry_price)` pair to consumers.

    Pre-loads a position, then patches `Position.__setattr__` to gate
    on a barrier between the two field assignments. With the fix
    holding the lock through the mutation, a parallel
    `snapshot_positions` call must block until the writer completes.
    Without the fix, the snapshot returns mid-update and the reader
    observes a torn (qty=old, avg=new) pair.'''

    state = TradingState(account_id='acct-1')
    state.apply(_fill_at_price('acct-1', 'trade-1', 100))

    mid_update = threading.Event()
    release_writer = threading.Event()
    original_setattr = Position.__setattr__

    def patched_setattr(self: Position, name: str, value: object) -> None:
        original_setattr(self, name, value)
        if name == 'avg_entry_price' and not mid_update.is_set():
            mid_update.set()
            release_writer.wait(timeout=5)

    monkeypatch.setattr(Position, '__setattr__', patched_setattr)

    snap_result: dict[str, object] = {}

    def writer() -> None:
        state.apply(_fill_at_price('acct-1', 'trade-1', 200))

    def reader() -> None:
        if not mid_update.wait(timeout=5):
            return

        snap_done = threading.Event()

        def _snapshot() -> None:
            snap_result['snapshot'] = state.snapshot_positions()
            snap_done.set()

        sub = threading.Thread(target=_snapshot, daemon=True)
        sub.start()
        snap_done.wait(timeout=0.5)
        snap_result['blocked_during_window'] = not snap_done.is_set()
        release_writer.set()
        sub.join(timeout=5)

    wt = threading.Thread(target=writer)
    rt = threading.Thread(target=reader)
    wt.start()
    rt.start()
    wt.join(timeout=10)
    rt.join(timeout=10)

    assert snap_result.get('blocked_during_window') is True, (
        'snapshot_positions completed while writer was mid-update — '
        '_update_position_on_fill is not holding _positions_lock around '
        'the field-mutation branch'
    )

    snapshot = snap_result.get('snapshot')
    assert isinstance(snapshot, dict) and snapshot, 'reader never produced a snapshot'
    position = next(iter(snapshot.values()))
    notional = position.qty * position.avg_entry_price
    assert notional == Decimal(300), (
        f'snapshot after writer completion is inconsistent: '
        f'qty={position.qty} avg={position.avg_entry_price} notional={notional}'
    )
