'''Tests for praxis.infrastructure.mytrades_backfill.paginate_my_trades.'''

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide
from praxis.infrastructure.mytrades_backfill import paginate_my_trades
from praxis.infrastructure.venue_adapter import VenueTrade

_TS = datetime(2026, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_SYMBOL = 'BTCUSDT'


def _trade(trade_id: int) -> VenueTrade:
    return VenueTrade(
        venue_trade_id=str(trade_id),
        venue_order_id=f'vo-{trade_id}',
        client_order_id=f'ord-{trade_id}',
        symbol=_SYMBOL,
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal('50000'),
        fee=Decimal('0.001'),
        fee_asset='USDT',
        is_maker=True,
        timestamp=_TS,
    )


class _FakeAdapter:
    def __init__(self, trade_ids: list[int]) -> None:
        self._ids = sorted(trade_ids)
        self.calls: list[int | None] = []

    async def query_trades(
        self,
        account_id: str,
        symbol: str,
        *,
        from_id: int | None = None,
        start_time: object | None = None,
        end_time: object | None = None,
        limit: int | None = None,
    ) -> list[VenueTrade]:
        del account_id, symbol, start_time, end_time
        self.calls.append(from_id)
        ids = self._ids if from_id is None else [i for i in self._ids if i >= from_id]
        if limit is not None:
            ids = ids[:limit]

        return [_trade(i) for i in ids]


@pytest.mark.asyncio
async def test_single_short_page_drains_fully() -> None:
    adapter = _FakeAdapter([1, 2, 3])

    trades, complete = await paginate_my_trades(
        adapter, _ACCT, _SYMBOL, from_id=1, page_limit=10,
    )

    assert [int(t.venue_trade_id) for t in trades] == [1, 2, 3]
    assert complete is True
    assert adapter.calls == [1]


@pytest.mark.asyncio
async def test_paginates_full_pages_advancing_cursor() -> None:
    adapter = _FakeAdapter([1, 2, 3, 4, 5])

    trades, complete = await paginate_my_trades(
        adapter, _ACCT, _SYMBOL, from_id=1, page_limit=2,
    )

    assert [int(t.venue_trade_id) for t in trades] == [1, 2, 3, 4, 5]
    assert complete is True
    assert adapter.calls == [1, 3, 5]


@pytest.mark.asyncio
async def test_inclusive_first_cursor() -> None:
    adapter = _FakeAdapter([3, 5, 7])

    trades, complete = await paginate_my_trades(
        adapter, _ACCT, _SYMBOL, from_id=5, page_limit=10,
    )

    assert [int(t.venue_trade_id) for t in trades] == [5, 7]
    assert complete is True
    assert adapter.calls == [5]


@pytest.mark.asyncio
async def test_empty_stream_is_complete() -> None:
    adapter = _FakeAdapter([])

    trades, complete = await paginate_my_trades(
        adapter, _ACCT, _SYMBOL, from_id=1, page_limit=2,
    )

    assert trades == []
    assert complete is True
    assert adapter.calls == [1]


@pytest.mark.asyncio
async def test_page_cap_truncates_incomplete() -> None:
    adapter = _FakeAdapter([1, 2, 3, 4, 5, 6])

    trades, complete = await paginate_my_trades(
        adapter, _ACCT, _SYMBOL, from_id=1, page_limit=2, max_pages=2,
    )

    assert [int(t.venue_trade_id) for t in trades] == [1, 2, 3, 4]
    assert complete is False
    assert adapter.calls == [1, 3]
