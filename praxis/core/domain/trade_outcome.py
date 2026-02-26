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
        target_qty (Decimal): Original requested quantity, must be positive.
        filled_qty (Decimal): Cumulative filled quantity, must be non-negative.
        avg_fill_price (Decimal | None): VWAP of all fills, must be positive if set. None when no fills.
        slices_completed (int): Completed slices or steps, must be non-negative.
        slices_total (int): Total planned slices or steps, must be positive.
        reason (str | None): Descriptive reason for status.
        missed_iterations (int | None): Skipped DCA iterations, must be non-negative if set.
        missed_reason (str | None): Why DCA iterations were missed.
        created_at (datetime): Outcome creation time, must be timezone-aware.
    '''

    command_id: str
    trade_id: str
    account_id: str
    status: TradeStatus
    target_qty: Decimal
    filled_qty: Decimal
    avg_fill_price: Decimal | None
    slices_completed: int
    slices_total: int
    reason: str | None
    created_at: datetime
    missed_iterations: int | None = None
    missed_reason: str | None = None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('command_id', 'trade_id', 'account_id'):
            _require_str('TradeOutcome', field, getattr(self, field))

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            msg = 'TradeOutcome.created_at must be timezone-aware'
            raise ValueError(msg)

        if self.target_qty <= _ZERO:
            msg = 'TradeOutcome.target_qty must be positive'
            raise ValueError(msg)

        if self.filled_qty < _ZERO:
            msg = 'TradeOutcome.filled_qty must be non-negative'
            raise ValueError(msg)

        if self.filled_qty > self.target_qty:
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

        if self.missed_iterations is not None and self.missed_iterations < 0:
            msg = 'TradeOutcome.missed_iterations must be non-negative'
            raise ValueError(msg)

    @property
    def is_terminal(self) -> bool:

        '''Return True if the outcome represents a terminal state.'''

        return self.status in _TERMINAL

    @property
    def fill_ratio(self) -> Decimal:

        '''Return the ratio of filled quantity to target quantity.'''

        return self.filled_qty / self.target_qty
