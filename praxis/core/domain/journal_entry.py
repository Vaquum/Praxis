'''Balanced double-entry journal records for the Account sub-system.

A `JournalEntry` is an immutable, balanced set of `JournalLine`s derived
from one Event Spine event. Balanced means total debits equal total
credits; the constructor rejects any entry that is not.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain.chart_of_accounts import Account

__all__ = ['JournalEntry', 'JournalLine']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class JournalLine:

    '''One leg of a journal entry: a debit or a credit to one account.

    Args:
        account: The account this line posts to.
        debit: Amount posted to the debit side, in the quote asset.
        credit: Amount posted to the credit side, in the quote asset.
    '''

    account: Account
    debit: Decimal
    credit: Decimal

    def __post_init__(self) -> None:

        if not self.debit.is_finite() or not self.credit.is_finite():
            msg = f'JournalLine amounts must be finite: {self.debit}, {self.credit}'
            raise ValueError(msg)

        if self.debit < _ZERO or self.credit < _ZERO:
            msg = f'JournalLine amounts must be non-negative: {self.debit}, {self.credit}'
            raise ValueError(msg)

        if self.debit > _ZERO and self.credit > _ZERO:
            msg = f'JournalLine must be one-sided, got debit={self.debit} credit={self.credit}'
            raise ValueError(msg)


@dataclass(frozen=True)
class JournalEntry:

    '''A balanced set of journal lines posted from one event.

    Args:
        timestamp: Event time, timezone-aware.
        source_event_type: Type name of the spine event this entry derives
            from, e.g. `'FillReceived'` or `'FundTransaction'`.
        source_event_id: Stable identifier of that source event.
        memo: Short human-readable description of the entry.
        lines: The debit and credit lines; total debits equal total credits.
    '''

    timestamp: datetime
    source_event_type: str
    source_event_id: str
    memo: str
    lines: tuple[JournalLine, ...]

    def __post_init__(self) -> None:

        if not self.lines:
            msg = 'JournalEntry must have at least one line'
            raise ValueError(msg)

        total_debits = sum((line.debit for line in self.lines), _ZERO)
        total_credits = sum((line.credit for line in self.lines), _ZERO)

        if total_debits != total_credits:
            msg = f'JournalEntry not balanced: debits={total_debits} credits={total_credits}'
            raise ValueError(msg)
