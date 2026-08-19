'''
Tests for TradeModify scheme-plan amend (WP-Praxis-0009, 8.6*): re-planning
a running TWAP / Time DCA / Scheduled VWAP scheme's remaining slices and
cadence in place, no venue cancel-replace.
'''

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
)
from praxis.core.domain.scheduled_vwap_modify import ScheduledVwapModify
from praxis.core.domain.scheduled_vwap_params import ScheduledVwapParams
from praxis.core.domain.trade_modify import TradeModify
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.twap_modify import TwapModify
from praxis.core.domain.twap_params import TwapParams
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    ImmediateFill,
    SubmitResult,
    VenueAdapter,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_PRICE = Decimal('50000')
_BIG_STEP = timedelta(seconds=60)
_QTY_ARG_INDEX = 4


def _twap_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.TWAP,
        'execution_params': TwapParams(num_slices=4, interval_seconds=10),
        'timeout': 3600,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


def _fill_echo(*args: Any, client_order_id: str | None = None, **_kwargs: Any) -> SubmitResult:
    qty = args[_QTY_ARG_INDEX]

    return SubmitResult(
        venue_order_id=f'v-{client_order_id}',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id=f't-{client_order_id}',
                qty=qty,
                price=_PRICE,
                fee=Decimal('0'),
                fee_asset='USDT',
                is_maker=False,
            ),
        ),
    )


@pytest.fixture
def clock_holder() -> list[datetime]:
    return [_T0]


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.side_effect = _fill_echo
    mock.cached_filters.return_value = None
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine,
    adapter: AsyncMock,
    clock_holder: list[datetime],
) -> AsyncGenerator[tuple[ExecutionManager, list[TradeOutcome]], None]:
    outcomes: list[TradeOutcome] = []

    async def _capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    em = ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=_capture,
        clock=lambda: clock_holder[0],
    )
    yield em, outcomes
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


def _modify(command_id: str, params: Any) -> TradeModify:
    return TradeModify(
        command_id=command_id,
        account_id=_ACCT,
        reason='reschedule',
        modify_params=params,
        created_at=_T0,
    )


async def _advance(clock_holder: list[datetime]) -> None:
    clock_holder[0] = clock_holder[0] + _BIG_STEP
    await asyncio.sleep(0.3)


