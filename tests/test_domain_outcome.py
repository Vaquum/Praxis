'''
Tests for TradeOutcome dataclass and TradeStatus enum.
'''

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from praxis.core.domain import TradeOutcome, TradeStatus

_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)

_TERMINAL = [TradeStatus.CANCELED, TradeStatus.EXPIRED, TradeStatus.FILLED, TradeStatus.REJECTED]
_NON_TERMINAL = [TradeStatus.PARTIAL, TradeStatus.PAUSED, TradeStatus.PENDING]
_SLICES = 5


def _outcome(
    status: TradeStatus = TradeStatus.FILLED,
    target_qty: Decimal = Decimal('10.0'),
    filled_qty: Decimal = Decimal('10.0'),
    avg_fill_price: Decimal | None = Decimal('50000.00'),
    slices_completed: int = 5,
    slices_total: int = 5,
    missed_iterations: int | None = None,
) -> TradeOutcome:

    return TradeOutcome(
        command_id='cmd-001',
        trade_id='trade-001',
        account_id='acc-1',
        status=status,
        target_qty=target_qty,
        filled_qty=filled_qty,
        avg_fill_price=avg_fill_price,
        slices_completed=slices_completed,
        slices_total=slices_total,
        reason='done',
        created_at=_TS,
        missed_iterations=missed_iterations,
    )


def test_trade_status_members() -> None:

    expected = {
        TradeStatus.PENDING,
        TradeStatus.PARTIAL,
        TradeStatus.PAUSED,
        TradeStatus.FILLED,
        TradeStatus.CANCELED,
        TradeStatus.REJECTED,
        TradeStatus.EXPIRED,
    }
    assert set(TradeStatus) == expected


def test_trade_status_values_are_strings() -> None:

    for member in TradeStatus:
        assert isinstance(member.value, str)


def test_trade_outcome_creation() -> None:

    outcome = _outcome()
    assert outcome.command_id == 'cmd-001'
    assert outcome.trade_id == 'trade-001'
    assert outcome.account_id == 'acc-1'
    assert outcome.status == TradeStatus.FILLED
    assert outcome.target_qty == Decimal('10.0')
    assert outcome.filled_qty == Decimal('10.0')
    assert outcome.avg_fill_price == Decimal('50000.00')
    assert outcome.slices_completed == _SLICES
    assert outcome.slices_total == _SLICES
    assert outcome.reason == 'done'
    assert outcome.missed_iterations is None
    assert outcome.missed_reason is None


def test_trade_outcome_frozen() -> None:

    outcome = _outcome()
    with pytest.raises(AttributeError):
        outcome.status = TradeStatus.CANCELED  # type: ignore[misc]


def test_trade_outcome_zero_filled_qty_valid() -> None:

    outcome = _outcome(
        status=TradeStatus.PENDING,
        filled_qty=Decimal('0'),
        avg_fill_price=None,
        slices_completed=0,
    )
    assert outcome.filled_qty == Decimal('0')
    assert outcome.avg_fill_price is None


def test_trade_outcome_financial_values_are_decimal() -> None:

    outcome = _outcome()
    assert isinstance(outcome.target_qty, Decimal)
    assert isinstance(outcome.filled_qty, Decimal)
    assert isinstance(outcome.avg_fill_price, Decimal)


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_trade_outcome_rejects_non_positive_target_qty(bad: Decimal) -> None:

    with pytest.raises(ValueError, match='positive'):
        _outcome(target_qty=bad)


def test_trade_outcome_rejects_negative_filled_qty() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        _outcome(filled_qty=Decimal('-1'))


def test_trade_outcome_rejects_filled_qty_exceeds_target_qty() -> None:

    with pytest.raises(ValueError, match='cannot exceed target_qty'):
        _outcome(target_qty=Decimal('10'), filled_qty=Decimal('11'))


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_trade_outcome_rejects_non_positive_avg_fill_price(bad: Decimal) -> None:

    with pytest.raises(ValueError, match='positive'):
        _outcome(avg_fill_price=bad)


def test_trade_outcome_rejects_avg_fill_price_when_no_fills() -> None:

    with pytest.raises(ValueError, match='None when filled_qty is zero'):
        _outcome(filled_qty=Decimal('0'), avg_fill_price=Decimal('100'))


def test_trade_outcome_rejects_negative_slices_completed() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        _outcome(slices_completed=-1)


@pytest.mark.parametrize('bad', [0, -1])
def test_trade_outcome_rejects_non_positive_slices_total(bad: int) -> None:

    with pytest.raises(ValueError, match='positive'):
        _outcome(slices_total=bad)


def test_trade_outcome_rejects_slices_completed_exceeds_slices_total() -> None:

    with pytest.raises(ValueError, match='cannot exceed slices_total'):
        _outcome(slices_completed=6, slices_total=5)


def test_trade_outcome_rejects_negative_missed_iterations() -> None:

    with pytest.raises(ValueError, match='non-negative'):
        _outcome(missed_iterations=-1)


def test_trade_outcome_rejects_naive_created_at() -> None:

    with pytest.raises(ValueError, match='timezone-aware'):
        TradeOutcome(
            command_id='cmd-001',
            trade_id='trade-001',
            account_id='acc-1',
            status=TradeStatus.FILLED,
            target_qty=Decimal('10.0'),
            filled_qty=Decimal('10.0'),
            avg_fill_price=Decimal('50000.00'),
            slices_completed=5,
            slices_total=5,
            reason='done',
            created_at=datetime(2026, 1, 1),
        )


@pytest.mark.parametrize('status', _TERMINAL)
def test_trade_outcome_is_terminal(status: TradeStatus) -> None:

    price = Decimal('50000') if status == TradeStatus.FILLED else None
    filled = Decimal('10') if status == TradeStatus.FILLED else Decimal('0')
    outcome = _outcome(status=status, filled_qty=filled, avg_fill_price=price)
    assert outcome.is_terminal is True


@pytest.mark.parametrize('status', _NON_TERMINAL)
def test_trade_outcome_is_not_terminal(status: TradeStatus) -> None:

    outcome = _outcome(
        status=status,
        filled_qty=Decimal('0'),
        avg_fill_price=None,
        slices_completed=0,
    )
    assert outcome.is_terminal is False


def test_trade_outcome_fill_ratio() -> None:

    outcome = _outcome(target_qty=Decimal('10'), filled_qty=Decimal('7'))
    assert outcome.fill_ratio == Decimal('0.7')


def test_trade_outcome_fill_ratio_zero() -> None:

    outcome = _outcome(
        status=TradeStatus.PENDING,
        filled_qty=Decimal('0'),
        avg_fill_price=None,
        slices_completed=0,
    )
    assert outcome.fill_ratio == Decimal('0')


def test_trade_outcome_missed_iterations_zero_valid() -> None:

    outcome = _outcome(missed_iterations=0)
    assert outcome.missed_iterations == 0


@pytest.mark.parametrize('field', ['command_id', 'trade_id', 'account_id'])
def test_trade_outcome_rejects_empty_string(field: str) -> None:

    kwargs = {
        'command_id': 'cmd-001',
        'trade_id': 'trade-001',
        'account_id': 'acc-1',
        'status': TradeStatus.FILLED,
        'target_qty': Decimal('10.0'),
        'filled_qty': Decimal('10.0'),
        'avg_fill_price': Decimal('50000.00'),
        'slices_completed': 5,
        'slices_total': 5,
        'reason': 'done',
        'created_at': _TS,
    }
    kwargs[field] = ''
    with pytest.raises(ValueError, match='non-empty string'):
        TradeOutcome(**kwargs)
