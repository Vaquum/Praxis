'''Tests for `Launcher._apply_sync_accounting` and `_AccountOutcomeWiring`.'''

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from nexus.core.domain.enums import OrderSide
from nexus.infrastructure.praxis_connector.order_context import OrderContext
from nexus.infrastructure.praxis_connector.process_result import ProcessResult
from nexus.infrastructure.praxis_connector.trade_outcome import (
    TradeOutcome as NexusTradeOutcome,
)
from nexus.infrastructure.praxis_connector.trade_outcome_type import TradeOutcomeType

from praxis.launcher import Launcher, _AccountOutcomeWiring


class _RecordingProcessor:

    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[NexusTradeOutcome, OrderContext]] = []

    def process(
        self,
        outcome: NexusTradeOutcome,
        context: OrderContext,
    ) -> ProcessResult:
        self.calls.append((outcome, context))

        return self.result


class _RaisingProcessor:

    def __init__(self) -> None:
        self.calls = 0

    def process(
        self,
        _outcome: NexusTradeOutcome,
        _context: OrderContext,
    ) -> ProcessResult:
        self.calls += 1
        msg = 'processor boom'
        raise RuntimeError(msg)


def _outcome(command_id: str = 'cmd_001') -> NexusTradeOutcome:
    return NexusTradeOutcome(
        outcome_id='out_001',
        command_id=command_id,
        outcome_type=TradeOutcomeType.ACK,
        timestamp=datetime.now(tz=UTC),
    )


def _order_context(command_id: str = 'cmd_001') -> OrderContext:
    return OrderContext(
        command_id=command_id,
        strategy_id='strat_a',
        trade_id='trade_001',
        side=OrderSide.SELL,
        order_size=Decimal('0.01'),
        order_notional=Decimal('100'),
        estimated_fees=Decimal('1'),
        is_entry=False,
    )


def _wiring(
    processor: Any,
    contexts: dict[str, OrderContext],
) -> _AccountOutcomeWiring:
    return _AccountOutcomeWiring(
        outcome_processor=processor,
        command_contexts=contexts,
        command_registry_lock=threading.Lock(),
        account_id='acct-test',
        command_strategy_ids={},
    )


class TestApplySyncAccounting:

    def test_mutation_marks_command_unpersisted(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(
                success=True,
                outcome_type=TradeOutcomeType.ACK,
                position_updated=True,
            ),
        )
        ctx = _order_context()
        wiring = _wiring(processor, {'cmd_001': ctx})
        outcome = _outcome()

        Launcher._apply_sync_accounting(wiring, outcome)

        assert processor.calls == [(outcome, ctx)]
        assert wiring.unpersisted_commands == {'cmd_001': 1}

    def test_capital_mutation_marks_command_unpersisted(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(
                success=True,
                outcome_type=TradeOutcomeType.ACK,
                capital_updated=True,
            ),
        )
        ctx = _order_context()
        wiring = _wiring(processor, {'cmd_001': ctx})

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert wiring.unpersisted_commands == {'cmd_001': 1}

    def test_remark_bumps_generation(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(
                success=True,
                outcome_type=TradeOutcomeType.ACK,
                position_updated=True,
            ),
        )
        ctx = _order_context()
        wiring = _wiring(processor, {'cmd_001': ctx})

        Launcher._apply_sync_accounting(wiring, _outcome())
        Launcher._apply_sync_accounting(wiring, _outcome())

        assert wiring.unpersisted_commands == {'cmd_001': 2}
        assert wiring.pending_generation == 2

    def test_skips_when_order_context_missing(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        processor = _RecordingProcessor(
            ProcessResult(success=True, outcome_type=TradeOutcomeType.ACK),
        )
        wiring = _wiring(processor, {})

        with caplog.at_level(logging.WARNING, logger='praxis.launcher'):
            Launcher._apply_sync_accounting(wiring, _outcome())

        assert processor.calls == []
        assert wiring.unpersisted_commands == {}

        record = next(
            r for r in caplog.records
            if 'sync accounting skipped' in r.message
        )
        assert record.account_id == 'acct-test'
        assert record.command_id == 'cmd_001'
        assert record.outcome_id == 'out_001'
        assert record.outcome_type == 'ACK'
        assert record.has_strategy_mapping is False

    def test_failure_result_does_not_mark_unpersisted(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(
                success=False,
                outcome_type=TradeOutcomeType.ACK,
                error_reason='nope',
            ),
        )
        ctx = _order_context()
        wiring = _wiring(processor, {'cmd_001': ctx})

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert len(processor.calls) == 1
        assert wiring.unpersisted_commands == {}

    def test_success_without_mutation_does_not_mark_unpersisted(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(success=True, outcome_type=TradeOutcomeType.ACK),
        )
        ctx = _order_context()
        wiring = _wiring(processor, {'cmd_001': ctx})

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert len(processor.calls) == 1
        assert wiring.unpersisted_commands == {}

    def test_process_exception_is_contained(self) -> None:
        processor = _RaisingProcessor()
        ctx = _order_context()
        wiring = _wiring(processor, {'cmd_001': ctx})

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert processor.calls == 1
        assert wiring.unpersisted_commands == {}
