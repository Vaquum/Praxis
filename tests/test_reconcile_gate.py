'''
Tests for the reconnect submission gate, projection fail-stop, and the
Trading reconnect reconcile flow (2.16c).
'''

from __future__ import annotations

import asyncio
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
)
from praxis.core.domain.events import CommandAccepted, OrderSubmitIntent
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import ChainVerificationError, EventSpine
from praxis.infrastructure.secret_store import Credentials
from praxis.infrastructure.venue_adapter import (
    OrderBookLevel,
    OrderBookSnapshot,
    SubmitResult,
    VenueAdapter,
    VenueError,
)
from praxis.trading import Trading
from praxis.trading_config import TradingConfig

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_EPOCH = 1
_CMD_KWARGS: dict[str, Any] = {
    'trade_id': 'trade-1',
    'account_id': _ACCT,
    'symbol': 'BTCUSDT',
    'side': OrderSide.BUY,
    'qty': Decimal('1'),
    'order_type': OrderType.LIMIT,
    'execution_mode': ExecutionMode.SINGLE_SHOT,
    'execution_params': SingleShotParams(price=Decimal('50000')),
    'timeout': 60,
    'reference_price': None,
    'maker_preference': MakerPreference.NO_PREFERENCE,
    'stp_mode': STPMode.NONE,
    'created_at': _TS,
}


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.OPEN,
        immediate_fills=(),
    )
    mock.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('2')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('2')),),
        last_update_id=1,
    )
    return mock


def _has(events: list[tuple[int, Any]], kind: type) -> bool:
    return any(isinstance(event, kind) for _seq, event in events)


