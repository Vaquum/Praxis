from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pandas as pd
import polars as pl
import pytest
import pytest_asyncio

from praxis.infrastructure.event_spine import EventSpine


@pytest_asyncio.fixture
async def spine() -> AsyncGenerator[EventSpine, None]:
    async with aiosqlite.connect(':memory:') as conn:
        es = EventSpine(conn)
        await es.ensure_schema()
        yield es


@pytest.fixture
def mock_market_data_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    '''Stub MainCache's data sources + redirect MAIN_CACHE_DIR.

    Launcher tests that exercise `_start_poller` would otherwise:
    - try to mkdir `/var/lib/praxis/maincache` (permission denied
      on dev machines), and
    - hit Hugging Face for the Limen snapshot + Binance for the
      binancial trailing fill (network IO from a unit test).

    This fixture redirects `MAIN_CACHE_DIR` to `tmp_path/maincache`
    and mocks both data sources to return empty frames so the cache
    bootstrap + scheduler start without any real IO.
    '''

    monkeypatch.setenv('MAIN_CACHE_DIR', str(tmp_path / 'maincache'))

    with (
        patch('praxis.market_data_cache.HistoricalData') as mock_hd,
        patch(
            'praxis.market_data_cache.get_spot_klines',
            return_value=pd.DataFrame(),
        ),
    ):
        mock_hd.return_value.get_spot_klines.return_value = pl.DataFrame()
        yield


def make_canonical_klines(start_ts: datetime, count: int) -> pl.DataFrame:

    '''Build a 17-column 1-min kline frame matching the canonical Limen shape.

    Used by `tests/test_market_data_cache.py` and
    `tests/test_market_data_poller.py` for synthetic kline frames;
    the columns and order match Limen's `HistoricalData.get_spot_klines`
    output (which is what `MainCache` stores on disk).

    Args:
        start_ts: Timestamp of the first bar; subsequent bars are
            `start_ts + i*1min` for `i in range(count)`.
        count: Number of consecutive 1-min bars to emit.

    Returns:
        pl.DataFrame: 17-column frame with synthetic numeric values.
    '''

    return pl.DataFrame({
        'datetime': [start_ts + timedelta(minutes=i) for i in range(count)],
        'open': [50000.0 + i for i in range(count)],
        'high': [50100.0 + i for i in range(count)],
        'low': [49900.0 + i for i in range(count)],
        'close': [50050.0 + i for i in range(count)],
        'mean': [50025.0 + i for i in range(count)],
        'std': [10.0] * count,
        'volume': [1.0] * count,
        'maker_ratio': [0.5] * count,
        'no_of_trades': [100] * count,
        'open_liquidity': [50.0] * count,
        'high_liquidity': [55.0] * count,
        'low_liquidity': [49.0] * count,
        'close_liquidity': [51.0] * count,
        'liquidity_sum': [205.0] * count,
        'maker_volume': [0.5] * count,
        'maker_liquidity': [102.5] * count,
    })
