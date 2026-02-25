'''
Tests for praxis.core.trading_state.TradingState.
'''

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
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
from praxis.core.trading_state import TradingState

_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
_TS2 = datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
_ACCT = 'acc-1'
_CMD = 'cmd-1'
_TRADE = 'trade-1'
_ORDER = 'new_order-cmd1-0'
_SYMBOL = 'BTCUSDT'
_VENUE_OID = 'vo-001'
_VENUE_TID = 'vt-001'


def _state() -> TradingState:

    return TradingState(account_id=_ACCT)


def _submit_intent(
    client_order_id: str = _ORDER,
    qty: Decimal = Decimal('1'),
    price: Decimal = Decimal('50000'),
    side: OrderSide = OrderSide.BUY,
) -> OrderSubmitIntent:

    return OrderSubmitIntent(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=_CMD,
        trade_id=_TRADE,
        client_order_id=client_order_id,
        symbol=_SYMBOL,
        side=side,
        order_type=OrderType.LIMIT,
        qty=qty,
        price=price,
    )


def _submitted(client_order_id: str = _ORDER) -> OrderSubmitted:

    return OrderSubmitted(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
        venue_order_id=_VENUE_OID,
    )


def _submit_failed(client_order_id: str = _ORDER) -> OrderSubmitFailed:

    return OrderSubmitFailed(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
        reason='insufficient balance',
    )


def _acked(client_order_id: str = _ORDER) -> OrderAcked:

    return OrderAcked(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
        venue_order_id=_VENUE_OID,
    )


def _fill_event(
    client_order_id: str = _ORDER,
    qty: Decimal = Decimal('1'),
    price: Decimal = Decimal('50000'),
    side: OrderSide = OrderSide.BUY,
) -> FillReceived:

    return FillReceived(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
        venue_order_id=_VENUE_OID,
        venue_trade_id=_VENUE_TID,
        trade_id=_TRADE,
        command_id=_CMD,
        symbol=_SYMBOL,
        side=side,
        qty=qty,
        price=price,
        fee=Decimal('0.001'),
        fee_asset='BTC',
        is_maker=True,
    )


def _rejected(
    client_order_id: str = _ORDER,
    venue_order_id: str | None = None,
) -> OrderRejected:

    return OrderRejected(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
        venue_order_id=venue_order_id,
        reason='price too far',
    )


def _canceled(
    client_order_id: str = _ORDER,
    venue_order_id: str | None = None,
) -> OrderCanceled:

    return OrderCanceled(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
        venue_order_id=venue_order_id,
        reason='user request',
    )


def _expired(
    client_order_id: str = _ORDER,
    venue_order_id: str | None = None,
) -> OrderExpired:

    return OrderExpired(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
        venue_order_id=venue_order_id,
    )


def _trade_closed() -> TradeClosed:

    return TradeClosed(
        account_id=_ACCT,
        timestamp=_TS2,
        trade_id=_TRADE,
        command_id=_CMD,
    )


def _command_accepted() -> CommandAccepted:

    return CommandAccepted(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=_CMD,
        trade_id=_TRADE,
    )


@dataclass(frozen=True)
class _UnknownEvent:

    account_id: str = _ACCT
    timestamp: datetime = _TS


# --- apply dispatch ---


def test_command_accepted_is_noop() -> None:

    state = _state()
    state.apply(_command_accepted())
    assert state.orders == {}
    assert state.positions == {}


# --- order lifecycle ---


def test_submit_intent_creates_submitting_order() -> None:

    state = _state()
    state.apply(_submit_intent())
    order = state.orders[_ORDER]
    assert order.status == OrderStatus.SUBMITTING
    assert order.client_order_id == _ORDER
    assert order.symbol == _SYMBOL
    assert order.venue_order_id is None


def test_order_submitted_promotes_to_open() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_submitted())
    order = state.orders[_ORDER]
    assert order.status == OrderStatus.OPEN
    assert order.venue_order_id == _VENUE_OID


def test_order_submit_failed_rejects_and_closes() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_submit_failed())
    assert _ORDER not in state.orders
    assert state.closed_orders[_ORDER].status == OrderStatus.REJECTED


def test_order_acked_promotes_submitting_to_open() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_acked())
    order = state.orders[_ORDER]
    assert order.status == OrderStatus.OPEN
    assert order.venue_order_id == _VENUE_OID


def test_order_acked_does_not_regress_partially_filled() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('2')))
    state.apply(_fill_event(qty=Decimal('1')))
    state.apply(_acked())
    assert state.orders[_ORDER].status == OrderStatus.PARTIALLY_FILLED


def test_partial_fill_updates_order() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('2')))
    state.apply(_fill_event(qty=Decimal('1')))
    order = state.orders[_ORDER]
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.filled_qty == Decimal('1')


def test_full_fill_closes_order() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))
    assert _ORDER not in state.orders
    closed = state.closed_orders[_ORDER]
    assert closed.status == OrderStatus.FILLED
    assert closed.filled_qty == Decimal('1')


