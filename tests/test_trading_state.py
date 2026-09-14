'''
Tests for praxis.core.trading_state.TradingState.
'''

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.core.domain.events import (
    CommandAccepted,
    FillReceived,
    OperatorHaltRequested,
    OperatorResumeRequested,
    OrderAcked,
    OrderCanceled,
    OrderExpired,
    OrderQuoteNativeFilled,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    OutcomeAcked,
    TradeClosed,
)
from praxis.core.trading_state import TradingState

_TS = datetime(2026, 1, 1, tzinfo=UTC)
_TS2 = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
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
    fee: Decimal = Decimal('0'),
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
        fee=fee,
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


def _command_accepted(strategy_id: str | None = None) -> CommandAccepted:

    return CommandAccepted(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=_CMD,
        trade_id=_TRADE,
        strategy_id=strategy_id,
    )


@dataclass(frozen=True)
class _UnknownEvent:

    account_id: str = _ACCT
    timestamp: datetime = _TS


def test_rejects_empty_account_id() -> None:

    with pytest.raises(ValueError, match='non-empty'):
        TradingState(account_id='')


def test_command_accepted_without_strategy_records_nothing() -> None:

    state = _state()
    state.apply(_command_accepted())
    assert state.orders == {}
    assert state.positions == {}
    assert state.trade_strategy_ids == {}


def test_command_accepted_records_strategy_attribution() -> None:

    state = _state()
    state.apply(_command_accepted(strategy_id='strat_001'))

    assert state.trade_strategy_ids == {_TRADE: 'strat_001'}
    assert state.orders == {}
    assert state.positions == {}


def test_replayed_command_accepted_attributes_the_opened_position() -> None:

    state = _state()
    state.apply(_command_accepted(strategy_id='strat_001'))
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))

    assert state.positions[(_TRADE, _ACCT)].strategy_id == 'strat_001'


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


def test_order_submitted_records_oco_leg_parent() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(
        OrderSubmitted(
            account_id=_ACCT,
            timestamp=_TS2,
            client_order_id=_ORDER,
            venue_order_id=_VENUE_OID,
            leg_client_order_ids=('leg-a', 'leg-b'),
        ),
    )
    assert state.oco_leg_parent == {'leg-a': _ORDER, 'leg-b': _ORDER}


def test_order_submitted_without_legs_leaves_map_empty() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_submitted())
    assert state.oco_leg_parent == {}


def test_oco_leg_mappings_persist_after_parent_close() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(
        OrderSubmitted(
            account_id=_ACCT,
            timestamp=_TS2,
            client_order_id=_ORDER,
            venue_order_id=_VENUE_OID,
            leg_client_order_ids=('leg-a', 'leg-b'),
        ),
    )
    assert state.oco_leg_parent == {'leg-a': _ORDER, 'leg-b': _ORDER}
    assert state.oco_parent_legs == {_ORDER: ('leg-a', 'leg-b')}

    state.apply(_canceled())

    assert _ORDER in state.closed_orders
    assert state.oco_leg_parent == {'leg-a': _ORDER, 'leg-b': _ORDER}
    assert state.oco_parent_legs == {_ORDER: ('leg-a', 'leg-b')}


def test_order_submit_failed_rejects_and_closes() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_submit_failed())
    assert _ORDER not in state.orders
    assert state.closed_orders[_ORDER].status == OrderStatus.REJECTED


def test_order_acked_is_retained_but_not_projected() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_acked())
    order = state.orders[_ORDER]
    assert order.status == OrderStatus.SUBMITTING
    assert order.venue_order_id is None


def test_exempt_telemetry_events_are_silent_no_ops(
    caplog: pytest.LogCaptureFixture,
) -> None:

    state = _state()
    with caplog.at_level(logging.WARNING):
        state.apply(OperatorHaltRequested(
            account_id=_ACCT, timestamp=_TS, reason='operator halt',
        ))
        state.apply(OperatorResumeRequested(
            account_id=_ACCT, timestamp=_TS, reason='operator resume',
        ))
        state.apply(OutcomeAcked(
            account_id=_ACCT, timestamp=_TS, outcome_id='outcome-1',
        ))

    assert state.orders == {}
    assert state.positions == {}
    assert not any(
        'unhandled event type' in record.getMessage() for record in caplog.records
    )


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


