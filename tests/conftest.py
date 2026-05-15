from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
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
