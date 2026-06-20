'''Tests for TD-052 boot outcome-replay reconstruction primitives.

The launcher's boot replay rebuilds the Nexus delivery `OrderContext`
and the Praxis `TradeOutcome` from their durable spine records and
re-runs `OutcomeTranslator` to derive the same deterministic Nexus
`outcome_id`s the live path produced, so an unacked outcome is
re-delivered with ids the Nexus durable dedup recognises.
'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from nexus.core.domain.enums import OrderSide as NexusOrderSide
from nexus.infrastructure.praxis_connector.order_context import OrderContext

from praxis.core.domain.enums import OrderSide, TradeStatus
from praxis.core.domain.events import (
    OutcomeAcked,
    OutcomeDeliveryContextRecorded,
    OutcomeReplayAbandoned,
    TradeOutcomeProduced,
)
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.launcher import (
    _DEFAULT_FEE_RATE,
    _apply_replay_plan,
    _order_context_from_recorded,
    _plan_outcome_replay,
    _trade_outcome_from_produced,
)
from praxis.outcome_translator import OutcomeTranslator

_TS = datetime(2026, 6, 20, tzinfo=UTC)


def test_order_context_round_trips_through_recorded_event() -> None:
    original = OrderContext(
        command_id='cmd-1',
        strategy_id='strat_a',
        trade_id='trade-1',
        side=NexusOrderSide.SELL,
        order_size=Decimal('0.5'),
        order_notional=Decimal('25000'),
        estimated_fees=Decimal('25'),
        is_entry=False,
        intended_full_close=True,
    )

    recorded = OutcomeDeliveryContextRecorded(
        account_id='acct-1',
        timestamp=_TS,
        command_id=original.command_id,
        side=OrderSide.SELL,
        is_entry=original.is_entry,
        order_notional=original.order_notional,
        estimated_fees=original.estimated_fees,
        strategy_id=original.strategy_id,
        trade_id=original.trade_id,
        order_size=original.order_size,
        intended_full_close=original.intended_full_close,
    )

    rebuilt = _order_context_from_recorded(recorded)

    assert rebuilt == original


def test_reconstructed_outcome_translates_to_live_ids() -> None:
    live_outcome = TradeOutcome(
        command_id='cmd-1',
        trade_id='trade-1',
        account_id='acct-1',
        status=TradeStatus.FILLED,
        target_qty=Decimal('2'),
        filled_qty=Decimal('2'),
        avg_fill_price=Decimal('100'),
        slices_completed=1,
        slices_total=1,
        reason=None,
        created_at=_TS,
        cumulative_notional=Decimal('200'),
    )

    produced = TradeOutcomeProduced(
        account_id='acct-1',
        timestamp=_TS,
        command_id='cmd-1',
        trade_id='trade-1',
        status=TradeStatus.FILLED,
        filled_qty=Decimal('2'),
        cumulative_notional=Decimal('200'),
        target_qty=Decimal('2'),
    )

    live_ids = [
        o.outcome_id
        for o in OutcomeTranslator(fee_rate=_DEFAULT_FEE_RATE).translate(live_outcome)
    ]
    replay_ids = [
        o.outcome_id
        for o in OutcomeTranslator(fee_rate=_DEFAULT_FEE_RATE).translate(
            _trade_outcome_from_produced(produced),
        )
    ]

    assert replay_ids == live_ids
    assert replay_ids == ['acct-1:cmd-1:ack', 'acct-1:cmd-1:filled']


def test_reconstructed_no_fill_outcome_has_no_avg_price() -> None:
    produced = TradeOutcomeProduced(
        account_id='acct-1',
        timestamp=_TS,
        command_id='cmd-1',
        trade_id='trade-1',
        status=TradeStatus.REJECTED,
        reason='rejected',
    )

    rebuilt = _trade_outcome_from_produced(produced)

    assert rebuilt.avg_fill_price is None
    assert rebuilt.filled_qty == Decimal('0')
    assert rebuilt.cumulative_notional == Decimal('0')


def _ctx_event(command_id: str, account_id: str = 'acct-1') -> OutcomeDeliveryContextRecorded:
    return OutcomeDeliveryContextRecorded(
        account_id=account_id,
        timestamp=_TS,
        command_id=command_id,
        side=OrderSide.BUY,
        is_entry=True,
        order_notional=Decimal('200'),
        estimated_fees=Decimal('0.2'),
        strategy_id='strat_a',
        trade_id='trade-1',
        order_size=None,
    )


def _produced_filled(command_id: str, account_id: str = 'acct-1') -> TradeOutcomeProduced:
    return TradeOutcomeProduced(
        account_id=account_id,
        timestamp=_TS,
        command_id=command_id,
        trade_id='trade-1',
        status=TradeStatus.FILLED,
        filled_qty=Decimal('2'),
        cumulative_notional=Decimal('200'),
        target_qty=Decimal('2'),
    )


def _acked(outcome_id: str, account_id: str = 'acct-1') -> OutcomeAcked:
    return OutcomeAcked(account_id=account_id, timestamp=_TS, outcome_id=outcome_id)


def _enumerate(events: list[object]) -> list[tuple[int, object]]:
    return list(enumerate(events))


def test_plan_replays_fully_unacked_command() -> None:
    events = _enumerate([_ctx_event('cmd-1'), _produced_filled('cmd-1')])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert [o.outcome_id for o, _ in plan] == [
        'acct-1:cmd-1:ack',
        'acct-1:cmd-1:filled',
    ]
    assert all(ctx.command_id == 'cmd-1' for _, ctx in plan)


def test_plan_skips_fully_acked_command() -> None:
    events = _enumerate([
        _ctx_event('cmd-1'),
        _produced_filled('cmd-1'),
        _acked('acct-1:cmd-1:ack'),
        _acked('acct-1:cmd-1:filled'),
    ])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert plan == []


def test_plan_replays_only_unacked_legs() -> None:
    events = _enumerate([
        _ctx_event('cmd-1'),
        _produced_filled('cmd-1'),
        _acked('acct-1:cmd-1:ack'),
    ])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert [o.outcome_id for o, _ in plan] == ['acct-1:cmd-1:filled']


def test_plan_skips_produced_without_context() -> None:
    events = _enumerate([_produced_filled('cmd-1')])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert plan == []


def test_plan_ignores_other_account_events() -> None:
    events = _enumerate([
        _ctx_event('cmd-2', account_id='acct-2'),
        _produced_filled('cmd-2', account_id='acct-2'),
    ])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert plan == []


def _produced(
    command_id: str,
    status: TradeStatus,
    filled_qty: Decimal,
    cumulative_notional: Decimal,
    target_qty: Decimal,
    account_id: str = 'acct-1',
) -> TradeOutcomeProduced:
    return TradeOutcomeProduced(
        account_id=account_id,
        timestamp=_TS,
        command_id=command_id,
        trade_id='trade-1',
        status=status,
        filled_qty=filled_qty,
        cumulative_notional=cumulative_notional,
        target_qty=target_qty,
    )


def test_plan_replays_partial_partial_filled_sequence() -> None:
    events = _enumerate([
        _ctx_event('cmd-1'),
        _produced('cmd-1', TradeStatus.PARTIAL, Decimal('1'), Decimal('100'), Decimal('3')),
        _produced('cmd-1', TradeStatus.PARTIAL, Decimal('2'), Decimal('200'), Decimal('3')),
        _produced('cmd-1', TradeStatus.FILLED, Decimal('3'), Decimal('300'), Decimal('3')),
    ])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert [o.outcome_id for o, _ in plan] == [
        'acct-1:cmd-1:ack',
        'acct-1:cmd-1:partial:0',
        'acct-1:cmd-1:partial:1',
        'acct-1:cmd-1:filled',
    ]


def test_plan_replays_only_unacked_legs_in_partial_sequence() -> None:
    events = _enumerate([
        _ctx_event('cmd-1'),
        _produced('cmd-1', TradeStatus.PARTIAL, Decimal('1'), Decimal('100'), Decimal('3')),
        _produced('cmd-1', TradeStatus.PARTIAL, Decimal('2'), Decimal('200'), Decimal('3')),
        _produced('cmd-1', TradeStatus.FILLED, Decimal('3'), Decimal('300'), Decimal('3')),
        _acked('acct-1:cmd-1:ack'),
        _acked('acct-1:cmd-1:partial:0'),
    ])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert [o.outcome_id for o, _ in plan] == [
        'acct-1:cmd-1:partial:1',
        'acct-1:cmd-1:filled',
    ]


def test_plan_preserves_global_spine_order_across_commands() -> None:
    events = _enumerate([
        _ctx_event('cmd-a'),
        _ctx_event('cmd-b'),
        _produced('cmd-a', TradeStatus.PARTIAL, Decimal('1'), Decimal('100'), Decimal('2')),
        _produced('cmd-b', TradeStatus.FILLED, Decimal('2'), Decimal('200'), Decimal('2')),
        _produced('cmd-a', TradeStatus.FILLED, Decimal('2'), Decimal('200'), Decimal('2')),
    ])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert [o.outcome_id for o, _ in plan] == [
        'acct-1:cmd-a:ack',
        'acct-1:cmd-a:partial:0',
        'acct-1:cmd-b:ack',
        'acct-1:cmd-b:filled',
        'acct-1:cmd-a:filled',
    ]


def test_plan_skips_abandoned_legs() -> None:
    events = _enumerate([
        _ctx_event('cmd-1'),
        _produced_filled('cmd-1'),
        _acked('acct-1:cmd-1:ack'),
        OutcomeReplayAbandoned(
            account_id='acct-1',
            timestamp=_TS,
            outcome_id='acct-1:cmd-1:filled',
            reason='order not found',
        ),
    ])

    plan = _plan_outcome_replay(events, 'acct-1', _DEFAULT_FEE_RATE)

    assert plan == []


class _StubResult:
    def __init__(self, success: bool, error_reason: str | None = None) -> None:
        self.success = success
        self.error_reason = error_reason


class _StubOutcome:
    def __init__(self, outcome_id: str) -> None:
        self.outcome_id = outcome_id


def test_apply_replay_plan_skips_raise_without_abandon() -> None:
    abandoned: list[tuple[str, str]] = []

    def _proc(_outcome: object, _ctx: object) -> _StubResult:
        raise RuntimeError('boom')

    # A raise is caught (does not propagate / wedge boot) but is NOT durably
    # abandoned — it may be transient and must be retried next boot.
    _apply_replay_plan(
        [(_StubOutcome('id-1'), None)],
        _proc,
        lambda oid, reason: abandoned.append((oid, reason)),
    )

    assert abandoned == []


def test_apply_replay_plan_abandons_on_failure() -> None:
    abandoned: list[tuple[str, str]] = []

    def _proc(_outcome: object, _ctx: object) -> _StubResult:
        return _StubResult(success=False, error_reason='order not found')

    _apply_replay_plan(
        [(_StubOutcome('id-1'), None)],
        _proc,
        lambda oid, reason: abandoned.append((oid, reason)),
    )

    assert abandoned == [('id-1', 'order not found')]


def test_apply_replay_plan_success_does_not_abandon() -> None:
    abandoned: list[tuple[str, str]] = []

    def _proc(_outcome: object, _ctx: object) -> _StubResult:
        return _StubResult(success=True)

    _apply_replay_plan(
        [(_StubOutcome('id-1'), None)],
        _proc,
        lambda oid, reason: abandoned.append((oid, reason)),
    )

    assert abandoned == []
