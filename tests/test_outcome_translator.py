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
    cumulative_notional: Decimal | None = None,
    reason: str | None = None,
) -> PraxisTradeOutcome:

    if cumulative_notional is None:
        if avg_fill_price is not None:
            cumulative_notional = filled_qty * avg_fill_price
        else:
            cumulative_notional = Decimal('0')

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
        cumulative_notional=cumulative_notional,
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


def test_terminal_dedup_set_is_bounded() -> None:
    '''PT-FIX-39: `_terminal_command_ids` is bounded by
    `terminal_dedup_cap`; on insertion past the cap the oldest entry
    is evicted FIFO. Pre-fix the set grew without bound across a
    sustained session — `len(...) == N` after N round-trips.

    Drives 50 ENTER+FILLED round trips through a translator with
    `terminal_dedup_cap=10`; asserts the dedup table size stays at
    or below the cap and the LRU eviction order is correct.'''

    translator = OutcomeTranslator(terminal_dedup_cap=10)

    for i in range(50):
        cid = f'cmd-{i:03d}'
        translator.translate(_praxis_outcome(command_id=cid, status=TradeStatus.PENDING))
        translator.translate(
            _praxis_outcome(
                command_id=cid,
                status=TradeStatus.FILLED,
                target_qty=Decimal('1'),
                filled_qty=Decimal('1'),
                avg_fill_price=Decimal('100'),
            ),
        )

    assert len(translator._terminal_command_ids) == 10
    expected = [f'cmd-{i:03d}' for i in range(40, 50)]
    assert list(translator._terminal_command_ids.keys()) == expected


def test_evicted_command_id_no_longer_dedups() -> None:
    '''After eviction, a duplicate terminal outcome for the evicted
    command_id is no longer dropped — it produces a stray Nexus
    terminal outcome. Downstream `OutcomeProcessor` handles this
    with `INVARIANT_BREACH: order not found`; the bound is a
    memory-vs-correctness tradeoff documented on the constructor.'''

    translator = OutcomeTranslator(terminal_dedup_cap=2)

    for cid in ('cmd-A', 'cmd-B', 'cmd-C'):
        translator.translate(
            _praxis_outcome(
                command_id=cid,
                status=TradeStatus.FILLED,
                target_qty=Decimal('1'),
                filled_qty=Decimal('1'),
                avg_fill_price=Decimal('100'),
            ),
        )

    assert 'cmd-A' not in translator._terminal_command_ids
    assert 'cmd-B' in translator._terminal_command_ids
    assert 'cmd-C' in translator._terminal_command_ids

    follow_up = translator.translate(
        _praxis_outcome(
            command_id='cmd-A',
            status=TradeStatus.FILLED,
            target_qty=Decimal('1'),
            filled_qty=Decimal('1'),
            avg_fill_price=Decimal('100'),
        ),
    )
    assert follow_up != []


def test_invalid_terminal_dedup_cap_rejected() -> None:
    with pytest.raises(ValueError, match='terminal_dedup_cap'):
        OutcomeTranslator(terminal_dedup_cap=0)

    with pytest.raises(ValueError, match='terminal_dedup_cap'):
        OutcomeTranslator(terminal_dedup_cap=-5)


