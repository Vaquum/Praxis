'''
Execution parameter types keyed by execution mode.

Defines the ExecutionParams union — the per-mode parameter object carried on
a TradeCommand — and PARAMS_FOR_MODE, the registry mapping each
ExecutionMode to its parameter type.
'''

from __future__ import annotations

from praxis.core.domain.bracket_params import BracketParams
from praxis.core.domain.enums import ExecutionMode
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.ladder_dca_params import LadderDcaParams
from praxis.core.domain.scheduled_vwap_params import ScheduledVwapParams
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.time_dca_params import TimeDcaParams
from praxis.core.domain.twap_params import TwapParams

__all__ = ['PARAMS_FOR_MODE', 'ExecutionParams']

ExecutionParams = (
    SingleShotParams
    | BracketParams
    | TwapParams
    | TimeDcaParams
    | ScheduledVwapParams
    | IcebergParams
    | LadderDcaParams
)

PARAMS_FOR_MODE: dict[ExecutionMode, type[ExecutionParams]] = {
    ExecutionMode.SINGLE_SHOT: SingleShotParams,
    ExecutionMode.BRACKET: BracketParams,
    ExecutionMode.TWAP: TwapParams,
    ExecutionMode.TIME_DCA: TimeDcaParams,
    ExecutionMode.SCHEDULED_VWAP: ScheduledVwapParams,
    ExecutionMode.ICEBERG: IcebergParams,
    ExecutionMode.LADDER_DCA: LadderDcaParams,
}