@pytest.mark.asyncio
async def test_reconciling_gate_blocks_then_releases_command(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    mgr = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    mgr.register_account(_ACCT)
    mgr.set_reconciling(_ACCT, True)

    assert mgr.is_order_capable(_ACCT) is False

    await mgr.submit_command(**_CMD_KWARGS)
    await asyncio.sleep(0.3)

    events = await spine.read(_EPOCH, after_seq=0)
    assert _has(events, CommandAccepted)
    assert not _has(events, OrderSubmitIntent)

    mgr.set_reconciling(_ACCT, False)
    assert mgr.is_order_capable(_ACCT) is True
    await asyncio.sleep(0.3)

    events = await spine.read(_EPOCH, after_seq=0)
    assert _has(events, OrderSubmitIntent)

    await mgr.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_projection_failure_poisons_and_blocks_commands(
    spine: EventSpine,
    adapter: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mgr = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    mgr.register_account(_ACCT)

    def _boom(runtime: Any, event: Any) -> None:
        del runtime, event
        raise RuntimeError('projection boom')

    monkeypatch.setattr(mgr, '_project', _boom)

    mgr.enqueue_ws_event(
        _ACCT,
        CommandAccepted(account_id=_ACCT, timestamp=_TS, command_id='cmd-1', trade_id='trade-1'),
    )
    await asyncio.sleep(0.3)

    assert mgr.is_order_capable(_ACCT) is False

    await mgr.submit_command(**_CMD_KWARGS)
    await asyncio.sleep(0.3)

    events = await spine.read(_EPOCH, after_seq=0)
    assert not _has(events, OrderSubmitIntent)

    await mgr.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_poisoned_account_stops_projecting_further_events(
    spine: EventSpine,
    adapter: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mgr = ExecutionManager(event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter)
    mgr.register_account(_ACCT)

    project_calls = 0

    def _boom(runtime: Any, event: Any) -> None:
        nonlocal project_calls
        del runtime, event
        project_calls += 1
        raise RuntimeError('projection boom')

    monkeypatch.setattr(mgr, '_project', _boom)

    for n in range(3):
        mgr.enqueue_ws_event(
            _ACCT,
            CommandAccepted(
                account_id=_ACCT, timestamp=_TS, command_id=f'cmd-{n}', trade_id=f'trade-{n}',
            ),
        )
    await asyncio.sleep(0.3)

    assert mgr.is_order_capable(_ACCT) is False
    assert project_calls == 1

    await mgr.unregister_account(_ACCT)


def _trading(spine: EventSpine) -> Trading:
    config = TradingConfig(
        epoch_id=_EPOCH,
        account_credentials={_ACCT: Credentials(api_key='k', api_secret='s')},
    )
    return Trading(config=config, event_spine=spine, venue_adapter=MagicMock())


@pytest.mark.asyncio
async def test_start_fails_closed_on_broken_chain(spine: EventSpine) -> None:
    await spine.append(CommandAccepted(account_id=_ACCT, timestamp=_TS, command_id='c1', trade_id='t1'), _EPOCH)
    await spine.append(CommandAccepted(account_id=_ACCT, timestamp=_TS, command_id='c2', trade_id='t2'), _EPOCH)
    await spine._conn.execute('UPDATE events SET payload = ? WHERE event_seq = 2', (b'{}',))
    await spine._conn.commit()

    trading = _trading(spine)

    with pytest.raises(ChainVerificationError):
        await trading.start()

    assert trading._started is False
    assert trading._execution_manager.is_order_capable(_ACCT) is False


@pytest.mark.asyncio
async def test_reconcile_on_reconnect_gates_then_releases(spine: EventSpine) -> None:
    trading = _trading(spine)
    trading._execution_manager = MagicMock()
    trading._backfill_account = AsyncMock(return_value=True)
    trading._reconcile_account = AsyncMock()

    await trading._reconcile_on_reconnect(_ACCT)

    calls = [call.args for call in trading._execution_manager.set_reconciling.call_args_list]
    assert (_ACCT, True) in calls
    assert calls[-1] == (_ACCT, False)
    trading._backfill_account.assert_awaited_once_with(_ACCT)
    trading._reconcile_account.assert_awaited_once_with(_ACCT)


@pytest.mark.asyncio
async def test_reconcile_on_reconnect_reruns_when_reentered(spine: EventSpine) -> None:
    trading = _trading(spine)
    trading._execution_manager = MagicMock()
    trading._reconcile_account = AsyncMock()
    calls = 0

    async def _backfill(account_id: str) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            await trading._reconcile_on_reconnect(account_id)
        return True

    trading._backfill_account = _backfill

    await trading._reconcile_on_reconnect(_ACCT)

    assert calls == 2
    assert _ACCT not in trading._reconciling_accounts
    assert _ACCT not in trading._reconcile_rerun_pending

    gate_calls = [call.args for call in trading._execution_manager.set_reconciling.call_args_list]
    assert gate_calls.count((_ACCT, False)) == 1
    assert gate_calls[-1] == (_ACCT, False)


@pytest.mark.asyncio
async def test_reconcile_on_reconnect_stays_gated_on_incomplete_backfill(spine: EventSpine) -> None:
    trading = _trading(spine)
    trading._execution_manager = MagicMock()
    trading._backfill_account = AsyncMock(return_value=False)
    trading._reconcile_account = AsyncMock()

    await trading._reconcile_on_reconnect(_ACCT)

    calls = [call.args for call in trading._execution_manager.set_reconciling.call_args_list]
    assert (_ACCT, True) in calls
    assert (_ACCT, False) not in calls
    assert _ACCT not in trading._reconciling_accounts


@pytest.mark.asyncio
async def test_reconcile_clears_pending_on_venue_failure(spine: EventSpine) -> None:
    trading = _trading(spine)
    trading._execution_manager = MagicMock()
    trading._reconcile_account = AsyncMock()

    async def _backfill(account_id: str) -> bool:
        await trading._reconcile_on_reconnect(account_id)
        raise VenueError('boom')

    trading._backfill_account = _backfill

    await trading._reconcile_on_reconnect(_ACCT)

    assert _ACCT not in trading._reconcile_rerun_pending
    assert _ACCT not in trading._reconciling_accounts


@pytest.mark.asyncio
async def test_reconcile_clears_pending_on_incomplete_backfill(spine: EventSpine) -> None:
    trading = _trading(spine)
    trading._execution_manager = MagicMock()
    trading._reconcile_account = AsyncMock()

    async def _backfill(account_id: str) -> bool:
        await trading._reconcile_on_reconnect(account_id)
        return False

    trading._backfill_account = _backfill

    await trading._reconcile_on_reconnect(_ACCT)

    assert _ACCT not in trading._reconcile_rerun_pending
    assert _ACCT not in trading._reconciling_accounts
    calls = [call.args for call in trading._execution_manager.set_reconciling.call_args_list]
    assert (_ACCT, False) not in calls


@pytest.mark.asyncio
async def test_reconcile_on_reconnect_stays_gated_on_venue_failure(spine: EventSpine) -> None:
    trading = _trading(spine)
    trading._execution_manager = MagicMock()
    trading._backfill_account = AsyncMock(side_effect=VenueError('boom'))
    trading._reconcile_account = AsyncMock()

    await trading._reconcile_on_reconnect(_ACCT)

    calls = [call.args for call in trading._execution_manager.set_reconciling.call_args_list]
    assert (_ACCT, True) in calls
    assert (_ACCT, False) not in calls
    assert _ACCT not in trading._reconciling_accounts