class TestTwapSchemeAmend:

    @pytest.mark.asyncio
    async def test_interval_amend_reschedules(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)

        em.submit_modify(_modify(command_id, TwapModify(interval_seconds=30)))
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[command_id]
        assert scheme.interval_seconds == 30

    @pytest.mark.asyncio
    async def test_num_slices_increase_replans_remaining(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[command_id]
        cursor = scheme.cursor

        em.submit_modify(_modify(command_id, TwapModify(num_slices=6)))
        await asyncio.sleep(0.3)

        assert scheme.slices_total == 6
        remaining = scheme.slice_qtys[cursor:]
        assert len(remaining) == 6 - cursor
        assert sum(remaining) == Decimal('1') - sum(scheme.slice_qtys[:cursor])

    @pytest.mark.asyncio
    async def test_reduce_at_or_below_cursor_rejected(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
        clock_holder: list[datetime],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)
        await _advance(clock_holder)

        scheme = em._accounts[_ACCT].schemes[command_id]
        assert scheme.cursor >= 2
        before = list(scheme.slice_qtys)

        em.submit_modify(_modify(command_id, TwapModify(num_slices=2)))
        await asyncio.sleep(0.3)

        assert scheme.slices_total == 4
        assert scheme.slice_qtys == before
        assert command_id in em._accounts[_ACCT].schemes


class TestVwapSchemeAmend:

    @pytest.mark.asyncio
    async def test_interval_amend_reschedules(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(
            **_twap_kwargs(
                execution_mode=ExecutionMode.SCHEDULED_VWAP,
                execution_params=ScheduledVwapParams(
                    interval_seconds=10,
                    volume_weights=(Decimal('0.5'), Decimal('0.3'), Decimal('0.2')),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        em.submit_modify(_modify(command_id, ScheduledVwapModify(interval_seconds=25)))
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[command_id]
        assert scheme.interval_seconds == 25

    @pytest.mark.asyncio
    async def test_weight_amend_rejected_leaves_scheme_unchanged(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(
            **_twap_kwargs(
                execution_mode=ExecutionMode.SCHEDULED_VWAP,
                execution_params=ScheduledVwapParams(
                    interval_seconds=10,
                    volume_weights=(Decimal('0.5'), Decimal('0.3'), Decimal('0.2')),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[command_id]
        before = list(scheme.slice_qtys)

        em.submit_modify(
            _modify(
                command_id,
                ScheduledVwapModify(
                    volume_weights=(Decimal('0.4'), Decimal('0.4'), Decimal('0.2')),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        assert scheme.slice_qtys == before


class TestFrozenResumeAndComposition:

    @pytest.mark.asyncio
    async def test_amend_resumes_a_frozen_scheme(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
        clock_holder: list[datetime],
    ) -> None:
        from praxis.infrastructure.venue_adapter import VenueError

        em, _ = mgr
        em.register_account(_ACCT)

        calls = {'n': 0}

        def _fail_first(*args: Any, client_order_id: str | None = None, **kw: Any) -> SubmitResult:
            calls['n'] += 1
            if calls['n'] == 1:
                raise VenueError('slice rejected')
            return _fill_echo(*args, client_order_id=client_order_id, **kw)

        adapter.submit_order.side_effect = _fail_first

        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[command_id]
        assert scheme.frozen is True
        submits_before = adapter.submit_order.call_count

        em.submit_modify(_modify(command_id, TwapModify(interval_seconds=5)))
        await asyncio.sleep(0.3)
        assert scheme.frozen is False

        await _advance(clock_holder)
        assert adapter.submit_order.call_count > submits_before

    @pytest.mark.asyncio
    async def test_amend_does_not_resume_a_protection_frozen_scheme(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
        clock_holder: list[datetime],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)

        runtime = em._accounts[_ACCT]
        await em._freeze_account_schemes(runtime, 'protection lost')
        scheme = runtime.schemes[command_id]
        assert scheme.protection_frozen is True
        submits_before = adapter.submit_order.call_count

        em.submit_modify(_modify(command_id, TwapModify(interval_seconds=30)))
        await asyncio.sleep(0.3)

        assert scheme.frozen is True
        assert scheme.protection_frozen is True
        assert scheme.next_run_at is None
        assert scheme.interval_seconds != 30

        await _advance(clock_holder)
        assert adapter.submit_order.call_count == submits_before

    @pytest.mark.asyncio
    async def test_protection_freeze_survives_replay_and_still_rejects_amend(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], spine: EventSpine,
        adapter: AsyncMock, clock_holder: list[datetime],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)

        await em._freeze_account_schemes(em._accounts[_ACCT], 'protection lost')
        events = await spine.read(_EPOCH, after_seq=0)
        await em.unregister_account(_ACCT)

        restarted = ExecutionManager(
            event_spine=spine,
            epoch_id=_EPOCH,
            venue_adapter=adapter,
            on_trade_outcome=None,
            clock=lambda: clock_holder[0],
        )
        restarted.register_account(_ACCT)
        restarted.replay_events(_ACCT, events)

        resumed = restarted._accounts[_ACCT].schemes[command_id]
        assert resumed.protection_frozen is True

        restarted.submit_modify(_modify(command_id, TwapModify(interval_seconds=30)))
        await asyncio.sleep(0.3)

        assert resumed.frozen is True
        assert resumed.interval_seconds != 30

        await restarted.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_slice_failure_frozen_scheme_is_upgraded_and_rejects_amend(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        from praxis.infrastructure.venue_adapter import VenueError

        em, _ = mgr
        em.register_account(_ACCT)

        calls = {'n': 0}

        def _fail_first(*args: Any, client_order_id: str | None = None, **kw: Any) -> SubmitResult:
            calls['n'] += 1
            if calls['n'] == 1:
                raise VenueError('slice rejected')
            return _fill_echo(*args, client_order_id=client_order_id, **kw)

        adapter.submit_order.side_effect = _fail_first

        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)

        runtime = em._accounts[_ACCT]
        scheme = runtime.schemes[command_id]
        assert scheme.frozen is True
        assert scheme.protection_frozen is False

        frozen = await em._freeze_account_schemes(runtime, 'protection lost')

        assert frozen == [command_id]
        assert scheme.protection_frozen is True

        em.submit_modify(_modify(command_id, TwapModify(interval_seconds=5)))
        await asyncio.sleep(0.3)

        assert scheme.frozen is True
        assert scheme.protection_frozen is True
        assert scheme.interval_seconds != 5

    @pytest.mark.asyncio
    async def test_sequential_partial_amends_compose(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(**_twap_kwargs())
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[command_id]

        em.submit_modify(_modify(command_id, TwapModify(interval_seconds=30)))
        await asyncio.sleep(0.3)
        assert scheme.interval_seconds == 30

        em.submit_modify(_modify(command_id, TwapModify(num_slices=6)))
        await asyncio.sleep(0.3)

        assert scheme.interval_seconds == 30
        assert scheme.slices_total == 6


class TestTimeDcaSchemeAmend:

    @pytest.mark.asyncio
    async def test_num_iterations_increase_replans_remaining(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]],
    ) -> None:
        from praxis.core.domain.time_dca_modify import TimeDcaModify
        from praxis.core.domain.time_dca_params import TimeDcaParams

        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(
            **_twap_kwargs(
                execution_mode=ExecutionMode.TIME_DCA,
                execution_params=TimeDcaParams(num_iterations=4, interval_seconds=10),
            ),
        )
        await asyncio.sleep(0.3)

        scheme = em._accounts[_ACCT].schemes[command_id]
        cursor = scheme.cursor

        em.submit_modify(_modify(command_id, TimeDcaModify(num_iterations=6, interval_seconds=20)))
        await asyncio.sleep(0.3)

        assert scheme.slices_total == 6
        assert scheme.interval_seconds == 20
        remaining = scheme.slice_qtys[cursor:]
        assert len(remaining) == 6 - cursor
        assert sum(remaining) == Decimal('1') - sum(scheme.slice_qtys[:cursor])