def _quote_native_submit_intent(
    client_order_id: str = _ORDER,
    quote_qty: Decimal = Decimal('100'),
) -> OrderSubmitIntent:

    return OrderSubmitIntent(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=_CMD,
        trade_id=_TRADE,
        client_order_id=client_order_id,
        symbol=_SYMBOL,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=None,
        quote_qty=quote_qty,
    )


def _quote_native_filled(
    client_order_id: str = _ORDER,
) -> OrderQuoteNativeFilled:

    return OrderQuoteNativeFilled(
        account_id=_ACCT,
        timestamp=_TS2,
        client_order_id=client_order_id,
    )


def test_quote_native_submit_intent_creates_order_with_none_qty() -> None:

    state = _state()
    state.apply(_quote_native_submit_intent())
    order = state.orders[_ORDER]
    assert order.qty is None
    assert order.quote_qty == Decimal('100')
    assert order.is_quote_native is True


def test_quote_native_fill_stays_partially_filled() -> None:

    state = _state()
    state.apply(_quote_native_submit_intent())
    state.apply(_fill_event(qty=Decimal('0.001'), price=Decimal('50000')))
    order = state.orders[_ORDER]
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert _ORDER in state.orders


def test_quote_native_filled_event_closes_order() -> None:

    state = _state()
    state.apply(_quote_native_submit_intent())
    state.apply(_fill_event(qty=Decimal('0.001'), price=Decimal('50000')))
    state.apply(_quote_native_filled())
    assert _ORDER not in state.orders
    closed = state.closed_orders[_ORDER]
    assert closed.status == OrderStatus.FILLED


def test_quote_native_filled_replay_is_idempotent() -> None:

    state = _state()
    state.apply(_quote_native_submit_intent())
    state.apply(_fill_event(qty=Decimal('0.001'), price=Decimal('50000')))
    state.apply(_quote_native_filled())
    state.apply(_quote_native_filled())
    closed = state.closed_orders[_ORDER]
    assert closed.status == OrderStatus.FILLED


def test_quote_native_filled_replay_does_not_warn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    '''Second apply of `OrderQuoteNativeFilled` after the order is
    already in `closed_orders` is a silent no-op. The handler short-
    circuits on `client_order_id in self.closed_orders` rather than
    falling through to `_get_order` which would log
    `unknown order in OrderQuoteNativeFilled` for a benign duplicate
    replay.
    '''

    state = _state()
    state.apply(_quote_native_submit_intent())
    state.apply(_fill_event(qty=Decimal('0.001'), price=Decimal('50000')))
    state.apply(_quote_native_filled())

    with caplog.at_level(logging.WARNING):
        state.apply(_quote_native_filled())

    assert 'unknown order' not in caplog.text


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
    state.apply(_submitted())
    assert state.orders[_ORDER].updated_at == _TS2


def test_position_created_on_first_fill() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_fill_event())
    key = (_TRADE, _ACCT)
    pos = state.positions[key]
    assert pos.symbol == _SYMBOL
    assert pos.side == OrderSide.BUY
    assert pos.qty == Decimal('1')
    assert pos.avg_entry_price == Decimal('50000')


def test_position_vwap_on_same_side_fill() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('3')))
    state.apply(_fill_event(qty=Decimal('2'), price=Decimal('100')))
    state.apply(_fill_event(qty=Decimal('1'), price=Decimal('130')))
    key = (_TRADE, _ACCT)
    pos = state.positions[key]
    assert pos.qty == Decimal('3')
    assert pos.avg_entry_price == Decimal('110')


