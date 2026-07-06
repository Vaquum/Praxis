'''Double-entry ledger projection for the Praxis Account sub-system.

`AccountLedger` is rebuilt by replaying Event Spine events. Each fill
posts a balanced `JournalEntry` and updates account balances; realized
P&L on a sell is computed against the position's cost basis. Like
`TradingState`, this is a derived view of the event log, not an
independent store.

Cost basis is chosen per account — FIFO or weighted-average (AVERAGE).
Fees are expensed to `Expense:Fees`; the base asset is carried at trade
price (fees are not capitalised), so realized P&L is the proceeds less the
lot cost (FIFO or average) and fees stand alone. A quote-asset (`USDT`)
fee credits `Cash:USDT`; a base-asset (`BTC`) fee — charged on a buy — is
valued at the fill price, credits `Crypto:BTC`, and reduces the booked lot
to the net quantity received. Any other fee asset is unsupported.
'''

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from praxis.core.domain.chart_of_accounts import Account, is_debit_normal
from praxis.core.domain.enums import CostBasisMethod, FundDirection, OrderSide
from praxis.core.domain.events import (
    Event,
    FillReceived,
    FundTransaction,
    RegisterAccount,
    TradeClosed,
)
from praxis.core.domain.journal_entry import JournalEntry, JournalLine
from praxis.core.domain.trade_pnl import TradePnL

__all__ = ['AccountLedger', 'CostBasisMethod']

_log = logging.getLogger(__name__)

_ZERO = Decimal(0)
_QUOTE_ASSET = 'USDT'
_BASE_ASSET = 'BTC'


@dataclass
class _Lot:

    qty: Decimal
    unit_cost: Decimal


