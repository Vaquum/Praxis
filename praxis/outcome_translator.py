'''Translate Praxis-shape `TradeOutcome` events into Nexus-shape outcomes.

The Praxis `TradeOutcome` carries cumulative aggregate state per command
(`status`, `target_qty`, `filled_qty`, `avg_fill_price`). The Nexus
`TradeOutcome` carries per-event lifecycle deltas (`outcome_type`,
`fill_size`, `fill_price`, `fill_notional`, `actual_fees`,
`remaining_size`). The two share only `command_id`; bridging them is a
launcher-side concern so neither subsystem leaks types into the other.

A single Praxis outcome can produce zero, one, or two Nexus outcomes
depending on prior state:

* First PENDING for a command: emit `ACK`.
* First PARTIAL/FILLED with no prior `ACK`: emit `ACK` then the
  fill outcome with delta-derived fields.
* Subsequent PARTIAL/FILLED: emit a single fill outcome with delta
  fields computed from the cumulative aggregate.
* CANCELED/EXPIRED with `filled_qty > prior_filled_qty`: emit the
  intermediate `PARTIAL` first, then the terminal outcome with the
  remaining quantity.
* REJECTED, or CANCELED/EXPIRED with no fills: emit the terminal
  outcome directly.

Once a terminal outcome has been emitted, further outcomes for the same
`command_id` are dropped to keep the Nexus consumer's lifecycle
contract intact.
'''

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from decimal import Decimal

from nexus.infrastructure.praxis_connector.trade_outcome import (
    TradeOutcome as NexusTradeOutcome,
)
from nexus.infrastructure.praxis_connector.trade_outcome_type import (
    TradeOutcomeType,
)

from praxis.core.domain.enums import TradeStatus
from praxis.core.domain.trade_outcome import TradeOutcome as PraxisTradeOutcome

__all__ = ['OutcomeTranslator']

_log = logging.getLogger(__name__)

_ZERO = Decimal(0)


@dataclass
class _CommandState:

    last_filled_qty: Decimal = _ZERO
    last_cumulative_notional: Decimal = _ZERO
    ack_emitted: bool = False
    terminal_emitted: bool = False