def test_position_qty_decreases_on_opposite_fill() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('2')))
    state.apply(_fill_event(qty=Decimal('2')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    assert state.positions[(_TRADE, _ACCT)].qty == Decimal('1')


def test_position_avg_price_preserved_on_exit_fill() -> None:

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


def test_position_removed_on_trade_closed() -> None:

    state = _state()
    state.apply(_submit_intent())
    state.apply(_fill_event())
    key = (_TRADE, _ACCT)
    assert key in state.positions
    state.apply(_trade_closed())
    assert key not in state.positions


def test_warns_unknown_order_on_submitted(caplog: pytest.LogCaptureFixture) -> None:

    state = _state()
    with caplog.at_level(logging.WARNING):
        state.apply(_submitted())
    assert 'unknown order' in caplog.text


def test_logs_missing_position_on_trade_closed_at_debug(caplog: pytest.LogCaptureFixture) -> None:

    state = _state()
    with caplog.at_level(logging.DEBUG):
        state.apply(_trade_closed())
    assert 'no position for TradeClosed' in caplog.text
    debug_records = [r for r in caplog.records if 'no position for TradeClosed' in r.getMessage()]
    assert all(r.levelno == logging.DEBUG for r in debug_records)


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


def test_full_lifecycle_submit_fill_close() -> None:

    state = _state()
    state.apply(_command_accepted())
    state.apply(_submit_intent(qty=Decimal('2')))
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


def test_cumulative_notional_accumulates_on_fills() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('3')))

    state.apply(_fill_event(qty=Decimal('1'), price=Decimal('50000')))
    order = state.orders[_ORDER]
    assert order.cumulative_notional == Decimal('50000')

    state.apply(_fill_event(qty=Decimal('1'), price=Decimal('51000')))
    assert order.cumulative_notional == Decimal('101000')

    state.apply(_fill_event(qty=Decimal('1'), price=Decimal('52000')))
    assert state.closed_orders[_ORDER].cumulative_notional == Decimal('153000')


def test_vwap_computed_from_cumulative_notional() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('2')))

    state.apply(_fill_event(qty=Decimal('1'), price=Decimal('50000')))
    state.apply(_fill_event(qty=Decimal('1'), price=Decimal('52000')))

    order = state.closed_orders[_ORDER]
    vwap = order.cumulative_notional / order.filled_qty
    assert vwap == Decimal('51000')


def test_position_removed_when_ws_exit_drives_qty_to_zero() -> None:
    '''Opposite-side fill that exactly closes the position must `del`
    the entry. `_on_trade_closed` is the only other deletion path
    and only fires on `_build_outcome` emissions, not on WS-driven
    `FillReceived`.
    '''

    state = _state()
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))

    assert (_TRADE, _ACCT) not in state.positions


def test_trade_strategy_id_removed_when_ws_exit_drives_qty_to_zero() -> None:
    state = _state()
    state.trade_strategy_ids[_TRADE] = 'strat_001'
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))

    assert _TRADE not in state.trade_strategy_ids


def test_position_remains_on_partial_close() -> None:
    '''Partial close (event.qty < pos.qty) leaves the position in place
    with the decremented qty.'''

    state = _state()
    state.apply(_submit_intent(qty=Decimal('2')))
    state.apply(_fill_event(qty=Decimal('2')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))

    assert (_TRADE, _ACCT) in state.positions
    assert state.positions[(_TRADE, _ACCT)].qty == Decimal('1')


def test_position_removed_on_overclose() -> None:
    '''When event.qty > pos.qty, qty clamps to zero AND the entry is
    deleted (defensive — overclose should never happen but if it does,
    leaving a zombie is worse than deleting).'''

    state = _state()
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('2'), side=OrderSide.SELL))
    state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('2'), side=OrderSide.SELL))

    assert (_TRADE, _ACCT) not in state.positions


def test_snapshot_positions_excludes_ws_closed_position() -> None:
    '''`snapshot_positions` (consumed by the Nexus-side boot
    reconciler) must not expose a position closed via the WS path —
    a stale entry here drives the per-strategy attribution mismatch
    denial on the next Nexus boot.'''

    state = _state()
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))
    sell_oid = 'sell-order-1'
    state.apply(_submit_intent(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))
    state.apply(_fill_event(client_order_id=sell_oid, qty=Decimal('1'), side=OrderSide.SELL))

    snapshot = state.snapshot_positions()
    assert snapshot == {}


