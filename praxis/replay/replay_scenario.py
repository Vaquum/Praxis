'''Inputs for a replay run: the series, its bars, and the strategy.'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.infrastructure.venue_adapter import SymbolFilters

__all__ = ['ReplayBar', 'ReplayScenario']


@dataclass(frozen=True)
class ReplayBar:
    '''One historical bar paired with its prediction.

    Args:
        ts_ns: Shared `ts` (UTC epoch nanoseconds) of the prediction and
            OHLCV frames — the bucket open for time bars, the settle for
            dollar bars.
        settle: The instant the bar is closed; the replay clock advances
            here before the bar is dispatched. Equals `ts_ns` (as a
            datetime) for dollar bars and `ts_ns + interval` for time
            bars.
        open: The bar's open price; the intrabar move `close - open` is the
            Limen-parity entry-bar return.
        close: The bar's close price, used as the fill price.
        prediction: Binary signal, 0 (exit) or 1 (enter).
        probability: Model probability carried on the signal.
        start_ts_ns: The bar's open `ts` for dollar bars (whose `ts_ns`
            is the settle); None for time bars. Its presence makes the
            OHLCV frame carry a `start_ts` column, which is how the price
            store classifies the series as dollar-family.
    '''

    ts_ns: int
    settle: datetime
    open: float
    close: float
    prediction: int
    probability: float
    start_ts_ns: int | None = None


@dataclass(frozen=True)
class ReplayScenario:
    '''A single-series replay run definition.

    Args:
        account_id: Account the replay books against.
        series: Conduit series identifier, e.g. 'time_15m'.
        interval_seconds: For time bars the bar width; for dollar bars
            the predict cadence, used only as the staleness window since
            dollar bars have no fixed time width.
        symbol: Trading pair, e.g. 'BTCUSDT'.
        capital_pool: Starting quote capital.
        filters: Venue filters for the symbol.
        strategy_source: Strategy module text defining a `Strategy` class.
        bars: Settle-ordered bars to replay.
    '''

    account_id: str
    series: str
    interval_seconds: int
    symbol: str
    capital_pool: Decimal
    filters: SymbolFilters
    strategy_source: str
    bars: tuple[ReplayBar, ...]
