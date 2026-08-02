'''
Live-only execution-mode classification.

Some execution modes rest non-MARKET orders on the venue — a protective
OCO (Bracket), a native-iceberg LIMIT (Iceberg), or a grid of resting
LIMIT rungs (Ladder DCA). The binsim paper simulator handles MARKET orders
only, so these modes cannot run against binsim and are classified
live-only. The launcher uses this to refuse enabling a live-only mode when
the selected venue is binsim, failing fast rather than surfacing a
confusing venue reject. This is keyed on binsim selection, not on paper
trade mode: paper on Binance testnet is a real venue that supports these
order types and is not restricted.
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
    '''Return whether an execution mode rests orders binsim cannot simulate.

    Args:
        mode (ExecutionMode): The execution mode to classify.

    Returns:
        bool: True when the mode rests non-MARKET orders that the binsim
            paper simulator (MARKET-only) cannot simulate.
    '''

    return mode in LIVE_ONLY_MODES
