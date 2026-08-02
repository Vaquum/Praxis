'''
ExecutionScheme projection for a multi-slice command.

Projects the SchemeInitialized and SchemeStateChanged events into
the live parent state of a running scheme: its immutable spec plus the
mutable scheduler cursor, cumulative fills, active children, next run
time, and lifecycle state. Mutation belongs in Trading State, not here.
'''

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from praxis.core.domain.enums import ExecutionMode, OrderSide, SchemeState

__all__ = ['ExecutionScheme']

_ZERO = Decimal(0)

_TERMINAL_STATES: frozenset[SchemeState] = frozenset({
    SchemeState.COMPLETED,
    SchemeState.CANCELED,
    SchemeState.FAILED,
})


@dataclass
class ExecutionScheme:

    '''
    Live parent state of a multi-slice execution scheme.

    Args:
        command_id (str): Scheme parent identifier.
        trade_id (str): Trade correlation identifier.
        execution_mode (ExecutionMode): The scheme's execution mode.
        symbol (str): Trading pair symbol.
        side (OrderSide): Order direction.
        total_qty (Decimal): Total base quantity to execute across children.
        slices_total (int): Planned number of children, or 0 when dynamic.
        cursor (int): Next child index.
        filled_qty (Decimal): Cumulative filled base quantity.
        active_client_order_ids (tuple[str, ...]): Child orders currently working.
        next_run_at (datetime | None): When the next child is due.
        state (SchemeState): Lifecycle state.
    '''

    command_id: str
    trade_id: str
    execution_mode: ExecutionMode
    symbol: str
    side: OrderSide
    total_qty: Decimal
    slices_total: int
    cursor: int = 0
    filled_qty: Decimal = _ZERO
    active_client_order_ids: tuple[str, ...] = field(default_factory=tuple)
    next_run_at: datetime | None = None
    state: SchemeState = SchemeState.RUNNING

    @property
    def is_terminal(self) -> bool:

        '''Return True if the scheme is in a terminal lifecycle state.'''

        return self.state in _TERMINAL_STATES
