'''
Represent trade-level execution outcome reported to Manager.

Frozen dataclass representing a point-in-time snapshot of trade
execution status. Both intermediate progress and terminal completion
use this type. Exactly one terminal outcome per command_id is
enforced upstream, not in this dataclass.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.enums import TradeStatus

__all__ = ['TradeOutcome']

_ZERO = Decimal(0)

_TERMINAL: frozenset[TradeStatus] = frozenset({
    TradeStatus.FILLED,
    TradeStatus.CANCELED,
    TradeStatus.REJECTED,
    TradeStatus.EXPIRED,
})


@dataclass(frozen=True)
class TradeOutcome:

    '''
    Represent execution outcome pushed from Trading sub-system to Manager.

    Args:
        command_id (str): Originating TradeCommand identifier.
        trade_id (str): Manager passthrough correlation identifier.
        account_id (str): Account identifier.
        status (TradeStatus): Current execution state.
        target_qty (Decimal | None): Original requested base-asset
            quantity, must be positive when set. `None` for quote-native
            MARKET BUY orders where the venue determines the executed
            base quantity from the strategy's quote-asset budget.
        filled_qty (Decimal): Cumulative filled quantity, must be non-negative.
        avg_fill_price (Decimal | None): VWAP of all fills, must be positive if set. None when no fills.
        slices_completed (int): Completed slices or steps, must be non-negative.
        slices_total (int): Total planned slices or steps, must be positive.
        reason (str | None): Descriptive reason for status.
        created_at (datetime): Outcome creation time, must be timezone-aware.
        cumulative_notional (Decimal): Venue-side cumulative notional for
            this command, sum of `qty * price` over all fills. FINAL-MAJOR-07:
            carried verbatim from `Order.cumulative_notional` so the
            OutcomeTranslator does not have to reverse-derive
            `cumulative_notional = filled_qty * avg_fill_price` (a
            precision-lossy round trip after the venue already did
            `total_notional / filled_qty` for `avg_fill_price`). Must be
            non-negative; must be zero when `filled_qty` is zero. Default
            `_ZERO` for synthetic / no-fill outcomes (boot-orphan REJECTED).
        execution_slippage_bps (Decimal | None): Signed displacement of
            `avg_fill_price` from the mid price sampled before submission,
            in basis points, as `(avg - mid) / mid * 10000`. Not an
            execution cost: it is not adjusted for side, so a SELL filling
            below the mid reads negative while being the worse outcome.
            None means no measurement is attached to this outcome, which
            covers a command with no estimate, nothing filled, a record
            written before the field existed, and — the case most likely
            to surprise — any outcome from a producer that does not
            measure. Only the submitting path holds the pre-submission
            estimate, so a WebSocket-driven outcome for the same command
            reports None even where an earlier immediate one carried a
            number.
        arrival_slippage_bps (Decimal | None): Signed displacement of
            `avg_fill_price` from the decision layer's reference price, in
            basis points, on the same terms and with the same meaning of
            None.

    Both are measured against `avg_fill_price` as reported here, which is
    the average of the fills admitted against `target_qty` rather than of
    every fill the venue returned. They are displacements of an execution
    price, exclusive of commission — not an all-in acquisition cost — and
    they do not describe an overfill's excess, which was never part of the
    trade requested.

    `filled_qty` is the only quantity these may be multiplied by. Joining
    them to a position or a wallet balance mixes populations: both carry
    what the venue delivered net of commission, which is neither the
    quantity these measure nor priced by them (see TD-156).
    '''

    command_id: str
    trade_id: str
    account_id: str
    status: TradeStatus
    target_qty: Decimal | None
    filled_qty: Decimal
    avg_fill_price: Decimal | None
    slices_completed: int
    slices_total: int
    reason: str | None
    created_at: datetime
    cumulative_notional: Decimal = _ZERO
    execution_slippage_bps: Decimal | None = None
    arrival_slippage_bps: Decimal | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('command_id', 'trade_id', 'account_id'):
            _require_str('TradeOutcome', field, getattr(self, field))

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            msg = 'TradeOutcome.created_at must be timezone-aware'
            raise ValueError(msg)

        if self.target_qty is not None and (
            not isinstance(self.target_qty, Decimal)
            or not self.target_qty.is_finite()
            or self.target_qty <= _ZERO
        ):
            msg = 'TradeOutcome.target_qty must be a finite positive Decimal'
            raise ValueError(msg)

        if self.filled_qty < _ZERO:
            msg = 'TradeOutcome.filled_qty must be non-negative'
            raise ValueError(msg)

        if self.target_qty is not None and self.filled_qty > self.target_qty:
            msg = 'TradeOutcome.filled_qty cannot exceed target_qty'
            raise ValueError(msg)

        if self.avg_fill_price is not None and self.avg_fill_price <= _ZERO:
            msg = 'TradeOutcome.avg_fill_price must be positive'
            raise ValueError(msg)

        if self.filled_qty == _ZERO and self.avg_fill_price is not None:
            msg = 'TradeOutcome.avg_fill_price must be None when filled_qty is zero'
            raise ValueError(msg)

        if self.slices_completed < 0:
            msg = 'TradeOutcome.slices_completed must be non-negative'
            raise ValueError(msg)

        if self.slices_total <= 0:
            msg = 'TradeOutcome.slices_total must be positive'
            raise ValueError(msg)

        if self.slices_completed > self.slices_total:
            msg = 'TradeOutcome.slices_completed cannot exceed slices_total'
            raise ValueError(msg)

        if self.cumulative_notional < _ZERO:
            msg = 'TradeOutcome.cumulative_notional must be non-negative'
            raise ValueError(msg)

        if self.filled_qty == _ZERO and self.cumulative_notional != _ZERO:
            msg = 'TradeOutcome.cumulative_notional must be zero when filled_qty is zero'
            raise ValueError(msg)

        if self.filled_qty > _ZERO and self.cumulative_notional == _ZERO:
            msg = 'TradeOutcome.cumulative_notional must be positive when filled_qty is positive'
            raise ValueError(msg)

    @property
    def is_terminal(self) -> bool:

        '''Return True if the outcome represents a terminal state.'''

        return self.status in _TERMINAL

    @property
    def fill_ratio(self) -> Decimal | None:

        '''Return the ratio of filled quantity to target quantity.

        Returns `None` for quote-native orders where `target_qty` is
        unknown ahead of fill.
        '''

        if self.target_qty is None or self.target_qty == _ZERO:
            return None

        return self.filled_qty / self.target_qty
