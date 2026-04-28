'''Integration test for PT-FIX-8: OutcomeProcessor is wired into the runtime.

Pre-fix: OutcomeProcessor was built and unit-tested in Nexus, but no
caller anywhere in the runtime constructed one or invoked
CapitalController.order_ack / order_fill / order_reject / order_cancel.
OutcomeLoop._dispatch only fired the strategy callback; capital state
desynced from venue lifecycle. After ~30s reservations TTL-expired,
but position_notional and per_strategy_deployed accumulated phantom
values forever.

Post-fix: the launcher instantiates OutcomeProcessor per account,
maintains a per-account command_id->OrderContext registry populated
at submission time, and wires `process_outcome` into OutcomeLoop so
capital state moves with each outcome before the strategy callback
runs.

These tests exercise the wiring end-to-end against real
CapitalController, OutcomeProcessor, and OutcomeLoop instances
(with a fake StrategyRunner / PraxisInbound) so the full lifecycle
is observable.
'''

from __future__ import annotations

import queue
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.outcome_loop import OutcomeLoop
from nexus.infrastructure.praxis_connector.order_context import OrderContext
from nexus.infrastructure.praxis_connector.outcome_processor import OutcomeProcessor
from nexus.infrastructure.praxis_connector.praxis_inbound import PraxisInbound
from nexus.infrastructure.praxis_connector.trade_outcome import TradeOutcome
from nexus.infrastructure.praxis_connector.trade_outcome_type import (
    TradeOutcomeType,
)
from nexus.infrastructure.state_store import StateStore

_TS = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)


def _build_fixture(tmp_path: Path) -> tuple[
    CapitalController,
    OutcomeProcessor,
    OutcomeLoop,
    queue.Queue[TradeOutcome],
    InstanceState,
    str,
    str,
]:
    state = InstanceState.fresh(capital_pool=Decimal('10000'))
    capital_controller = CapitalController(state.capital)

    state_store = StateStore(tmp_path)

    processor = OutcomeProcessor(
        capital_controller=capital_controller,
        instance_state=state,
        state_store=state_store,
    )

    strategy_id = 'strat-1'
    command_id = 'cmd-1'

    reservation_result = capital_controller.check_and_reserve(
        strategy_id=strategy_id,
        order_notional=Decimal('100'),
        estimated_fees=Decimal('1'),
        strategy_budget=Decimal('1000'),
    )
    assert reservation_result.granted

    send_result = capital_controller.send_order(
        reservation_result.reservation.reservation_id,
        command_id,
    )
    assert send_result.success

    order_context = OrderContext(
        command_id=command_id,
        strategy_id=strategy_id,
        trade_id='trade-1',
        side=OrderSide.BUY,
        order_size=Decimal('1'),
        order_notional=Decimal('100'),
        estimated_fees=Decimal('1'),
        is_entry=True,
    )

    state.positions['trade-1'] = MagicMock(
        size=Decimal('0'),
        entry_price=Decimal('100'),
        side=OrderSide.BUY,
        pending_exit=Decimal('0'),
        is_closed=False,
    )

    contexts = {command_id: order_context}

    def process_outcome(outcome: TradeOutcome) -> None:
        ctx = contexts.get(outcome.command_id)
        if ctx is None:
            return
        processor.process(outcome, ctx)

    outcome_queue: queue.Queue[TradeOutcome] = queue.Queue()
    inbound = PraxisInbound(outcome_queue=outcome_queue)

    runner = MagicMock()
    runner.dispatch_outcome.return_value = []

    loop = OutcomeLoop(
        runner=runner,
        praxis_inbound=inbound,
        state=state,
        context_provider=lambda _sid: MagicMock(),
        resolve_strategy_id=lambda _o: strategy_id,
        process_outcome=process_outcome,
    )

    return capital_controller, processor, loop, outcome_queue, state, command_id, strategy_id


