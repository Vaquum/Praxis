'''Tests for Trading fund-transaction reconciliation (WP-Praxis-0009).'''

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock

import pytest

from praxis.core.domain.events import FundTransaction
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    VenueAdapter,
    VenueError,
    VenueFundTransaction,
)
from praxis.trading import Trading
from praxis.trading_config import TradingConfig

_ACCT = 'acc-1'
_TS = datetime(2023, 11, 14, 22, 14, tzinfo=UTC)


def _vft(
    fid: str,
    *,
    asset: str = 'USDT',
    direction: str = 'DEPOSIT',
    ts: datetime = _TS,
) -> VenueFundTransaction:
    return VenueFundTransaction(
        fund_transaction_id=fid, asset=asset, amount=Decimal('100'),
        direction=direction, timestamp=ts,
    )


def _trading(spine: EventSpine, adapter: AsyncMock) -> Trading:
    trading = Trading(
        config=TradingConfig(epoch_id=1),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )
    trading.execution_manager.register_account(_ACCT)
    return trading


async def _funds_on_spine(spine: EventSpine) -> list[FundTransaction]:
    events = await spine.read(epoch_id=1)
    return [event for _seq, event in events if isinstance(event, FundTransaction)]


@pytest.mark.asyncio
async def test_appends_usdt_fund_transactions(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_fund_transactions.return_value = [
        _vft('dep-1'), _vft('wd-1', direction='WITHDRAWAL'),
    ]
    trading = _trading(spine, adapter)

    await trading._reconcile_fund_transactions(_ACCT)

    funds = await _funds_on_spine(spine)
    assert {f.fund_transaction_id for f in funds} == {'dep-1', 'wd-1'}


@pytest.mark.asyncio
async def test_filters_non_quote_asset(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_fund_transactions.return_value = [_vft('btc-dep', asset='BTC')]
    trading = _trading(spine, adapter)

    await trading._reconcile_fund_transactions(_ACCT)

    assert await _funds_on_spine(spine) == []


@pytest.mark.asyncio
async def test_dedup_second_poll_does_not_reappend(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_fund_transactions.return_value = [_vft('dep-1')]
    trading = _trading(spine, adapter)

    await trading._reconcile_fund_transactions(_ACCT)
    await trading._reconcile_fund_transactions(_ACCT)

    assert len(await _funds_on_spine(spine)) == 1


@pytest.mark.asyncio
async def test_cursor_advances_to_latest_timestamp(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_fund_transactions.return_value = [_vft('dep-1', ts=_TS)]
    trading = _trading(spine, adapter)

    await trading._reconcile_fund_transactions(_ACCT)

    assert trading._fund_reconcile_cursor[_ACCT] == _TS


@pytest.mark.asyncio
async def test_venue_error_is_swallowed(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_fund_transactions.side_effect = VenueError('boom')
    trading = _trading(spine, adapter)

    await trading._reconcile_fund_transactions(_ACCT)

    assert await _funds_on_spine(spine) == []


@pytest.mark.asyncio
async def test_reconciliation_loop_polls_ready_accounts(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_fund_transactions.return_value = [_vft('dep-1')]
    trading = Trading(
        config=TradingConfig(epoch_id=1, reconcile_interval_seconds=0.01),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )
    trading.execution_manager.register_account(_ACCT)
    trading._ready_accounts.add(_ACCT)

    task = asyncio.create_task(trading._reconciliation_loop())
    await asyncio.sleep(0.05)
    trading._stopping = True
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    funds = await _funds_on_spine(spine)
    assert any(fund.fund_transaction_id == 'dep-1' for fund in funds)
