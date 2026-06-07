'''
TradeCommand dataclass representing an execution instruction from Manager.

TradeCommands are immutable: once received from Manager, no field
changes. The Trading sub-system assigns the command_id.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams

__all__ = ['TradeCommand']

_ZERO = Decimal(0)


@dataclass(frozen=True)
class TradeCommand:

    '''
    Represent an execution instruction from Manager to the Trading sub-system.

    Args:
        command_id (str): UUID assigned by the Trading sub-system.
        trade_id (str): Manager correlation identifier.
        account_id (str): Target account identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Order direction.
        qty (Decimal | None): Total base-asset quantity to execute, must
            be positive if set. Mutually exclusive with `quote_qty`.
        quote_qty (Decimal | None): Quote-asset spend (e.g. USDT) for
            MARKET BUY orders. The venue determines the executed base
            quantity from live liquidity. Must be positive if set.
            Mutually exclusive with `qty`.
        order_type (OrderType): Order type.
        execution_mode (ExecutionMode): Execution strategy.
        execution_params (SingleShotParams): Execution parameters for single-shot mode.
        timeout (int): Execution deadline in seconds, must be positive.
        reference_price (Decimal | None): Optional reference price from Manager, must be positive if set.
        maker_preference (MakerPreference): Maker/taker preference.
        stp_mode (STPMode): Self-trade prevention mode.
        created_at (datetime): Command creation time, must be timezone-aware.
    '''

    command_id: str
    trade_id: str
    account_id: str
    symbol: str
    side: OrderSide
    qty: Decimal | None
    order_type: OrderType
    execution_mode: ExecutionMode
    execution_params: SingleShotParams
    timeout: int
    reference_price: Decimal | None
    maker_preference: MakerPreference
    stp_mode: STPMode
    created_at: datetime
    quote_qty: Decimal | None = None

    @property
    def is_quote_native(self) -> bool:
        '''Return True when the command was sized in quote units (USDT).'''

        return self.quote_qty is not None

    def __post_init__(self) -> None:

        '''Validate invariants at construction time.'''

        for field in ('command_id', 'trade_id', 'account_id', 'symbol'):
            _require_str('TradeCommand', field, getattr(self, field))

        if (self.qty is None) == (self.quote_qty is None):
            msg = 'TradeCommand requires exactly one of qty or quote_qty'
            raise ValueError(msg)

        if self.qty is not None and (
            not isinstance(self.qty, Decimal)
            or not self.qty.is_finite()
            or self.qty <= _ZERO
        ):
            msg = 'TradeCommand.qty must be a finite positive Decimal'
            raise ValueError(msg)

        if self.quote_qty is not None and (
            not isinstance(self.quote_qty, Decimal)
            or not self.quote_qty.is_finite()
            or self.quote_qty <= _ZERO
        ):
            msg = 'TradeCommand.quote_qty must be a finite positive Decimal'
            raise ValueError(msg)

        if self.timeout <= 0:
            msg = 'TradeCommand.timeout must be positive'
            raise ValueError(msg)

        if self.reference_price is not None and self.reference_price <= _ZERO:
            msg = 'TradeCommand.reference_price must be positive'
            raise ValueError(msg)

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            msg = 'TradeCommand.created_at must be timezone-aware'
            raise ValueError(msg)

        if (
            self.execution_mode is ExecutionMode.SINGLE_SHOT
            and not isinstance(self.execution_params, SingleShotParams)
        ):
            msg = 'execution_params must be SingleShotParams for SINGLE_SHOT mode'
            raise TypeError(msg)