def test_ack_outcome_keeps_capital_in_working_state(tmp_path: Path) -> None:
    '''ACK transitions IN_FLIGHT -> WORKING; capital math is preserved.'''

    _capital_controller, _, loop, outcome_queue, state, command_id, _ = _build_fixture(
        tmp_path,
    )

    pre_in_flight = state.capital.in_flight_order_notional
    assert pre_in_flight > Decimal('0')

    outcome_queue.put_nowait(
        TradeOutcome(
            outcome_id='out-1',
            command_id=command_id,
            outcome_type=TradeOutcomeType.ACK,
            timestamp=_TS,
        ),
    )

    consumed = loop.tick_once()

    assert consumed
    assert state.capital.in_flight_order_notional == Decimal('0')
    assert state.capital.working_order_notional == pre_in_flight


def test_fill_outcome_moves_capital_into_position(tmp_path: Path) -> None:
    '''FILLED moves working_order_notional -> position_notional.'''

    _, _, loop, outcome_queue, state, command_id, _ = _build_fixture(tmp_path)

    outcome_queue.put_nowait(
        TradeOutcome(
            outcome_id='out-ack',
            command_id=command_id,
            outcome_type=TradeOutcomeType.ACK,
            timestamp=_TS,
        ),
    )
    loop.tick_once()

    pre_position = state.capital.position_notional

    outcome_queue.put_nowait(
        TradeOutcome(
            outcome_id='out-fill',
            command_id=command_id,
            outcome_type=TradeOutcomeType.FILLED,
            timestamp=_TS,
            fill_size=Decimal('1'),
            fill_price=Decimal('100'),
            fill_notional=Decimal('100'),
            actual_fees=Decimal('1'),
        ),
    )
    loop.tick_once()

    assert state.capital.position_notional > pre_position
    assert state.capital.working_order_notional == Decimal('0')


def test_reject_outcome_releases_reservation_via_order_reject(
    tmp_path: Path,
) -> None:
    '''REJECTED triggers order_reject; capital exits the in-flight bucket.'''

    _, _, loop, outcome_queue, state, command_id, _ = _build_fixture(tmp_path)

    pre_in_flight = state.capital.in_flight_order_notional
    assert pre_in_flight > Decimal('0')

    outcome_queue.put_nowait(
        TradeOutcome(
            outcome_id='out-reject',
            command_id=command_id,
            outcome_type=TradeOutcomeType.REJECTED,
            timestamp=_TS,
            reject_reason='insufficient balance',
        ),
    )
    loop.tick_once()

    assert state.capital.in_flight_order_notional == Decimal('0')
    assert state.capital.working_order_notional == Decimal('0')


def test_cancel_outcome_releases_capital(tmp_path: Path) -> None:
    '''CANCELED on a working order releases working_order_notional.'''

    _, _, loop, outcome_queue, state, command_id, _ = _build_fixture(tmp_path)

    outcome_queue.put_nowait(
        TradeOutcome(
            outcome_id='out-ack',
            command_id=command_id,
            outcome_type=TradeOutcomeType.ACK,
            timestamp=_TS,
        ),
    )
    loop.tick_once()

    pre_working = state.capital.working_order_notional
    assert pre_working > Decimal('0')

    outcome_queue.put_nowait(
        TradeOutcome(
            outcome_id='out-cancel',
            command_id=command_id,
            outcome_type=TradeOutcomeType.CANCELED,
            timestamp=_TS,
            remaining_size=Decimal('1'),
        ),
    )
    loop.tick_once()

    assert state.capital.working_order_notional == Decimal('0')


def test_outcome_loop_calls_processor_before_strategy_runner(
    tmp_path: Path,
) -> None:
    '''process_outcome runs before runner.dispatch_outcome.'''

    _capital_controller, _, loop, outcome_queue, state, command_id, _ = _build_fixture(
        tmp_path,
    )

    runner = loop._runner
    seen_in_flight: list[Decimal] = []

    def capture(*_args: object, **_kwargs: object) -> list[object]:
        seen_in_flight.append(state.capital.in_flight_order_notional)
        return []

    runner.dispatch_outcome.side_effect = capture

    outcome_queue.put_nowait(
        TradeOutcome(
            outcome_id='out-ack',
            command_id=command_id,
            outcome_type=TradeOutcomeType.ACK,
            timestamp=_TS,
        ),
    )
    loop.tick_once()

    assert seen_in_flight == [Decimal('0')]
