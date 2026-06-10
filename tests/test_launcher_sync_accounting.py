'''Tests for `Launcher._apply_sync_accounting` and `_AccountOutcomeWiring`.'''

from __future__ import annotations

import threading
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.instance_state import InstanceState
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


class _RecordingStateStore:

    def __init__(self) -> None:
        self.mutations: list[InstanceState] = []

    def append_mutation(self, state: InstanceState) -> None:
        self.mutations.append(state)


class _RaisingStateStore:

    def __init__(self) -> None:
        self.calls = 0

    def append_mutation(self, _state: InstanceState) -> None:
        self.calls += 1
        msg = 'store boom'
        raise OSError(msg)


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


def _state() -> InstanceState:
    return InstanceState(capital=CapitalState(capital_pool=Decimal('10000')))


def _wiring(
    processor: Any,
    state_store: Any,
    contexts: dict[str, OrderContext],
    state: InstanceState,
) -> _AccountOutcomeWiring:
    return _AccountOutcomeWiring(
        outcome_processor=processor,
        command_contexts=contexts,
        command_registry_lock=threading.Lock(),
        state_store=state_store,
        state=state,
    )


class TestApplySyncAccounting:

    def test_processes_outcome_and_persists_mutation(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(
                success=True,
                outcome_type=TradeOutcomeType.ACK,
                position_updated=True,
            ),
        )
        store = _RecordingStateStore()
        state = _state()
        ctx = _order_context()
        wiring = _wiring(processor, store, {'cmd_001': ctx}, state)
        outcome = _outcome()

        Launcher._apply_sync_accounting(wiring, outcome)

        assert processor.calls == [(outcome, ctx)]
        assert store.mutations == [state]

    def test_skips_when_order_context_missing(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(success=True, outcome_type=TradeOutcomeType.ACK),
        )
        store = _RecordingStateStore()
        wiring = _wiring(processor, store, {}, _state())

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert processor.calls == []
        assert store.mutations == []

    def test_failure_result_does_not_persist(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(
                success=False,
                outcome_type=TradeOutcomeType.ACK,
                error_reason='nope',
            ),
        )
        store = _RecordingStateStore()
        ctx = _order_context()
        wiring = _wiring(processor, store, {'cmd_001': ctx}, _state())

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert len(processor.calls) == 1
        assert store.mutations == []

    def test_success_without_mutation_does_not_persist(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(success=True, outcome_type=TradeOutcomeType.ACK),
        )
        store = _RecordingStateStore()
        ctx = _order_context()
        wiring = _wiring(processor, store, {'cmd_001': ctx}, _state())

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert len(processor.calls) == 1
        assert store.mutations == []

    def test_process_exception_is_contained(self) -> None:
        processor = _RaisingProcessor()
        store = _RecordingStateStore()
        ctx = _order_context()
        wiring = _wiring(processor, store, {'cmd_001': ctx}, _state())

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert processor.calls == 1
        assert store.mutations == []

    def test_append_mutation_exception_is_contained(self) -> None:
        processor = _RecordingProcessor(
            ProcessResult(
                success=True,
                outcome_type=TradeOutcomeType.ACK,
                capital_updated=True,
            ),
        )
        store = _RaisingStateStore()
        ctx = _order_context()
        wiring = _wiring(processor, store, {'cmd_001': ctx}, _state())

        Launcher._apply_sync_accounting(wiring, _outcome())

        assert len(processor.calls) == 1
        assert store.calls == 1
