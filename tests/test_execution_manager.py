'''
Tests for praxis.core.execution_manager.ExecutionManager.
'''

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from collections.abc import AsyncGenerator
from typing import Any

import aiosqlite
import pytest
import pytest_asyncio

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.events import CommandAccepted
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.execution_manager import AccountNotRegisteredError, ExecutionManager
from praxis.infrastructure.event_spine import EventSpine

_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
_ACCT = 'acc-1'
_ACCT2 = 'acc-2'
_TRADE = 'trade-1'
_EPOCH = 1

_CMD_KWARGS: dict[str, Any] = {
    'trade_id': _TRADE,
    'account_id': _ACCT,
    'symbol': 'BTCUSDT',
    'side': OrderSide.BUY,
    'qty': Decimal('1'),
    'order_type': OrderType.LIMIT,
    'execution_mode': ExecutionMode.SINGLE_SHOT,
    'execution_params': SingleShotParams(price=Decimal('50000')),
    'timeout': 300,
    'reference_price': None,
    'maker_preference': MakerPreference.NO_PREFERENCE,
    'stp_mode': STPMode.NONE,
    'created_at': _TS,
}


@pytest_asyncio.fixture
async def spine() -> AsyncGenerator[EventSpine, None]:
    conn = await aiosqlite.connect(':memory:')
    es = EventSpine(conn)
    await es.ensure_schema()
    yield es
    await conn.close()


@pytest_asyncio.fixture
async def mgr(spine: EventSpine) -> AsyncGenerator[ExecutionManager, None]:
    em = ExecutionManager(event_spine=spine, epoch_id=_EPOCH)
    yield em
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


class TestRegisterAccount:
    @pytest.mark.asyncio
    async def test_register_starts_task(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        runtime = mgr._accounts[_ACCT]
        assert runtime.task is not None
        assert not runtime.task.done()

    @pytest.mark.asyncio
    async def test_register_empty_account_id_raises(
        self, mgr: ExecutionManager
    ) -> None:
        with pytest.raises(ValueError, match='non-empty'):
            mgr.register_account('')

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        with pytest.raises(ValueError, match='already registered'):
            mgr.register_account(_ACCT)


class TestUnregisterAccount:
    @pytest.mark.asyncio
    async def test_unregister_cancels_task(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        task = mgr._accounts[_ACCT].task
        await mgr.unregister_account(_ACCT)
        assert _ACCT not in mgr._accounts
        assert task is not None
        assert task.done()

    @pytest.mark.asyncio
    async def test_unregister_unknown_raises(self, mgr: ExecutionManager) -> None:
        with pytest.raises(AccountNotRegisteredError, match='not registered'):
            await mgr.unregister_account('unknown')


class TestSubmitCommand:
    @pytest.mark.asyncio
    async def test_returns_uuid(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        uuid.UUID(command_id)

    @pytest.mark.asyncio
    async def test_unregistered_account_raises(self, mgr: ExecutionManager) -> None:
        with pytest.raises(AccountNotRegisteredError, match='not registered'):
            await mgr.submit_command(**_CMD_KWARGS)

    @pytest.mark.asyncio
    async def test_appends_command_accepted_to_spine(
        self,
        mgr: ExecutionManager,
        spine: EventSpine,
    ) -> None:
        mgr.register_account(_ACCT)
        command_id = await mgr.submit_command(**_CMD_KWARGS)
        events = await spine.read(_EPOCH, after_seq=0)
        assert len(events) == 1
        _seq, event = events[0]
        assert isinstance(event, CommandAccepted)
        assert event.command_id == command_id
        assert event.trade_id == _TRADE

    @pytest.mark.asyncio
    async def test_enqueues_to_command_queue(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        await mgr.submit_command(**_CMD_KWARGS)
        runtime = mgr._accounts[_ACCT]
        assert runtime.command_queue.qsize() >= 1


class TestSubmitAbort:
    @pytest.mark.asyncio
    async def test_enqueues_to_priority_queue(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        abort = TradeAbort(
            command_id='cmd-1',
            account_id=_ACCT,
            reason='test',
            created_at=_TS,
        )
        mgr.submit_abort(abort)
        assert mgr._accounts[_ACCT].priority_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_unregistered_account_raises(self, mgr: ExecutionManager) -> None:
        abort = TradeAbort(
            command_id='cmd-1',
            account_id='unknown',
            reason='test',
            created_at=_TS,
        )
        with pytest.raises(AccountNotRegisteredError, match='not registered'):
            mgr.submit_abort(abort)


class TestAccountLoop:
    @pytest.mark.asyncio
    async def test_priority_drained_before_command(
        self,
        mgr: ExecutionManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.INFO):
            mgr.register_account(_ACCT)
            runtime = mgr._accounts[_ACCT]

            abort = TradeAbort(
                command_id='cmd-abort',
                account_id=_ACCT,
                reason='test',
                created_at=_TS,
            )
            runtime.priority_queue.put_nowait(abort)

            await mgr.submit_command(**_CMD_KWARGS)

            await asyncio.sleep(0.3)

        messages = [r.message for r in caplog.records]
        abort_idx = next(
            (i for i, m in enumerate(messages) if 'abort received' in m),
            None,
        )
        cmd_idx = next(
            (i for i, m in enumerate(messages) if 'command dequeued' in m),
            None,
        )
        assert abort_idx is not None
        assert cmd_idx is not None
        assert abort_idx < cmd_idx


class TestIsolation:
    @pytest.mark.asyncio
    async def test_independent_queues(self, mgr: ExecutionManager) -> None:
        mgr.register_account(_ACCT)
        mgr.register_account(_ACCT2)

        kwargs2 = {**_CMD_KWARGS, 'account_id': _ACCT2}
        await mgr.submit_command(**_CMD_KWARGS)
        await mgr.submit_command(**kwargs2)

        rt1 = mgr._accounts[_ACCT]
        rt2 = mgr._accounts[_ACCT2]
        assert rt1.command_queue is not rt2.command_queue