class AccountLedger:

    '''In-memory double-entry ledger projection for one account.

    The ledger starts unregistered: a `RegisterAccount` event fixes the
    per-account `cost_basis_method` immutably and must be applied before any
    fill or trade-closed event.

    Args:
        account_id: Account this ledger belongs to.
    '''

    def __init__(self, account_id: str) -> None:

        if not account_id:
            msg = 'AccountLedger.account_id must be a non-empty string'
            raise ValueError(msg)

        self.account_id = account_id
        self.cost_basis_method: CostBasisMethod | None = None
        self.balances: dict[Account, Decimal] = dict.fromkeys(Account, _ZERO)
        self.trades: dict[str, TradePnL] = {}
        self.journal: list[JournalEntry] = []
        self._lots: dict[str, deque[_Lot]] = {}
        self._registered = False
        self._lock = threading.Lock()

    def apply(self, event: Event) -> None:

        '''Apply a single event, posting a journal entry where it books.

        Args:
            event: Domain event to project.

        Raises:
            ValueError: A `RegisterAccount` re-registers an already-registered
                account, or a fill or trade-closed event arrives before the
                account is registered.
        '''

        if isinstance(event, RegisterAccount):
            self._on_register_account(event)

            return

        if not self._registered:
            msg = f'account {self.account_id!r} not registered; apply RegisterAccount first'
            raise ValueError(msg)

        if isinstance(event, FillReceived):
            self._on_fill_received(event)

        elif isinstance(event, TradeClosed):
            self._on_trade_closed(event)

        elif isinstance(event, FundTransaction):
            self._on_fund_transaction(event)

    def state(self) -> dict[str, Any]:

        '''Return the resumable projection state as a JSON-serialisable dict.

        Holds balances, per-trade P&L, and open cost-basis lots — the
        derived state needed to resume without replaying from genesis.
        The journal is the audit trail and is not part of this state.
        '''

        with self._lock:
            return {
                'account_id': self.account_id,
                'registered': self._registered,
                'cost_basis_method': self.cost_basis_method.value if self.cost_basis_method is not None else None,
                'balances': {account.value: str(amount) for account, amount in self.balances.items()},
                'trades': {
                    trade_id: {
                        'realized_gross': str(trade.realized_gross),
                        'fees': str(trade.fees),
                        'closed': trade.closed,
                    }
                    for trade_id, trade in self.trades.items()
                },
                'lots': {
                    trade_id: [{'qty': str(lot.qty), 'unit_cost': str(lot.unit_cost)} for lot in lots]
                    for trade_id, lots in self._lots.items()
                },
            }

    def read_balances(self) -> dict[Account, Decimal]:

        '''Return a copy of the current account balances by ledger account.'''

        with self._lock:
            return dict(self.balances)

    def read_trade_pnls(self) -> dict[str, TradePnL]:

        '''Return copies of the per-trade realized P&L, keyed by `trade_id`.'''

        with self._lock:
            return {trade_id: replace(trade) for trade_id, trade in self.trades.items()}

    def to_snapshot(self, last_applied_event_seq: int, epoch_id: int) -> dict[str, Any]:

        '''Return a snapshot of the ledger tagged with its spine position.

        Args:
            last_applied_event_seq: Sequence of the last event applied.
            epoch_id: Epoch the snapshot belongs to.
        '''

        return {
            'last_applied_event_seq': last_applied_event_seq,
            'epoch_id': epoch_id,
            'state': self.state(),
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> AccountLedger:

        '''Rebuild a ledger from a `to_snapshot` payload (journal not restored).'''

        state = snapshot['state']
        ledger = cls(state['account_id'])

        method = state['cost_basis_method']
        if method is not None:
            ledger.cost_basis_method = CostBasisMethod(method)

        ledger._registered = state.get('registered', method is not None)

        for account_value, amount in state['balances'].items():
            ledger.balances[Account(account_value)] = Decimal(amount)

        ledger.trades = {
            trade_id: TradePnL(trade_id, Decimal(t['realized_gross']), Decimal(t['fees']), t['closed'])
            for trade_id, t in state['trades'].items()
        }
        ledger._lots = {
            trade_id: deque(_Lot(Decimal(lot['qty']), Decimal(lot['unit_cost'])) for lot in lots)
            for trade_id, lots in state['lots'].items()
        }

        return ledger

    def _on_register_account(self, event: RegisterAccount) -> None:

        with self._lock:
            if self._registered:
                msg = f'account {self.account_id!r} already registered; cost_basis_method is immutable'
                raise ValueError(msg)

            self.cost_basis_method = CostBasisMethod(event.cost_basis_method)
            self._registered = True

    def _on_fill_received(self, event: FillReceived) -> None:

        if event.side is OrderSide.BUY:
            entry, fee_value = self._buy_entry(event)
            realized = _ZERO

        else:
            entry, realized, fee_value = self._sell_entry(event)

        self._post(entry, event.trade_id, realized, fee_value)

    def _on_trade_closed(self, event: TradeClosed) -> None:

        with self._lock:
            trade = self.trades.get(event.trade_id)

            if trade is not None:
                trade.closed = True

    def _on_fund_transaction(self, event: FundTransaction) -> None:

        if event.direction == FundDirection.DEPOSIT.value:
            lines = [
                JournalLine(Account.CASH_USDT, event.amount, _ZERO),
                JournalLine(Account.CONTRIBUTIONS, _ZERO, event.amount),
            ]
            memo = 'deposit'

        else:
            lines = [
                JournalLine(Account.CONTRIBUTIONS, event.amount, _ZERO),
                JournalLine(Account.CASH_USDT, _ZERO, event.amount),
            ]
            memo = 'withdrawal'

        entry = JournalEntry(
            timestamp=event.timestamp,
            source_event_type='FundTransaction',
            source_event_id=event.fund_transaction_id,
            memo=memo,
            lines=tuple(lines),
        )

        with self._lock:
            self._post_entry(entry)

    def _buy_entry(self, event: FillReceived) -> tuple[JournalEntry, Decimal]:

        notional = event.qty * event.price
        lines = [
            JournalLine(Account.CRYPTO_BTC, notional, _ZERO),
            JournalLine(Account.CASH_USDT, _ZERO, notional),
        ]

        if event.fee_asset == _QUOTE_ASSET:
            fee_value = event.fee
            lines.extend(self._fee_lines(fee_value, Account.CASH_USDT))
            lot_qty = event.qty

        elif event.fee_asset == _BASE_ASSET:
            if event.fee >= event.qty:
                msg = f'base-asset fee {event.fee} must be smaller than the filled qty {event.qty}'
                raise ValueError(msg)

            fee_value = event.fee * event.price
            lines.extend(self._fee_lines(fee_value, Account.CRYPTO_BTC))
            lot_qty = event.qty - event.fee

        else:
            msg = f'fee_asset {event.fee_asset!r} not supported for a buy fill'
            raise NotImplementedError(msg)

        self._add_lot(event.trade_id, lot_qty, event.price)

        return self._entry(event, 'buy fill', lines), fee_value

    def _add_lot(self, trade_id: str, qty: Decimal, price: Decimal) -> None:

        lots = self._lots.setdefault(trade_id, deque())

        if self.cost_basis_method is CostBasisMethod.AVERAGE and lots:
            existing = lots[0]
            total_qty = existing.qty + qty
            existing.unit_cost = (existing.qty * existing.unit_cost + qty * price) / total_qty
            existing.qty = total_qty

            return

        lots.append(_Lot(qty, price))

    def _sell_entry(self, event: FillReceived) -> tuple[JournalEntry, Decimal, Decimal]:

        if event.fee_asset != _QUOTE_ASSET:
            msg = f'fee_asset {event.fee_asset!r} not supported for a sell fill'
            raise NotImplementedError(msg)

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

        lines.extend(self._fee_lines(event.fee, Account.CASH_USDT))

        return self._entry(event, 'sell fill', lines), realized, event.fee

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
    def _fee_lines(fee_value: Decimal, credit_account: Account) -> list[JournalLine]:

        if fee_value <= _ZERO:
            return []

        return [
            JournalLine(Account.FEES, fee_value, _ZERO),
            JournalLine(credit_account, _ZERO, fee_value),
        ]

    @staticmethod
    def _entry(event: FillReceived, memo: str, lines: list[JournalLine]) -> JournalEntry:

        return JournalEntry(
            timestamp=event.timestamp,
            source_event_type='FillReceived',
            source_event_id=event.venue_trade_id,
            memo=memo,
            lines=tuple(lines),
        )

    def _post_entry(self, entry: JournalEntry) -> None:

        self.journal.append(entry)

        for line in entry.lines:
            delta = line.debit - line.credit if is_debit_normal(line.account) else line.credit - line.debit
            self.balances[line.account] += delta

    def _post(self, entry: JournalEntry, trade_id: str, realized: Decimal, fee: Decimal) -> None:

        with self._lock:
            self._post_entry(entry)

            trade = self.trades.setdefault(trade_id, TradePnL(trade_id))
            trade.realized_gross += realized
            trade.fees += fee