def test_apply_reconciliation_mismatch_is_noop(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from praxis.core.domain.events import ReconciliationMismatch

    state = _state()
    with caplog.at_level(logging.WARNING):
        state.apply(
            ReconciliationMismatch(
                account_id=_ACCT,
                timestamp=_TS,
                reconciliation_mismatch_id='recon-1',
                asset='USDT',
                expected=Decimal('1000'),
                actual=Decimal('995'),
            ),
        )

    assert 'unhandled event type' not in caplog.text


def test_late_fill_on_a_closed_order_books_without_reopening_it() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_canceled())
    closed = state.closed_orders[_ORDER]

    assert closed.status == OrderStatus.CANCELED
    assert closed.filled_qty == Decimal('0')

    state.apply(_fill_event(qty=Decimal('0.25')))

    assert _ORDER not in state.orders
    assert closed.status == OrderStatus.CANCELED
    assert closed.filled_qty == Decimal('0.25')
    assert closed.cumulative_notional == Decimal('0.25') * Decimal('50000')


def test_late_fill_on_a_filled_order_does_not_close_it_twice() -> None:

    state = _state()
    state.apply(_submit_intent(qty=Decimal('1')))
    state.apply(_fill_event(qty=Decimal('1')))
    closed = state.closed_orders[_ORDER]

    state.apply(_fill_event(qty=Decimal('0.5')))

    assert closed.status == OrderStatus.FILLED
    assert closed.filled_qty == Decimal('1.5')


def test_a_buy_position_is_net_of_its_base_commission() -> None:

    '''A position must say what the account holds, not what the venue quoted.

    A spot venue charges a taker commission in the asset the trade
    receives, so a buy reporting a gross quantity delivers `qty - fee`.
    Crediting the gross quantity put the position above the wallet by the
    commission on every buy, and `AccountLedger` already nets it out of its
    lots, so the two disagreed about the same trade.
    '''

    state = TradingState(_ACCT)
    state.apply(_fill_event(qty=Decimal('1'), fee=Decimal('0.001')))

    pos = state.positions[(_TRADE, _ACCT)]

    assert pos.qty == Decimal('0.999')


def test_a_sell_position_is_not_reduced_by_a_quote_commission() -> None:

    '''A sell's commission is quote, so its base leg is exact.

    Netting it out of the base quantity would under-reduce the position and
    leave a residue that never closes.
    '''

    state = TradingState(_ACCT)
    state.apply(_fill_event(qty=Decimal('2')))
    state.apply(
        _fill_event(
            client_order_id='sell-1', qty=Decimal('2'),
            side=OrderSide.SELL,
        ),
    )

    assert (_TRADE, _ACCT) not in state.positions


def test_selling_what_is_held_closes_the_position() -> None:

    '''The defect this prevents: a full close leaving a phantom remainder.

    Buying 1 and selling everything the account received used to leave the
    commission behind as an open position above the lot step, so the trade
    stayed open against inventory that no longer existed.
    '''

    state = TradingState(_ACCT)
    state.apply(_fill_event(qty=Decimal('1'), fee=Decimal('0.001')))

    held = state.positions[(_TRADE, _ACCT)].qty

    state.apply(
        _fill_event(client_order_id='sell-1', qty=held, side=OrderSide.SELL),
    )

    assert (_TRADE, _ACCT) not in state.positions, (
        'selling the full held quantity left a position open'
    )


def test_an_exactly_emptied_position_is_reported_once() -> None:

    '''The close marker must fire once and only for a real emptying.

    A reducing fill that lands exactly on zero removes the position, so the
    close cannot be recognised from the projection afterwards. Treating
    every absent position as closed would report a close for a trade that
    never opened one, so the emptying itself is what is recorded, and the
    durable close is what retires it.
    '''

    state = TradingState(_ACCT)
    state.apply(_fill_event(qty=Decimal('1')))
    state.apply(
        _fill_event(
            client_order_id='sell-1', qty=Decimal('1'), side=OrderSide.SELL,
        ),
    )

    assert (_TRADE, _ACCT) not in state.positions
    assert state.has_emptied_marker(_TRADE, _ACCT) is True

    # Reading does not retire it: an append that fails must leave the close
    # to be produced on the next attempt rather than lose it with the read.
    assert state.has_emptied_marker(_TRADE, _ACCT) is True

    state.apply(TradeClosed(
        account_id=_ACCT, timestamp=_TS2, trade_id=_TRADE, command_id=_CMD,
    ))

    assert state.has_emptied_marker(_TRADE, _ACCT) is False


