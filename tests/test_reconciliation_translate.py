'''Tests for Praxis to Nexus reconciliation-event translation (WP-9 7.3/8.7).'''

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from nexus.infrastructure.praxis_connector.fund_transaction import (
    FundTransaction as NexusFundTransaction,
)
from nexus.infrastructure.praxis_connector.reconciliation_mismatch import (
    ReconciliationMismatch as NexusReconciliationMismatch,
)

from praxis.core.domain.events import FundTransaction, ReconciliationMismatch
from praxis.reconciliation_translate import (
    translate_fund_transaction,
    translate_reconciliation_mismatch,
)

_TS = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def test_translate_fund_transaction_maps_every_field() -> None:
    praxis_fund = FundTransaction(
        account_id='acc-1',
        timestamp=_TS,
        fund_transaction_id='dep-1',
        amount=Decimal('250.5'),
        direction='DEPOSIT',
    )

    nexus_fund = translate_fund_transaction(praxis_fund)

    assert isinstance(nexus_fund, NexusFundTransaction)
    assert nexus_fund.account_id == 'acc-1'
    assert nexus_fund.timestamp == _TS
    assert nexus_fund.fund_transaction_id == 'dep-1'
    assert nexus_fund.amount == Decimal('250.5')
    assert nexus_fund.direction == 'DEPOSIT'


def test_translate_fund_transaction_normalises_timestamp_to_utc() -> None:
    non_utc = datetime(2026, 8, 3, 13, 0, tzinfo=timezone(timedelta(hours=1)))
    praxis_fund = FundTransaction(
        account_id='acc-1',
        timestamp=non_utc,
        fund_transaction_id='dep-1',
        amount=Decimal('100'),
        direction='WITHDRAWAL',
    )

    nexus_fund = translate_fund_transaction(praxis_fund)

    assert nexus_fund.timestamp.tzinfo is UTC
    assert nexus_fund.timestamp == non_utc


def test_translate_reconciliation_mismatch_maps_every_field() -> None:
    praxis_mismatch = ReconciliationMismatch(
        account_id='acc-1',
        timestamp=_TS,
        reconciliation_mismatch_id='recon-1',
        asset='USDT',
        expected=Decimal('1000'),
        actual=Decimal('995.5'),
    )

    nexus_mismatch = translate_reconciliation_mismatch(praxis_mismatch)

    assert isinstance(nexus_mismatch, NexusReconciliationMismatch)
    assert nexus_mismatch.account_id == 'acc-1'
    assert nexus_mismatch.timestamp == _TS
    assert nexus_mismatch.reconciliation_mismatch_id == 'recon-1'
    assert nexus_mismatch.asset == 'USDT'
    assert nexus_mismatch.expected == Decimal('1000')
    assert nexus_mismatch.actual == Decimal('995.5')


def test_translate_reconciliation_mismatch_normalises_timestamp_to_utc() -> None:
    non_utc = datetime(2026, 8, 3, 13, 0, tzinfo=timezone(timedelta(hours=1)))
    praxis_mismatch = ReconciliationMismatch(
        account_id='acc-1',
        timestamp=non_utc,
        reconciliation_mismatch_id='recon-1',
        asset='USDT',
        expected=Decimal('1000'),
        actual=Decimal('995.5'),
    )

    nexus_mismatch = translate_reconciliation_mismatch(praxis_mismatch)

    assert nexus_mismatch.timestamp.tzinfo is UTC
    assert nexus_mismatch.timestamp == non_utc
