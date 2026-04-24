'''Tests for the Praxis -> Nexus `TradeOutcome` translator (PT-FIX-6).

Pre-fix: `Trading.route_outcome` put Praxis-shape `TradeOutcome` directly
into the per-account queue. Nexus `OutcomeLoop._dispatch` and
`ShutdownSequencer._poll_until_terminal` expect Nexus-shape `TradeOutcome`
(`outcome_id`, `outcome_type`, `fill_size`, ...). The first outcome
routed at runtime raised `AttributeError` on `outcome.outcome_type`.

Post-fix: the launcher installs `OutcomeTranslator` as the seam. Each
Praxis aggregate `TradeOutcome` is converted into zero or more
Nexus-shape outcomes covering the lifecycle (`ACK`, `PARTIAL`,
`FILLED`, `REJECTED`, `EXPIRED`, `CANCELED`) with delta-derived fill
fields.
'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from nexus.infrastructure.praxis_connector.trade_outcome_type import (
    TradeOutcomeType,
)

from praxis.core.domain.enums import TradeStatus
from praxis.core.domain.trade_outcome import TradeOutcome as PraxisTradeOutcome
from praxis.outcome_translator import OutcomeTranslator

_TS = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)


def _praxis_outcome(
    *,
    command_id: str = 'cmd-1',
    status: TradeStatus,
    target_qty: Decimal = Decimal('1'),
    filled_qty: Decimal = Decimal('0'),
    avg_fill_price: Decimal | None = None,
    reason: str | None = None,
) -> PraxisTradeOutcome:

    return PraxisTradeOutcome(
        command_id=command_id,
        trade_id='trade-1',
        account_id='acct-1',
        status=status,
        target_qty=target_qty,
        filled_qty=filled_qty,
        avg_fill_price=avg_fill_price,
        slices_completed=1,
        slices_total=1,
        reason=reason,
        created_at=_TS,
    )


def test_pending_emits_single_ack() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(_praxis_outcome(status=TradeStatus.PENDING))

    assert len(result) == 1
    assert result[0].outcome_type == TradeOutcomeType.ACK
    assert result[0].command_id == 'cmd-1'
    assert result[0].fill_size is None


def test_repeated_pending_does_not_re_emit_ack() -> None:

    translator = OutcomeTranslator()

    first = translator.translate(_praxis_outcome(status=TradeStatus.PENDING))
    second = translator.translate(_praxis_outcome(status=TradeStatus.PENDING))

    assert len(first) == 1
    assert second == []


def test_immediate_full_fill_emits_ack_then_filled() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('2'),
            filled_qty=Decimal('2'),
            avg_fill_price=Decimal('100'),
        ),
    )

    assert [o.outcome_type for o in result] == [
        TradeOutcomeType.ACK,
        TradeOutcomeType.FILLED,
    ]
    filled = result[1]
    assert filled.fill_size == Decimal('2')
    assert filled.fill_price == Decimal('100')
    assert filled.fill_notional == Decimal('200')
    assert filled.actual_fees == Decimal('0')


def test_partial_then_filled_emits_correct_deltas() -> None:

    translator = OutcomeTranslator()

    first = translator.translate(
        _praxis_outcome(
            status=TradeStatus.PARTIAL,
            target_qty=Decimal('10'),
            filled_qty=Decimal('4'),
            avg_fill_price=Decimal('100'),
        ),
    )
    second = translator.translate(
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('10'),
            filled_qty=Decimal('10'),
            avg_fill_price=Decimal('110'),
        ),
    )

    assert [o.outcome_type for o in first] == [
        TradeOutcomeType.ACK,
        TradeOutcomeType.PARTIAL,
    ]
    partial = first[1]
    assert partial.fill_size == Decimal('4')
    assert partial.fill_price == Decimal('100')
    assert partial.fill_notional == Decimal('400')
    assert partial.remaining_size == Decimal('6')

    assert [o.outcome_type for o in second] == [TradeOutcomeType.FILLED]
    filled = second[0]
    assert filled.fill_size == Decimal('6')
    assert filled.fill_notional == Decimal('700')
    assert filled.fill_price == Decimal('700') / Decimal('6')


def test_rejected_emits_single_rejected_with_reason() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.REJECTED,
            reason='insufficient balance',
        ),
    )

    assert len(result) == 1
    assert result[0].outcome_type == TradeOutcomeType.REJECTED
    assert result[0].reject_reason == 'insufficient balance'
    assert result[0].fill_size is None


def test_rejected_without_reason_uses_fallback() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(_praxis_outcome(status=TradeStatus.REJECTED))

    assert result[0].reject_reason == 'rejected'


def test_canceled_with_no_fills_emits_single_canceled() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.CANCELED,
            target_qty=Decimal('5'),
            reason='operator cancel',
        ),
    )

    assert len(result) == 1
    canceled = result[0]
    assert canceled.outcome_type == TradeOutcomeType.CANCELED
    assert canceled.cancel_reason == 'operator cancel'
    assert canceled.remaining_size == Decimal('5')


def test_canceled_after_partial_fill_emits_partial_then_canceled() -> None:

    translator = OutcomeTranslator()

    translator.translate(
        _praxis_outcome(
            status=TradeStatus.PARTIAL,
            target_qty=Decimal('10'),
            filled_qty=Decimal('3'),
            avg_fill_price=Decimal('100'),
        ),
    )
    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.CANCELED,
            target_qty=Decimal('10'),
            filled_qty=Decimal('5'),
            avg_fill_price=Decimal('101'),
        ),
    )

    assert [o.outcome_type for o in result] == [
        TradeOutcomeType.PARTIAL,
        TradeOutcomeType.CANCELED,
    ]
    partial = result[0]
    assert partial.fill_size == Decimal('2')
    assert partial.fill_notional == Decimal('505') - Decimal('300')
    canceled = result[1]
    assert canceled.remaining_size == Decimal('5')


def test_expired_with_partial_fill_emits_partial_then_expired() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.EXPIRED,
            target_qty=Decimal('4'),
            filled_qty=Decimal('1'),
            avg_fill_price=Decimal('50'),
        ),
    )

    assert [o.outcome_type for o in result] == [
        TradeOutcomeType.ACK,
        TradeOutcomeType.PARTIAL,
        TradeOutcomeType.EXPIRED,
    ]
    expired = result[2]
    assert expired.remaining_size == Decimal('3')
    assert expired.cancel_reason is None


def test_outcome_after_terminal_is_dropped() -> None:

    translator = OutcomeTranslator()

    translator.translate(
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('1'),
            filled_qty=Decimal('1'),
            avg_fill_price=Decimal('100'),
        ),
    )
    follow_up = translator.translate(
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('1'),
            filled_qty=Decimal('1'),
            avg_fill_price=Decimal('100'),
        ),
    )

    assert follow_up == []


def test_distinct_command_ids_are_isolated() -> None:

    translator = OutcomeTranslator()

    translator.translate(
        _praxis_outcome(command_id='cmd-A', status=TradeStatus.PENDING),
    )
    second = translator.translate(
        _praxis_outcome(command_id='cmd-B', status=TradeStatus.PENDING),
    )

    assert len(second) == 1
    assert second[0].outcome_type == TradeOutcomeType.ACK
    assert second[0].command_id == 'cmd-B'


def test_fee_rate_is_applied_to_fill_notional() -> None:

    translator = OutcomeTranslator(fee_rate=Decimal('0.001'))

    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('2'),
            filled_qty=Decimal('2'),
            avg_fill_price=Decimal('100'),
        ),
    )

    filled = result[1]
    assert filled.fill_notional == Decimal('200')
    assert filled.actual_fees == Decimal('200') * Decimal('0.001')


def test_outcome_id_is_unique_per_emission() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('2'),
            filled_qty=Decimal('2'),
            avg_fill_price=Decimal('100'),
        ),
    )

    assert result[0].outcome_id != result[1].outcome_id


def test_invalid_fee_rate_rejected() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        OutcomeTranslator(fee_rate=Decimal('-0.001'))
