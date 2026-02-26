'''
TradeAbort dataclass representing a cancel instruction from Manager.

TradeAborts are immutable: once received, no field changes. References
the command_id of the TradeCommand to cancel.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from praxis.core.domain._require_str import _require_str

__all__ = ['TradeAbort']


@dataclass(frozen=True)
class TradeAbort:

    '''
    A cancel instruction targeting a specific TradeCommand.

    Args:
        command_id (str): UUID of the TradeCommand to abort.
        account_id (str): Must match the original command account.
        reason (str): Reason for aborting.
        created_at (datetime): Abort creation time, must be timezone-aware.
    '''

    command_id: str
    account_id: str
    reason: str
    created_at: datetime

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('command_id', 'account_id', 'reason'):
            _require_str('TradeAbort', field, getattr(self, field))

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            msg = 'TradeAbort.created_at must be timezone-aware'
            raise ValueError(msg)
