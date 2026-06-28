'''Chart of accounts for the Praxis double-entry ledger (Account sub-system).

Accounts are carried in the quote asset (USDT). `Crypto:BTC` holds the
base asset at cost. Each account has a normal balance side: assets and
expenses are debit-normal (a debit increases them), income and equity are
credit-normal (a credit increases them).
'''

from __future__ import annotations

from enum import Enum

__all__ = ['Account', 'is_debit_normal']


class Account(Enum):

    '''A ledger account in the chart of accounts.'''

    CASH_USDT = 'Cash:USDT'
    CRYPTO_BTC = 'Crypto:BTC'
    REALIZED_PNL = 'Income:RealizedPnL'
    FEES = 'Expense:Fees'
    CONTRIBUTIONS = 'Equity:Contributions'


_DEBIT_NORMAL = frozenset({Account.CASH_USDT, Account.CRYPTO_BTC, Account.FEES})


def is_debit_normal(account: Account) -> bool:

    '''Return whether `account` increases on the debit side.

    Args:
        account: The account to classify.

    Returns:
        True for asset and expense accounts (`Cash:USDT`, `Crypto:BTC`,
        `Expense:Fees`); False for income and equity accounts
        (`Income:RealizedPnL`, `Equity:Contributions`).
    '''

    return account in _DEBIT_NORMAL
