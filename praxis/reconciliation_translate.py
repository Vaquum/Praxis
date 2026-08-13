'''Translate Praxis reconciliation events into Nexus inbound types.

The Praxis reconciliation engine emits its own domain events —
`praxis.core.domain.events.FundTransaction` and
`ReconciliationMismatch` — onto the Event Spine. The Nexus Praxis
Connector consumes distinct inbound dataclasses of the same name
(`nexus.infrastructure.praxis_connector.fund_transaction.FundTransaction`
and `...reconciliation_mismatch.ReconciliationMismatch`). The two
sides are separate Python classes even though their fields line up
one-to-one, so a Praxis event cannot be handed to a Nexus handler
directly; these helpers re-key each field to the Nexus type.

Both Nexus types require `timestamp.tzinfo is timezone.utc` (an
identity check), a stricter contract than the Praxis events, which
only require a timezone-aware value. Praxis reconciliation timestamps
are already UTC, but a venue-sourced fund timestamp may carry an
equivalent-but-not-identical tzinfo; `astimezone(UTC)`
normalises the instant to the exact `timezone.utc` object the Nexus
validator demands without changing the moment represented.
'''

from __future__ import annotations

from datetime import UTC

from nexus.infrastructure.praxis_connector.fund_transaction import (
    FundTransaction as NexusFundTransaction,
)
from nexus.infrastructure.praxis_connector.reconciliation_mismatch import (
    ReconciliationMismatch as NexusReconciliationMismatch,
)

from praxis.core.domain.events import FundTransaction, ReconciliationMismatch

__all__ = [
    'translate_fund_transaction',
    'translate_reconciliation_mismatch',
]


def translate_fund_transaction(
    praxis_fund: FundTransaction,
) -> NexusFundTransaction:
    '''Re-key a Praxis `FundTransaction` to the Nexus inbound type.

    Args:
        praxis_fund: The Praxis reconciliation-engine fund transaction.

    Returns:
        The equivalent Nexus `FundTransaction`, with `timestamp`
        normalised to `timezone.utc`.
    '''

    return NexusFundTransaction(
        account_id=praxis_fund.account_id,
        timestamp=praxis_fund.timestamp.astimezone(UTC),
        fund_transaction_id=praxis_fund.fund_transaction_id,
        amount=praxis_fund.amount,
        direction=praxis_fund.direction,
    )


def translate_reconciliation_mismatch(
    praxis_mismatch: ReconciliationMismatch,
) -> NexusReconciliationMismatch:
    '''Re-key a Praxis `ReconciliationMismatch` to the Nexus inbound type.

    Args:
        praxis_mismatch: The Praxis reconciliation-engine balance mismatch.

    Returns:
        The equivalent Nexus `ReconciliationMismatch`, with `timestamp`
        normalised to `timezone.utc`.
    '''

    return NexusReconciliationMismatch(
        account_id=praxis_mismatch.account_id,
        timestamp=praxis_mismatch.timestamp.astimezone(UTC),
        reconciliation_mismatch_id=praxis_mismatch.reconciliation_mismatch_id,
        asset=praxis_mismatch.asset,
        expected=praxis_mismatch.expected,
        actual=praxis_mismatch.actual,
    )
