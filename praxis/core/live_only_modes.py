'''
Live-only execution-mode classification.

Some execution modes rest non-MARKET orders on the venue — a protective
OCO (Bracket), a native-iceberg LIMIT (Iceberg), or a grid of resting
LIMIT rungs (Ladder DCA). The paper venue (binsim) simulates MARKET orders
only, so these modes cannot run against paper and are classified live-only.
The launcher uses this to refuse enabling a live-only mode under paper
trade mode, failing fast rather than surfacing a confusing venue reject.
'''

from __future__ import annotations

from praxis.core.domain.enums import ExecutionMode

__all__ = ['LIVE_ONLY_MODES', 'is_live_only']

LIVE_ONLY_MODES = frozenset(
    {
        ExecutionMode.BRACKET,
        ExecutionMode.ICEBERG,
        ExecutionMode.LADDER_DCA,
    },
)


def is_live_only(mode: ExecutionMode) -> bool:
    '''Return whether an execution mode requires a live (non-paper) venue.

    Args:
        mode (ExecutionMode): The execution mode to classify.

    Returns:
        bool: True when the mode rests non-MARKET orders that the paper
            venue cannot simulate.
    '''

    return mode in LIVE_ONLY_MODES
