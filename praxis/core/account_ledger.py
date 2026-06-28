'''Double-entry ledger projection for the Praxis Account sub-system.

`AccountLedger` is rebuilt by replaying Event Spine events. Each fill
posts a balanced `JournalEntry` and updates account balances; realized
P&L on a sell is computed against the position's cost basis. Like
`TradingState`, this is a derived view of the event log, not an
independent store.

Cost basis is chosen per account — FIFO or weighted-average (AVERAGE).
Fees are expensed to `Expense:Fees`; the base asset is carried at trade
price (fees are not capitalised), so realized P&L is the proceeds less the
lot cost (FIFO or average) and fees stand alone.
'''

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from praxis.core.domain.chart_of_accounts import Account, is_debit_normal
from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import Event, FillReceived, TradeClosed
from praxis.core.domain.journal_entry import JournalEntry, JournalLine

__all__ = ['AccountLedger', 'CostBasisMethod']

_log = logging.getLogger(__name__)

_ZERO = Decimal(0)
_QUOTE_ASSET = 'USDT'


class CostBasisMethod(Enum):

    '''Cost-basis method for realizing P&L on a sell.'''

    FIFO = 'FIFO'
    AVERAGE = 'AVERAGE'


@dataclass
class _Lot:

    qty: Decimal
    unit_cost: Decimal


class AccountLedger:

    '''In-memory double-entry ledger projection for one account.

    Args:
        account_id: Account this ledger belongs to.
        cost_basis_method: Method for realizing P&L on a sell — `FIFO` or
            `AVERAGE` (weighted average). Set immutably per account.
    '''

    def __init__(
        self,
        account_id: str,
        cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO,
    ) -> None:

        if not account_id:
            msg = 'AccountLedger.account_id must be a non-empty string'
            raise ValueError(msg)

        if not isinstance(cost_basis_method, CostBasisMethod):
            msg = f'unsupported cost_basis_method: {cost_basis_method}'
            raise ValueError(msg)

        self.account_id = account_id
        self.cost_basis_method = cost_basis_method
        self.balances: dict[Account, Decimal] = dict.fromkeys(Account, _ZERO)
        self.journal: list[JournalEntry] = []
        self._lots: dict[str, deque[_Lot]] = {}
        self._lock = threading.Lock()

    def apply(self, event: Event) -> None:

        '''Apply a single event, posting a journal entry where it books.

        Args:
            event: Domain event to project.
        '''

        if isinstance(event, FillReceived):
            self._on_fill_received(event)

        elif isinstance(event, TradeClosed):
            return

    def _on_fill_received(self, event: FillReceived) -> None:

        if event.fee_asset != _QUOTE_ASSET:
            msg = f'fee_asset {event.fee_asset!r} not yet supported (only {_QUOTE_ASSET})'
            raise NotImplementedError(msg)

        if event.side is OrderSide.BUY:
            self._post(self._buy_entry(event))

        else:
            self._post(self._sell_entry(event))

    def _buy_entry(self, event: FillReceived) -> JournalEntry:

        notional = event.qty * event.price
        lines = [
            JournalLine(Account.CRYPTO_BTC, notional, _ZERO),
            JournalLine(Account.CASH_USDT, _ZERO, notional),
        ]
        lines.extend(self._fee_lines(event.fee))
        self._add_lot(event.trade_id, event.qty, event.price)

        return self._entry(event, 'buy fill', lines)

    def _add_lot(self, trade_id: str, qty: Decimal, price: Decimal) -> None:

        lots = self._lots.setdefault(trade_id, deque())

        if self.cost_basis_method is CostBasisMethod.AVERAGE and lots:
            existing = lots[0]
            total_qty = existing.qty + qty
            existing.unit_cost = (existing.qty * existing.unit_cost + qty * price) / total_qty
            existing.qty = total_qty

            return

        lots.append(_Lot(qty, price))

    def _sell_entry(self, event: FillReceived) -> JournalEntry:

        proceeds = event.qty * event.price
        cost = self._consume_lots(event.trade_id, event.qty)
        realized = proceeds - cost
        lines = [
            JournalLine(Account.CASH_USDT, proceeds, _ZERO),
            JournalLine(Account.CRYPTO_BTC, _ZERO, cost),
        ]

        if realized > _ZERO:
            lines.append(JournalLine(Account.REALIZED_PNL, _ZERO, realized))

        elif realized < _ZERO:
            lines.append(JournalLine(Account.REALIZED_PNL, -realized, _ZERO))

        lines.extend(self._fee_lines(event.fee))

        return self._entry(event, 'sell fill', lines)

    def _consume_lots(self, trade_id: str, qty: Decimal) -> Decimal:

        lots = self._lots.get(trade_id)
        remaining = qty
        cost = _ZERO

        while remaining > _ZERO and lots:

            lot = lots[0]
            taken = min(remaining, lot.qty)
            cost += taken * lot.unit_cost
            lot.qty -= taken
            remaining -= taken

            if lot.qty <= _ZERO:
                lots.popleft()

        if remaining > _ZERO:
            msg = f'sell qty exceeds open lots for trade_id={trade_id!r} by {remaining}'
            raise ValueError(msg)

        return cost

    @staticmethod
    def _fee_lines(fee: Decimal) -> list[JournalLine]:

        if fee <= _ZERO:
            return []

        return [
            JournalLine(Account.FEES, fee, _ZERO),
            JournalLine(Account.CASH_USDT, _ZERO, fee),
        ]

    @staticmethod
    def _entry(event: FillReceived, memo: str, lines: list[JournalLine]) -> JournalEntry:

        return JournalEntry(
            timestamp=event.timestamp,
            trade_id=event.trade_id,
            command_id=event.command_id,
            memo=memo,
            lines=tuple(lines),
        )

    def _post(self, entry: JournalEntry) -> None:

        with self._lock:
            self.journal.append(entry)

            for line in entry.lines:
                delta = line.debit - line.credit if is_debit_normal(line.account) else line.credit - line.debit
                self.balances[line.account] += delta
