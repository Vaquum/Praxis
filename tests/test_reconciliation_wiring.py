'''Tests for the Praxis to Nexus reconciliation dispatch composition (WP-9 7.3/8.7).

Exercises the translate-then-dispatch pair the launcher wires onto the
`Trading` singleton, driving real Nexus handlers rather than a full
launcher runtime: a Praxis mismatch through
`translate_reconciliation_mismatch` + `ReconciliationHandler` drives the
account `ModeController` to HALTED under a default-HALT response, and a
Praxis fund transaction through `translate_fund_transaction` +
`OutcomeProcessor.process_fund_transaction` records once and dedups.
'''

from __future__ import annotations

import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OperationalMode
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.reconciliation_mismatch_response import (
    ReconciliationMismatchResponse,
)
from nexus.core.mode_controller import ModeController
from nexus.infrastructure.praxis_connector.outcome_processor import OutcomeProcessor
from nexus.infrastructure.state_store import StateStore
from nexus.reconciler.reconciliation_handler import ReconciliationHandler

from praxis.core.domain.events import FundTransaction, ReconciliationMismatch
from praxis.reconciliation_translate import (
    translate_fund_transaction,
    translate_reconciliation_mismatch,
)

_TS = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def _instance_state() -> InstanceState:
    return InstanceState(capital=CapitalState(capital_pool=Decimal('1000')))


def _praxis_mismatch() -> ReconciliationMismatch:
    return ReconciliationMismatch(
        account_id='acc-1',
        timestamp=_TS,
        reconciliation_mismatch_id='recon-1',
        asset='USDT',
        expected=Decimal('1000'),
        actual=Decimal('900'),
    )


def test_wired_mismatch_drives_mode_controller_to_halted() -> None:
    state = _instance_state()
    mode_controller = ModeController(state, threading.Lock())
    handler = ReconciliationHandler(
        mode_controller, ReconciliationMismatchResponse.HALT,
    )

    assert state.mode.mode is OperationalMode.ACTIVE

    handler.process_reconciliation_mismatch(
        translate_reconciliation_mismatch(_praxis_mismatch()),
    )

    assert state.mode.mode is OperationalMode.HALTED


def test_wired_mismatch_alert_only_leaves_mode_active() -> None:
    state = _instance_state()
    mode_controller = ModeController(state, threading.Lock())
    handler = ReconciliationHandler(
        mode_controller, ReconciliationMismatchResponse.ALERT_ONLY,
    )

    handler.process_reconciliation_mismatch(
        translate_reconciliation_mismatch(_praxis_mismatch()),
    )

    assert state.mode.mode is OperationalMode.ACTIVE


def test_wired_fund_transaction_records_once_and_dedups(tmp_path: Path) -> None:
    state = _instance_state()
    processor = OutcomeProcessor(
        capital_controller=CapitalController(state.capital),
        instance_state=state,
        state_store=StateStore(tmp_path),
        positions_lock=threading.Lock(),
    )
    praxis_fund = FundTransaction(
        account_id='acc-1',
        timestamp=_TS,
        fund_transaction_id='dep-1',
        amount=Decimal('250'),
        direction='DEPOSIT',
    )

    assert processor.process_fund_transaction(
        translate_fund_transaction(praxis_fund),
    )
    assert not processor.process_fund_transaction(
        translate_fund_transaction(praxis_fund),
    )
