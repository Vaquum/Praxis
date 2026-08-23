'''
TradeModify dataclass representing an amend instruction from Manager.

TradeModifies are immutable: once received, no field changes. References
the command_id of the TradeCommand to amend and carries the per-mode
ModifyParams describing the new absolute values.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.modify_params import ModifyParams

__all__ = ['TradeModify']


@dataclass(frozen=True)
class TradeModify:

    '''
    An amend instruction targeting a specific TradeCommand.

    Args:
        command_id (str): UUID of the TradeCommand to amend.
        account_id (str): Must match the original command account.
        reason (str): Reason for amending.
        modify_params (ModifyParams): Per-mode amend parameters carrying the
            new absolute values.
        created_at (datetime): Amend creation time, must be timezone-aware.
    '''

    command_id: str
    account_id: str
    reason: str
    modify_params: ModifyParams
    created_at: datetime

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('command_id', 'account_id', 'reason'):
            _require_str('TradeModify', field, getattr(self, field))

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            msg = 'TradeModify.created_at must be timezone-aware'
            raise ValueError(msg)