def test_order_rejected_closes() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_rejected())
    assert _ORDER not in state.orders
    assert state.closed_orders[_ORDER].status == OrderStatus.REJECTED


def test_order_canceled_closes() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_canceled())
    assert _ORDER not in state.orders
    assert state.closed_orders[_ORDER].status == OrderStatus.CANCELED


def test_order_expired_closes() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_expired())
    assert _ORDER not in state.orders
    assert state.closed_orders[_ORDER].status == OrderStatus.EXPIRED


def test_rejected_sets_venue_order_id() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_rejected(venue_order_id=_VENUE_OID))
    assert state.closed_orders[_ORDER].venue_order_id == _VENUE_OID


def test_canceled_sets_venue_order_id() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_canceled(venue_order_id=_VENUE_OID))
    assert state.closed_orders[_ORDER].venue_order_id == _VENUE_OID


def test_expired_sets_venue_order_id() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_expired(venue_order_id=_VENUE_OID))
    assert state.closed_orders[_ORDER].venue_order_id == _VENUE_OID


def test_order_updated_at_tracks_latest_event() -> None:

    state = _state()
    state.apply(_submit_intent())
    assert state.orders[_ORDER].updated_at == _TS
    state.apply(_acked())
    assert state.orders[_ORDER].updated_at == _TS2


# --- position tracking ---


def test_first_fill_creates_position() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_fill_event())
    key = (_TRADE, _ACCT)
    pos = state.positions[key]
    assert pos.symbol == _SYMBOL
    assert pos.side == OrderSide.BUY
    assert pos.qty == Decimal('1')
    assert pos.avg_entry_price == Decimal('50000')


def test_same_side_fill_computes_vwap() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('3')))
    state.apply(_fill_event(qty=Decimal('2'), price=Decimal('100')))
    state.apply(_fill_event(qty=Decimal('1'), price=Decimal('130')))
    key = (_TRADE, _ACCT)
    pos = state.positions[key]
    assert pos.qty == Decimal('3')
    assert pos.avg_entry_price == Decimal('110')


def test_opposite_side_fill_decreases_qty() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('2')))
    state.apply(_fill_event(qty=Decimal('2')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    assert state.positions[(_TRADE, _ACCT)].qty == Decimal('1')


def test_exit_fill_preserves_avg_entry_price() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('2')))
    state.apply(_fill_event(qty=Decimal('2'), price=Decimal('50000')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    state.apply(
        _fill_event(
            client_order_id=sell_oid,
            qty=Decimal('1'),
            side=OrderSide.SELL,
            price=Decimal('55000'),
        )
    )
    assert state.positions[(_TRADE, _ACCT)].avg_entry_price == Decimal('50000')


def test_trade_closed_removes_position() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_fill_event())
    key = (_TRADE, _ACCT)
    assert key in state.positions
    state.apply(_trade_closed())
    assert key not in state.positions


# --- warning logs ---


def test_warns_unknown_order_on_submitted(caplog: pytest.LogCaptureFixture) -> None:

    state = _state()
    with caplog.at_level(logging.WARNING):
        state.apply(_submitted())
    assert 'unknown order' in caplog.text


def test_warns_missing_position_on_trade_closed(caplog: pytest.LogCaptureFixture) -> None:

    state = _state()
    with caplog.at_level(logging.WARNING):
        state.apply(_trade_closed())
    assert 'no position for TradeClosed' in caplog.text


def test_warns_negative_qty_on_exit_fill(caplog: pytest.LogCaptureFixture) -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('2'), side=OrderSide.SELL))
    with caplog.at_level(logging.WARNING):
        state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('2'), side=OrderSide.SELL))
    assert 'position qty went negative' in caplog.text


def test_warns_close_order_unknown(caplog: pytest.LogCaptureFixture) -> None:

    state = _state()
    with caplog.at_level(logging.WARNING):
        state._close_order('nonexistent')
    assert 'close_order called for unknown order' in caplog.text


def test_warns_unhandled_event_type(caplog: pytest.LogCaptureFixture) -> None:

    state = _state()
    with caplog.at_level(logging.WARNING):
        state.apply(_UnknownEvent())  # type: ignore[arg-type]
    assert 'unhandled event type' in caplog.text


# --- full lifecycle ---


def test_full_lifecycle_submit_fill_close() -> None:

    state = _state()
    state.apply(_command_accepted())
    state.apply(_submit_intent(qty=Decimal('2')))
    state.apply(_acked())
    state.apply(_fill_event(qty=Decimal('1')))
    order = state.orders[_ORDER]
    assert order.status == OrderStatus.PARTIALLY_FILLED
    key = (_TRADE, _ACCT)
    assert state.positions[key].qty == Decimal('1')

    state.apply(_fill_event(qty=Decimal('1')))
    assert _ORDER not in state.orders
    assert state.closed_orders[_ORDER].status == OrderStatus.FILLED
    assert state.positions[key].qty == Decimal('2')

    state.apply(_trade_closed())
    assert key not in state.positions