class OutcomeTranslator:

    '''Convert Praxis `TradeOutcome` aggregates into Nexus delta outcomes.

    Args:
        fee_rate: Per-fill fee rate applied to `fill_notional` to derive
            `actual_fees` for fill outcomes. Defaults to `Decimal(0)`;
            paper trading on testnet does not charge real fees and the
            downstream `OutcomeProcessor` accepts a zero fee.
    '''

    def __init__(self, fee_rate: Decimal = _ZERO) -> None:

        if not isinstance(fee_rate, Decimal) or not fee_rate.is_finite():
            msg = f'fee_rate must be a finite Decimal, got {fee_rate!r}'
            raise ValueError(msg)

        if fee_rate < _ZERO:
            msg = f'fee_rate must be non-negative, got {fee_rate}'
            raise ValueError(msg)

        self._fee_rate = fee_rate
        self._state: dict[str, _CommandState] = {}
        self._terminal_command_ids: set[str] = set()
        self._lock = threading.Lock()

    def translate(
        self,
        outcome: PraxisTradeOutcome,
    ) -> list[NexusTradeOutcome]:

        '''Translate a Praxis `TradeOutcome` into zero or more Nexus outcomes.

        Maintains per-`command_id` state across calls so subsequent
        cumulative-aggregate inputs yield the correct deltas.

        Args:
            outcome: Praxis-shape outcome from `Trading.route_outcome`.

        Returns:
            Ordered list of Nexus-shape outcomes to enqueue. Empty when
            a terminal outcome has already been emitted for the
            command.
        '''

        with self._lock:
            if outcome.command_id in self._terminal_command_ids:
                _log.debug(
                    'dropping post-terminal outcome',
                    extra={
                        'command_id': outcome.command_id,
                        'status': outcome.status.value,
                    },
                )
                return []

            state = self._state.setdefault(outcome.command_id, _CommandState())

            results: list[NexusTradeOutcome] = []

            if outcome.status == TradeStatus.REJECTED:
                results.append(self._build_rejected(outcome))
                self._mark_terminal_locked(outcome.command_id, state)
                return results

            if outcome.status == TradeStatus.PENDING:
                if not state.ack_emitted:
                    results.append(self._build_ack(outcome))
                    state.ack_emitted = True
                return results

            cumulative_notional = (
                outcome.filled_qty * outcome.avg_fill_price
                if outcome.avg_fill_price is not None
                else _ZERO
            )
            delta_size = outcome.filled_qty - state.last_filled_qty
            delta_notional = cumulative_notional - state.last_cumulative_notional

            if outcome.status == TradeStatus.PARTIAL:
                if not state.ack_emitted:
                    results.append(self._build_ack(outcome))
                    state.ack_emitted = True
                if delta_size > _ZERO:
                    results.append(
                        self._build_partial(
                            outcome,
                            delta_size=delta_size,
                            delta_notional=delta_notional,
                        ),
                    )
                    state.last_filled_qty = outcome.filled_qty
                    state.last_cumulative_notional = cumulative_notional
                return results

            if outcome.status == TradeStatus.FILLED:
                if not state.ack_emitted:
                    results.append(self._build_ack(outcome))
                    state.ack_emitted = True
                if delta_size > _ZERO:
                    results.append(
                        self._build_filled(
                            outcome,
                            delta_size=delta_size,
                            delta_notional=delta_notional,
                        ),
                    )
                self._mark_terminal_locked(outcome.command_id, state)
                return results

            if outcome.status in (TradeStatus.CANCELED, TradeStatus.EXPIRED):
                if delta_size > _ZERO:
                    if not state.ack_emitted:
                        results.append(self._build_ack(outcome))
                        state.ack_emitted = True
                    results.append(
                        self._build_partial(
                            outcome,
                            delta_size=delta_size,
                            delta_notional=delta_notional,
                        ),
                    )
                    state.last_filled_qty = outcome.filled_qty
                    state.last_cumulative_notional = cumulative_notional
                results.append(self._build_terminal(outcome))
                self._mark_terminal_locked(outcome.command_id, state)
                return results

            msg = f'unhandled Praxis TradeStatus: {outcome.status!r}'
            raise ValueError(msg)

    def _mark_terminal_locked(
        self,
        command_id: str,
        state: _CommandState,
    ) -> None:

        state.terminal_emitted = True
        self._terminal_command_ids.add(command_id)
        self._state.pop(command_id, None)

    def _build_ack(self, outcome: PraxisTradeOutcome) -> NexusTradeOutcome:

        return NexusTradeOutcome(
            outcome_id=_new_outcome_id(),
            command_id=outcome.command_id,
            outcome_type=TradeOutcomeType.ACK,
            timestamp=outcome.created_at,
        )

    def _build_partial(
        self,
        outcome: PraxisTradeOutcome,
        *,
        delta_size: Decimal,
        delta_notional: Decimal,
    ) -> NexusTradeOutcome:

        delta_price = delta_notional / delta_size
        actual_fees = delta_notional * self._fee_rate
        remaining_size = outcome.target_qty - outcome.filled_qty

        return NexusTradeOutcome(
            outcome_id=_new_outcome_id(),
            command_id=outcome.command_id,
            outcome_type=TradeOutcomeType.PARTIAL,
            timestamp=outcome.created_at,
            fill_size=delta_size,
            fill_price=delta_price,
            fill_notional=delta_notional,
            actual_fees=actual_fees,
            remaining_size=remaining_size,
        )

    def _build_filled(
        self,
        outcome: PraxisTradeOutcome,
        *,
        delta_size: Decimal,
        delta_notional: Decimal,
    ) -> NexusTradeOutcome:

        delta_price = delta_notional / delta_size
        actual_fees = delta_notional * self._fee_rate

        return NexusTradeOutcome(
            outcome_id=_new_outcome_id(),
            command_id=outcome.command_id,
            outcome_type=TradeOutcomeType.FILLED,
            timestamp=outcome.created_at,
            fill_size=delta_size,
            fill_price=delta_price,
            fill_notional=delta_notional,
            actual_fees=actual_fees,
        )

    def _build_rejected(self, outcome: PraxisTradeOutcome) -> NexusTradeOutcome:

        reason = outcome.reason if outcome.reason else 'rejected'

        return NexusTradeOutcome(
            outcome_id=_new_outcome_id(),
            command_id=outcome.command_id,
            outcome_type=TradeOutcomeType.REJECTED,
            timestamp=outcome.created_at,
            reject_reason=reason,
        )

    def _build_terminal(self, outcome: PraxisTradeOutcome) -> NexusTradeOutcome:

        if outcome.status == TradeStatus.EXPIRED:
            outcome_type = TradeOutcomeType.EXPIRED
            cancel_reason = None
        else:
            outcome_type = TradeOutcomeType.CANCELED
            cancel_reason = outcome.reason if outcome.reason else None

        remaining_size = outcome.target_qty - outcome.filled_qty

        return NexusTradeOutcome(
            outcome_id=_new_outcome_id(),
            command_id=outcome.command_id,
            outcome_type=outcome_type,
            timestamp=outcome.created_at,
            remaining_size=remaining_size,
            cancel_reason=cancel_reason,
        )


def _new_outcome_id() -> str:

    return uuid.uuid4().hex
