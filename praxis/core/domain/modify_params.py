'''
Amend parameter types keyed by execution mode.

Defines the ModifyParams union — the per-mode amend object carried on a
TradeModify — and MODIFY_PARAMS_FOR_MODE, the registry mapping each
ExecutionMode to its amend-parameter type. Mirrors ExecutionParams and
PARAMS_FOR_MODE so a modify's amend shape matches the mode being amended.
'''

from __future__ import annotations

from praxis.core.domain.bracket_modify import BracketModify
from praxis.core.domain.enums import ExecutionMode
from praxis.core.domain.iceberg_modify import IcebergModify
from praxis.core.domain.interval_slice_modify import IntervalSliceModify
from praxis.core.domain.ladder_dca_modify import LadderDcaModify
from praxis.core.domain.scheduled_vwap_modify import ScheduledVwapModify
from praxis.core.domain.single_shot_modify import SingleShotModify

__all__ = ['MODIFY_PARAMS_FOR_MODE', 'ModifyParams']

ModifyParams = (
    SingleShotModify
    | BracketModify
    | IntervalSliceModify
    | ScheduledVwapModify
    | IcebergModify
    | LadderDcaModify
)

MODIFY_PARAMS_FOR_MODE: dict[ExecutionMode, type[ModifyParams]] = {
    ExecutionMode.SINGLE_SHOT: SingleShotModify,
    ExecutionMode.BRACKET: BracketModify,
    ExecutionMode.TWAP: IntervalSliceModify,
    ExecutionMode.TIME_DCA: IntervalSliceModify,
    ExecutionMode.SCHEDULED_VWAP: ScheduledVwapModify,
    ExecutionMode.ICEBERG: IcebergModify,
    ExecutionMode.LADDER_DCA: LadderDcaModify,
}
