'''Per-trade realized P&L record for the Account sub-system.

Accumulated by `AccountLedger` per `trade_id`: realized gross P&L from
sells (proceeds less lot cost), the trade's fees, and whether the trade
has been closed. Net P&L is gross less fees.
'''

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ['TradePnL']

_ZERO = Decimal(0)


@dataclass
class TradePnL:

    '''Realized P&L accumulated for one trade (`trade_id`).

    Args:
        trade_id: Trade correlation identifier.
        realized_gross: Realized P&L from sells, before fees.
        fees: Total fees booked against this trade.
        closed: Whether a `TradeClosed` event has finalized the trade.
    '''

    trade_id: str
    realized_gross: Decimal = _ZERO
    fees: Decimal = _ZERO
    closed: bool = False

    @property
    def net(self) -> Decimal:

        '''Return realized P&L net of fees (`realized_gross - fees`).'''

        return self.realized_gross - self.fees
