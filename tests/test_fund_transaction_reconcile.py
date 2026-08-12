'''Tests for Trading fund-transaction reconciliation (WP-Praxis-0009).'''

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock

import pytest

from praxis.core.account_ledger import AccountLedger
from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import (
    FillReceived,
    FundTransaction,
    ReconciliationMismatch,
    RegisterAccount,
)
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    BalanceEntry,
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


async def _mismatches_on_spine(spine: EventSpine) -> list[ReconciliationMismatch]:
    events = await spine.read(epoch_id=1)
    return [event for _seq, event in events if isinstance(event, ReconciliationMismatch)]


def _ledger(trading: Trading) -> AccountLedger:
    ledger = trading.execution_manager._accounts[_ACCT].account_ledger
    ledger.apply(RegisterAccount(account_id=_ACCT, timestamp=_TS))

    return ledger


def _seed_usdt(trading: Trading, amount: Decimal) -> None:
    _ledger(trading).apply(FundTransaction(
        account_id=_ACCT, timestamp=_TS, fund_transaction_id='seed',
        amount=amount, direction='DEPOSIT',
    ))


def _seed_btc(trading: Trading, qty: Decimal) -> None:
    _ledger(trading).apply(FillReceived(
        account_id=_ACCT, timestamp=_TS, client_order_id='SS-seed',
        venue_order_id='v-seed', venue_trade_id='vt-seed',
        trade_id='trade-seed', command_id='cmd-seed',
        symbol='BTCUSDT', side=OrderSide.BUY, qty=qty, price=Decimal('50000'),
        fee=Decimal('0'), fee_asset='USDT', is_maker=True,
    ))


@pytest.mark.asyncio
async def test_balance_shortfall_emits_reconciliation_mismatch(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('0'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('100'))

    await trading._reconcile_balances(_ACCT)

    mismatches = await _mismatches_on_spine(spine)
    assert len(mismatches) == 1
    assert mismatches[0].asset == 'USDT'
    assert mismatches[0].expected == Decimal('100')
    assert mismatches[0].actual == Decimal('0')


@pytest.mark.asyncio
async def test_balance_excess_is_ignored_as_untracked(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('100'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)

    await trading._reconcile_balances(_ACCT)

    assert await _mismatches_on_spine(spine) == []


@pytest.mark.asyncio
async def test_balance_within_tolerance_no_mismatch(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('99.996'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('100'))

    await trading._reconcile_balances(_ACCT)

    assert await _mismatches_on_spine(spine) == []


@pytest.mark.asyncio
async def test_balance_uses_free_plus_locked(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('30'), locked=Decimal('60')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('100'))

    await trading._reconcile_balances(_ACCT)

    mismatches = await _mismatches_on_spine(spine)
    assert mismatches[0].actual == Decimal('90')


@pytest.mark.asyncio
async def test_balance_shortfall_suppressed_when_unchanged(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('0'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('100'))

    await trading._reconcile_balances(_ACCT)
    await trading._reconcile_balances(_ACCT)

    assert len(await _mismatches_on_spine(spine)) == 1


@pytest.mark.asyncio
async def test_balance_venue_error_swallowed(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.side_effect = VenueError('boom')
    trading = _trading(spine, adapter)

    await trading._reconcile_balances(_ACCT)

    assert await _mismatches_on_spine(spine) == []


@pytest.mark.asyncio
async def test_balance_btc_shortfall(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='BTC', free=Decimal('0.5'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_btc(trading, Decimal('1'))

    await trading._reconcile_balances(_ACCT)

    mismatches = await _mismatches_on_spine(spine)
    assert [(m.asset, m.expected, m.actual) for m in mismatches] == [
        ('BTC', Decimal('1'), Decimal('0.5')),
    ]


@pytest.mark.asyncio
async def test_balance_skipped_while_projection_pending(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('0'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('100'))
    trading.execution_manager.enqueue_ws_event(
        _ACCT,
        FundTransaction(
            account_id=_ACCT, timestamp=_TS, fund_transaction_id='dep-1',
            amount=Decimal('100'), direction='DEPOSIT',
        ),
    )

    await trading._reconcile_balances(_ACCT)

    assert await _mismatches_on_spine(spine) == []


@pytest.mark.asyncio
async def test_balance_shortfall_retried_after_failed_append(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('0'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('100'))

    real_append = trading._event_spine.append
    calls = {'n': 0}

    async def _flaky_append(event: object, epoch_id: int) -> int | None:
        calls['n'] += 1
        if calls['n'] == 1:
            raise RuntimeError('spine down')
        return await real_append(event, epoch_id)  # type: ignore[arg-type]

    trading._event_spine.append = _flaky_append  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await trading._reconcile_balances(_ACCT)

    await trading._reconcile_balances(_ACCT)

    assert len(await _mismatches_on_spine(spine)) == 1


@pytest.mark.asyncio
async def test_balance_mismatch_reemits_on_delta_change(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('100'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('200'))

    await trading._reconcile_balances(_ACCT)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('50'), locked=Decimal('0')),
    ]
    await trading._reconcile_balances(_ACCT)

    assert len(await _mismatches_on_spine(spine)) == 2


@pytest.mark.asyncio
async def test_balance_mismatch_clears_then_reappears(spine: EventSpine) -> None:
    adapter = AsyncMock(spec=VenueAdapter)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('0'), locked=Decimal('0')),
    ]
    trading = _trading(spine, adapter)
    _seed_usdt(trading, Decimal('100'))

    await trading._reconcile_balances(_ACCT)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('100'), locked=Decimal('0')),
    ]
    await trading._reconcile_balances(_ACCT)
    adapter.query_balance.return_value = [
        BalanceEntry(asset='USDT', free=Decimal('0'), locked=Decimal('0')),
    ]
    await trading._reconcile_balances(_ACCT)

    assert len(await _mismatches_on_spine(spine)) == 2


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
