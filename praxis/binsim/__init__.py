'''In-process Binance simulator for paper trading.'''

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import (
    Account,
    DuplicateClientOrderIdError,
    InsufficientBalanceError,
    Ledger,
    LedgerFill,
)
from praxis.binsim.server import (
    BOOK_KEY,
    LEDGER_KEY,
    POLLER_KEY,
    STALENESS_THRESHOLD_MS_KEY,
    WS_SUBSCRIPTION_COUNTER_KEY,
    BinsimServer,
    make_app,
)


__all__ = [
    'BOOK_KEY',
    'LEDGER_KEY',
    'POLLER_KEY',
    'STALENESS_THRESHOLD_MS_KEY',
    'WS_SUBSCRIPTION_COUNTER_KEY',
    'Account',
    'BinsimServer',
    'DepthPoller',
    'DuplicateClientOrderIdError',
    'InsufficientBalanceError',
    'Ledger',
    'LedgerFill',
    'OrderBook',
    'make_app',
]
