'''
Tests for the scheme-state events, their spine round-trip, and the
ExecutionScheme projection (WP-Praxis-0007 item 3).
'''

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal

import pytest

from praxis.core.domain.enums import SchemeState, ExecutionMode, OrderSide
from praxis.core.domain.events import SchemeInitialized, SchemeStateChanged
from praxis.core.trading_state import TradingState
from praxis.infrastructure.event_spine import EventSpine

_TS = datetime(2026, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_EPOCH = 1


def _init() -> SchemeInitialized:
    return SchemeInitialized(
        account_id=_ACCT,
        timestamp=_TS,
        command_id='cmd-1',
        trade_id='t-1',
        execution_mode=ExecutionMode.TWAP,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        total_qty=Decimal('1'),
        slices_total=4,
    )


def _changed(
    *,
    cursor: int = 1,
    filled: str = '0.25',
    state: SchemeState = SchemeState.RUNNING,
) -> SchemeStateChanged:
    return SchemeStateChanged(
        account_id=_ACCT,
        timestamp=_TS,
        command_id='cmd-1',
        cursor=cursor,
        filled_qty=Decimal(filled),
        active_client_order_ids=('TW-cmd-1-000',),
        next_run_at=_TS,
        state=state,
    )


def test_scheme_initialized_rejects_non_positive_total() -> None:
    with pytest.raises(ValueError, match='total_qty'):
        SchemeInitialized(
            account_id=_ACCT,
            timestamp=_TS,
            command_id='c',
            trade_id='t',
            execution_mode=ExecutionMode.TWAP,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            total_qty=Decimal('0'),
            slices_total=4,
        )


def test_scheme_initialized_rejects_single_shot() -> None:
    with pytest.raises(ValueError, match='SINGLE_SHOT'):
        SchemeInitialized(
            account_id=_ACCT,
            timestamp=_TS,
            command_id='c',
            trade_id='t',
            execution_mode=ExecutionMode.SINGLE_SHOT,
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            total_qty=Decimal('1'),
            slices_total=4,
        )


def test_scheme_state_changed_coerces_client_ids_to_tuple() -> None:
    event = SchemeStateChanged(
        account_id=_ACCT,
        timestamp=_TS,
        command_id='c',
        cursor=0,
        filled_qty=Decimal('0'),
        active_client_order_ids=['a', 'b'],  # type: ignore[arg-type]
        next_run_at=None,
        state=SchemeState.RUNNING,
    )

    assert isinstance(event.active_client_order_ids, tuple)
    assert event.active_client_order_ids == ('a', 'b')


@pytest.mark.asyncio
async def test_scheme_events_round_trip_through_spine(spine: EventSpine) -> None:
    await spine.append(_init(), _EPOCH)
    await spine.append(_changed(), _EPOCH)

    events = await spine.read(_EPOCH, after_seq=0)
    by_type = {type(event).__name__: event for _seq, event in events}

    assert set(by_type) == {'SchemeInitialized', 'SchemeStateChanged'}

    init = by_type['SchemeInitialized']
    assert init.execution_mode is ExecutionMode.TWAP
    assert init.total_qty == Decimal('1')
    assert init.slices_total == 4

    changed = by_type['SchemeStateChanged']
    assert isinstance(changed.active_client_order_ids, tuple)
    assert changed.active_client_order_ids == ('TW-cmd-1-000',)
    assert changed.next_run_at == _TS
    assert changed.state is SchemeState.RUNNING
    assert changed.filled_qty == Decimal('0.25')


def test_projection_creates_and_updates_scheme() -> None:
    state = TradingState(_ACCT)
    state.apply(_init())

    scheme = state.schemes['cmd-1']
    assert scheme.execution_mode is ExecutionMode.TWAP
    assert scheme.state is SchemeState.RUNNING
    assert scheme.slices_total == 4

    state.apply(_changed(cursor=2, filled='0.5', state=SchemeState.COMPLETED))
    assert scheme.cursor == 2
    assert scheme.filled_qty == Decimal('0.5')
    assert scheme.active_client_order_ids == ('TW-cmd-1-000',)
    assert scheme.is_terminal


def test_projection_ignores_state_change_for_unknown_command() -> None:
    state = TradingState(_ACCT)
    state.apply(_changed())

    assert 'cmd-1' not in state.schemes


def test_duplicate_scheme_initialized_preserves_progress() -> None:
    state = TradingState(_ACCT)
    state.apply(_init())
    state.apply(_changed(cursor=3, filled='0.75'))
    state.apply(_init())

    scheme = state.schemes['cmd-1']
    assert scheme.cursor == 3
    assert scheme.filled_qty == Decimal('0.75')