class TestFinalMajor07TranslatorUsesVenueCumulativeNotional:
    '''FINAL-MAJOR-07: pre-fix the translator computed
    `cumulative_notional = outcome.filled_qty * outcome.avg_fill_price`,
    a precision-lossy round trip after the venue had already done
    `total_notional / filled_qty` for `avg_fill_price`. On multi-partial
    sequences the two round trips can flip `delta_notional` negative,
    producing `delta_price < 0`, which `TradeOutcome.__post_init__`
    rejects with ValueError; the partial fill is silently dropped at
    `execution_manager._emit_outcome`, capital stays parked, position
    never grows.

    Post-fix the translator uses `outcome.cumulative_notional` carried
    verbatim from `Order.cumulative_notional` (the venue-side
    `sum(qty * price)`), so per-fill deltas equal the exact venue
    deltas with no reverse-derivation drift.
    '''

    def test_multi_partial_with_drift_inducing_avg_price_no_negative_delta(
        self,
    ) -> None:
        '''Construct a multi-partial sequence where the reverse-derived
        cumulative would drift due to ROUND_HALF_EVEN at default
        Decimal precision. Verify the translator emits successive
        partials with non-negative delta_notional matching the venue
        cumulative deltas exactly.
        '''

        translator = OutcomeTranslator()

        partials = [
            (Decimal('1'), Decimal('100')),
            (Decimal('1'), Decimal('100.000000000000000000000000007')),
            (Decimal('1'), Decimal('99.999999999999999999999999993')),
        ]

        cumulative_qty = Decimal('0')
        cumulative_notional = Decimal('0')
        emitted_partials = []

        for qty, notional in partials:
            cumulative_qty += qty
            cumulative_notional += notional
            avg_fill_price = cumulative_notional / cumulative_qty

            results = translator.translate(
                _praxis_outcome(
                    status=TradeStatus.PARTIAL,
                    target_qty=Decimal('10'),
                    filled_qty=cumulative_qty,
                    avg_fill_price=avg_fill_price,
                    cumulative_notional=cumulative_notional,
                )
            )

            for r in results:
                if r.fill_notional is None:
                    continue
                assert r.fill_notional >= Decimal('0'), (
                    f'pre-fix would drift negative on round-trip; '
                    f'got fill_notional={r.fill_notional}'
                )
                emitted_partials.append(r.fill_notional)

        assert sum(emitted_partials, Decimal('0')) == cumulative_notional, (
            f'translator-emitted fill_notional sum '
            f'{sum(emitted_partials, Decimal('0'))} drifted from venue '
            f'cumulative_notional {cumulative_notional}'
        )

    def test_translator_per_fill_deltas_byte_equal_venue_cumulative(
        self,
    ) -> None:
        '''For any sequence of partial fills, the sum of translator-
        emitted fill_notional values must equal the venue's final
        cumulative_notional exactly (no per-fill drift introduced).
        '''

        translator = OutcomeTranslator()

        venue_fills = [
            (Decimal('0.5'), Decimal('60123.456789012345')),
            (Decimal('0.3'), Decimal('60125.789012345678')),
            (Decimal('0.2'), Decimal('60127.345678901234')),
            (Decimal('1.0'), Decimal('60130.111111111111')),
        ]

        cumulative_qty = Decimal('0')
        cumulative_notional = Decimal('0')
        sum_emitted = Decimal('0')

        for qty, price in venue_fills:
            cumulative_qty += qty
            cumulative_notional += qty * price

            results = translator.translate(
                _praxis_outcome(
                    status=TradeStatus.PARTIAL,
                    target_qty=Decimal('10'),
                    filled_qty=cumulative_qty,
                    avg_fill_price=cumulative_notional / cumulative_qty,
                    cumulative_notional=cumulative_notional,
                )
            )

            for r in results:
                if r.fill_notional is not None:
                    sum_emitted += r.fill_notional

        assert sum_emitted == cumulative_notional, (
            f'translator drift: emitted={sum_emitted} '
            f'venue_cumulative={cumulative_notional} '
            f'delta={sum_emitted - cumulative_notional}'
        )


def test_leg_outcome_ids_are_deterministic() -> None:

    translator = OutcomeTranslator()

    result = translator.translate(
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('2'),
            filled_qty=Decimal('2'),
            avg_fill_price=Decimal('100'),
        ),
    )

    assert [o.outcome_id for o in result] == [
        'acct-1:cmd-1:ack',
        'acct-1:cmd-1:filled',
    ]


def test_successive_partials_get_indexed_ids() -> None:

    translator = OutcomeTranslator()

    first = translator.translate(
        _praxis_outcome(
            status=TradeStatus.PARTIAL,
            target_qty=Decimal('3'),
            filled_qty=Decimal('1'),
            avg_fill_price=Decimal('100'),
        ),
    )
    second = translator.translate(
        _praxis_outcome(
            status=TradeStatus.PARTIAL,
            target_qty=Decimal('3'),
            filled_qty=Decimal('2'),
            avg_fill_price=Decimal('100'),
        ),
    )

    partial_ids = [
        o.outcome_id
        for o in (*first, *second)
        if o.outcome_type == TradeOutcomeType.PARTIAL
    ]
    assert partial_ids == ['acct-1:cmd-1:partial:0', 'acct-1:cmd-1:partial:1']


def test_replay_reproduces_identical_outcome_ids() -> None:

    sequence = [
        _praxis_outcome(
            status=TradeStatus.PARTIAL,
            target_qty=Decimal('3'),
            filled_qty=Decimal('1'),
            avg_fill_price=Decimal('100'),
        ),
        _praxis_outcome(
            status=TradeStatus.FILLED,
            target_qty=Decimal('3'),
            filled_qty=Decimal('3'),
            avg_fill_price=Decimal('100'),
        ),
    ]

    live = OutcomeTranslator()
    live_ids = [o.outcome_id for s in sequence for o in live.translate(s)]

    replay = OutcomeTranslator()
    replay_ids = [o.outcome_id for s in sequence for o in replay.translate(s)]

    assert replay_ids == live_ids
