'''In-process Binance simulator for paper trading.'''

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller


__all__ = ['DepthPoller', 'OrderBook']
