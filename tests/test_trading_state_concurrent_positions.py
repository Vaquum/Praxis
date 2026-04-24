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

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived, TradeClosed
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
        except BaseException as exc:  # noqa: BLE001
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
        except BaseException as exc:  # noqa: BLE001
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