def test_a_trade_that_never_opened_reports_no_close() -> None:

    state = TradingState(_ACCT)

    assert state.has_emptied_marker('trade-never', _ACCT) is False


def test_a_partial_reduction_sets_no_close_marker() -> None:

    state = TradingState(_ACCT)
    state.apply(_fill_event(qty=Decimal('2')))
    state.apply(
        _fill_event(
            client_order_id='sell-1', qty=Decimal('1'), side=OrderSide.SELL,
        ),
    )

    assert state.has_emptied_marker(_TRADE, _ACCT) is False


def test_a_replayed_close_retires_its_own_marker() -> None:

    '''Replaying a completed close must not leave a second one owed.

    Replay reprojects the fill that emptied the position, setting the
    marker again, and then reprojects the close that already answered it.
    The close retiring its own marker is what keeps a rebuilt history from
    producing a duplicate.
    '''

    state = TradingState(_ACCT)
    state.apply(_fill_event(qty=Decimal('1')))
    state.apply(
        _fill_event(
            client_order_id='sell-1', qty=Decimal('1'), side=OrderSide.SELL,
        ),
    )
    state.apply(TradeClosed(
        account_id=_ACCT, timestamp=_TS2, trade_id=_TRADE, command_id=_CMD,
    ))

    assert (_TRADE, _ACCT) not in state.positions
    assert state.has_emptied_marker(_TRADE, _ACCT) is False


def test_a_close_lost_to_a_crash_is_still_owed_after_replay() -> None:

    '''A history ending between the fill and its close still owes one.

    The reducing fill is durable and the close is not — the crash window.
    Clearing markers wholesale at the end of replay closed the duplicate
    case and silently discarded this one, leaving the ledger's trade open
    with nothing left to reopen it.
    '''

    state = TradingState(_ACCT)
    state.apply(_fill_event(qty=Decimal('1')))
    state.apply(
        _fill_event(
            client_order_id='sell-1', qty=Decimal('1'), side=OrderSide.SELL,
        ),
    )

    assert (_TRADE, _ACCT) not in state.positions
    assert state.has_emptied_marker(_TRADE, _ACCT) is True


def test_an_order_accumulates_the_commission_charged_in_base() -> None:

    '''An order must record what it was charged in the asset it received.

    Exposure is reconstructed from order totals — how much of an entry is
    still held, how much a protective amend must cover, whether an exit
    closed it. Those totals report what the venue filled, and a buy delivers
    less, so without the commission beside them a fully exited trade looks
    to be holding the fee and is routed into flattening for it.
    '''

    state = TradingState(_ACCT)
    state.apply(_submit_intent())
    state.apply(_submitted())
    state.apply(_fill_event(qty=Decimal('1'), fee=Decimal('0.001')))

    order = state.orders.get(_ORDER) or state.closed_orders.get(_ORDER)

    assert order is not None
    assert order.filled_qty == Decimal('1')
    assert order.base_fee == Decimal('0.001')
    assert order.filled_qty - order.base_fee == Decimal('0.999')


def test_a_sell_records_no_base_commission() -> None:

    '''A sell is charged in quote, so its base leg is exact.'''

    state = TradingState(_ACCT)
    state.apply(_submit_intent())
    state.apply(_submitted())
    state.apply(
        _fill_event(qty=Decimal('1'), side=OrderSide.SELL, fee=Decimal('5')),
    )

    order = state.orders.get(_ORDER) or state.closed_orders.get(_ORDER)

    assert order is not None
    assert order.base_fee == Decimal('0')
