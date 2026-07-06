from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.domain.chart_of_accounts import Account
from praxis.core.domain.journal_entry import JournalEntry, JournalLine

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def _entry(lines: list[JournalLine]) -> JournalEntry:
    return JournalEntry(
        timestamp=_TS, source_event_type='FillReceived', source_event_id='vt-1',
        memo='m', lines=tuple(lines),
    )


def test_balanced_entry_is_accepted():
    entry = _entry([
        JournalLine(Account.CRYPTO_BTC, Decimal('100'), Decimal('0')),
        JournalLine(Account.CASH_USDT, Decimal('0'), Decimal('100')),
    ])

    assert len(entry.lines) == 2


def test_unbalanced_entry_is_rejected():
    with pytest.raises(ValueError, match='not balanced'):
        _entry([
            JournalLine(Account.CRYPTO_BTC, Decimal('100'), Decimal('0')),
            JournalLine(Account.CASH_USDT, Decimal('0'), Decimal('99')),
        ])


def test_two_sided_line_is_rejected():
    with pytest.raises(ValueError, match='one-sided'):
        JournalLine(Account.CASH_USDT, Decimal('5'), Decimal('5'))


def test_negative_line_is_rejected():
    with pytest.raises(ValueError, match='non-negative'):
        JournalLine(Account.CASH_USDT, Decimal('-1'), Decimal('0'))


def test_empty_entry_is_rejected():
    with pytest.raises(ValueError, match='at least one line'):
        _entry([])
