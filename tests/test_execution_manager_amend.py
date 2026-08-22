'''
Tests for TradeModify order-price amend of a resting single order
(WP-Praxis-0009, 5.8* + 8.6* single-order): cancel-query-place with
command-total fill aggregation across the superseded and replacement
orders.
'''

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
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
    TradeStatus,
)
from praxis.core.domain.events import FillReceived
from praxis.core.domain.iceberg_modify import IcebergModify
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.trade_modify import TradeModify
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.twap_modify import TwapModify
from praxis.core.domain.twap_params import TwapParams
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    CancelResult,
    OrderBookLevel,
    OrderBookSnapshot,
    SubmitResult,
    SymbolFilters,
    VenueAdapter,
    VenueOrder,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_OLD_PRICE = Decimal('50000')
_NEW_PRICE = Decimal('49000')
_PRICE_KW = 'price'
_QTY_ARG_INDEX = 4


def _iceberg_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.LIMIT,
        'execution_mode': ExecutionMode.ICEBERG,
        'execution_params': IcebergParams(
            display_qty=Decimal('0.1'), limit_price=_OLD_PRICE,
        ),
        'timeout': 3600,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


def _venue_order(
    filled: Decimal, status: OrderStatus = OrderStatus.CANCELED,
) -> VenueOrder:
    return VenueOrder(
        venue_order_id='v-ice',
        client_order_id='old-coid',
        status=status,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        qty=Decimal('1'),
        filled_qty=filled,
        price=_OLD_PRICE,
    )


@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='v-new', status=OrderStatus.OPEN, immediate_fills=(),
    )
    mock.cancel_order.return_value = CancelResult(
        venue_order_id='v-ice', status=OrderStatus.CANCELED,
    )
    mock.query_order.return_value = _venue_order(Decimal('0'))
    mock.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('2')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('2')),),
        last_update_id=1,
    )
    mock.cached_filters.return_value = SymbolFilters(
        symbol='BTCUSDT',
        tick_size=Decimal('0.01'),
        lot_step=Decimal('0.001'),
        lot_min=Decimal('0.001'),
        lot_max=Decimal('100'),
        min_notional=Decimal('10'),
    )
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine,
    adapter: AsyncMock,
) -> AsyncGenerator[tuple[ExecutionManager, list[TradeOutcome]], None]:
    outcomes: list[TradeOutcome] = []

    async def _capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    em = ExecutionManager(
        event_spine=spine,
        epoch_id=_EPOCH,
        venue_adapter=adapter,
        on_trade_outcome=_capture,
        clock=lambda: _T0,
    )
    yield em, outcomes
    for account_id in list(em._accounts):
        await em.unregister_account(account_id)


def _ws_fill(command_id: str, client_order_id: str, qty: Decimal, price: Decimal) -> FillReceived:
    return FillReceived(
        account_id=_ACCT,
        timestamp=_T0,
        client_order_id=client_order_id,
        venue_order_id='v',
        venue_trade_id=f't-{client_order_id}-{qty}',
        trade_id=_TRADE,
        command_id=command_id,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        price=price,
        fee=Decimal('0'),
        fee_asset='USDT',
        is_maker=True,
    )


def _modify(command_id: str, **params: Any) -> TradeModify:
    return TradeModify(
        command_id=command_id,
        account_id=_ACCT,
        reason='reprice',
        modify_params=IcebergModify(**params),
        created_at=_T0,
    )


async def _rest_iceberg(em: ExecutionManager, adapter: AsyncMock) -> str:
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_iceberg_kwargs())
    adapter.query_order.return_value = _venue_order(Decimal('0'))
    await asyncio.sleep(0.3)
    adapter.submit_order.reset_mock()
    return command_id


class TestZeroFillAmend:

    @pytest.mark.asyncio
    async def test_reprice_cancels_old_and_replaces_full_qty(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)

        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        assert adapter.cancel_order.await_count == 1
        assert adapter.query_order.await_count == 1

        call = adapter.submit_order.call_args
        assert call.args[_QTY_ARG_INDEX] == Decimal('1')
        assert call.kwargs[_PRICE_KW] == _NEW_PRICE

        new_coid = generate_client_order_id(ExecutionMode.ICEBERG, command_id, sequence=1)
        assert em._accounts[_ACCT].command_to_order[command_id] == new_coid


class TestPartialFillAggregation:

    @pytest.mark.asyncio
    async def test_reprice_after_partial_aggregates_to_filled(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, outcomes = mgr
        command_id = await _rest_iceberg(em, adapter)
        old_coid = generate_client_order_id(ExecutionMode.ICEBERG, command_id, sequence=0)

        em.enqueue_ws_event(_ACCT, _ws_fill(command_id, old_coid, Decimal('0.3'), _OLD_PRICE))
        await asyncio.sleep(0.2)
        assert outcomes[-1].status is TradeStatus.PARTIAL

        adapter.query_order.return_value = _venue_order(Decimal('0.3'))
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        assert adapter.submit_order.call_args.args[_QTY_ARG_INDEX] == Decimal('0.7')

        new_coid = generate_client_order_id(ExecutionMode.ICEBERG, command_id, sequence=1)
        em.enqueue_ws_event(_ACCT, _ws_fill(command_id, new_coid, Decimal('0.7'), _NEW_PRICE))
        await asyncio.sleep(0.3)

        assert outcomes[-1].status is TradeStatus.FILLED
        assert outcomes[-1].filled_qty == Decimal('1')


class TestOverOrderSafety:

    @pytest.mark.asyncio
    async def test_venue_authoritative_filled_bounds_replacement(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)

        adapter.query_order.return_value = _venue_order(Decimal('0.4'))
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        assert adapter.submit_order.call_args.args[_QTY_ARG_INDEX] == Decimal('0.6')


class TestFullyFilledDuringAmend:

    @pytest.mark.asyncio
    async def test_venue_full_fill_places_no_replacement(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, outcomes = mgr
        command_id = await _rest_iceberg(em, adapter)
        old_coid = generate_client_order_id(ExecutionMode.ICEBERG, command_id, sequence=0)

        em.enqueue_ws_event(_ACCT, _ws_fill(command_id, old_coid, Decimal('0.3'), _OLD_PRICE))
        await asyncio.sleep(0.2)

        adapter.query_order.return_value = _venue_order(
            Decimal('1'), status=OrderStatus.FILLED,
        )
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        adapter.submit_order.assert_not_awaited()
        adapter.cancel_order.assert_awaited()

        em.enqueue_ws_event(_ACCT, _ws_fill(command_id, old_coid, Decimal('0.7'), _OLD_PRICE))
        await asyncio.sleep(0.3)

        assert outcomes[-1].status is TradeStatus.FILLED
        assert outcomes[-1].filled_qty == Decimal('1')


class TestDustRemainder:

    @pytest.mark.asyncio
    async def test_dust_remainder_terminalizes_filled(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, outcomes = mgr
        command_id = await _rest_iceberg(em, adapter)
        old_coid = generate_client_order_id(ExecutionMode.ICEBERG, command_id, sequence=0)

        em.enqueue_ws_event(
            _ACCT, _ws_fill(command_id, old_coid, Decimal('0.9995'), _OLD_PRICE),
        )
        await asyncio.sleep(0.2)

        adapter.query_order.return_value = _venue_order(Decimal('0.9995'))
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        adapter.submit_order.assert_not_awaited()
        assert outcomes[-1].status is TradeStatus.FILLED
        assert outcomes[-1].filled_qty == Decimal('0.9995')
        assert command_id in em._terminal_commands


class TestUnsupportedMode:

    @pytest.mark.asyncio
    async def test_scheme_mode_amend_is_rejected_without_cancel(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(
            **_iceberg_kwargs(
                order_type=OrderType.MARKET,
                execution_mode=ExecutionMode.TWAP,
                execution_params=TwapParams(num_slices=4, interval_seconds=10),
            ),
        )
        await asyncio.sleep(0.3)

        em.submit_modify(
            TradeModify(
                command_id=command_id,
                account_id=_ACCT,
                reason='reprice',
                modify_params=TwapModify(interval_seconds=30),
                created_at=_T0,
            ),
        )
        await asyncio.sleep(0.3)

        adapter.cancel_order.assert_not_awaited()


class TestFailClosed:

    @pytest.mark.asyncio
    async def test_cancel_error_aborts_without_replacement(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        from praxis.infrastructure.venue_adapter import VenueError

        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)
        old_coid = generate_client_order_id(ExecutionMode.ICEBERG, command_id, sequence=0)

        adapter.cancel_order.side_effect = VenueError('venue 5xx')
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        adapter.submit_order.assert_not_awaited()
        assert em._accounts[_ACCT].command_to_order[command_id] == old_coid

    @pytest.mark.asyncio
    async def test_query_error_aborts_without_replacement(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        from praxis.infrastructure.venue_adapter import VenueError

        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)

        adapter.query_order.side_effect = VenueError('venue 5xx')
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        adapter.submit_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_order_still_live_aborts_without_replacement(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)

        adapter.query_order.return_value = _venue_order(
            Decimal('0'), status=OrderStatus.OPEN,
        )
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        adapter.submit_order.assert_not_awaited()


class TestSingleShotAmend:

    @pytest.mark.asyncio
    async def test_single_shot_price_amend_replaces(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        from praxis.core.domain.single_shot_modify import SingleShotModify
        from praxis.core.domain.single_shot_params import SingleShotParams

        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(
            **_iceberg_kwargs(
                execution_mode=ExecutionMode.SINGLE_SHOT,
                execution_params=SingleShotParams(price=_OLD_PRICE),
            ),
        )
        adapter.query_order.return_value = _venue_order(Decimal('0'))
        await asyncio.sleep(0.3)
        adapter.submit_order.reset_mock()

        em.submit_modify(
            TradeModify(
                command_id=command_id,
                account_id=_ACCT,
                reason='reprice',
                modify_params=SingleShotModify(price=_NEW_PRICE),
                created_at=_T0,
            ),
        )
        await asyncio.sleep(0.3)

        assert adapter.submit_order.call_args.kwargs[_PRICE_KW] == _NEW_PRICE
        assert adapter.submit_order.call_args.kwargs.get('iceberg_qty') is None

    @pytest.mark.asyncio
    async def test_stop_field_amend_rejected(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        from praxis.core.domain.single_shot_modify import SingleShotModify
        from praxis.core.domain.single_shot_params import SingleShotParams

        em, _ = mgr
        em.register_account(_ACCT)
        command_id = await em.submit_command(
            **_iceberg_kwargs(
                execution_mode=ExecutionMode.SINGLE_SHOT,
                execution_params=SingleShotParams(price=_OLD_PRICE),
            ),
        )
        await asyncio.sleep(0.3)

        em.submit_modify(
            TradeModify(
                command_id=command_id,
                account_id=_ACCT,
                reason='reprice',
                modify_params=SingleShotModify(stop_price=Decimal('48000')),
                created_at=_T0,
            ),
        )
        await asyncio.sleep(0.3)

        adapter.cancel_order.assert_not_awaited()


class TestSequentialAmendCompose:

    @pytest.mark.asyncio
    async def test_display_amend_keeps_prior_price_amend(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)

        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        adapter.submit_order.reset_mock()
        em.submit_modify(_modify(command_id, display_qty=Decimal('0.2')))
        await asyncio.sleep(0.3)

        call = adapter.submit_order.call_args
        assert call.kwargs[_PRICE_KW] == _NEW_PRICE

    @pytest.mark.asyncio
    async def test_second_amend_retains_superseded_order_fills(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)

        old_coid = generate_client_order_id(
            ExecutionMode.ICEBERG, command_id, sequence=0,
        )
        em.enqueue_ws_event(
            _ACCT, _ws_fill(command_id, old_coid, Decimal('0.3'), _OLD_PRICE),
        )
        await asyncio.sleep(0.2)

        adapter.query_order.return_value = _venue_order(Decimal('0.3'))
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        new_coid = generate_client_order_id(
            ExecutionMode.ICEBERG, command_id, sequence=1,
        )
        em.enqueue_ws_event(
            _ACCT, _ws_fill(command_id, new_coid, Decimal('0.2'), _NEW_PRICE),
        )
        await asyncio.sleep(0.2)

        adapter.submit_order.reset_mock()
        adapter.query_order.return_value = _venue_order(Decimal('0.2'))
        em.submit_modify(_modify(command_id, limit_price=Decimal('48000')))
        await asyncio.sleep(0.3)

        call = adapter.submit_order.call_args
        assert call.args[_QTY_ARG_INDEX] == Decimal('0.5')


class TestModifiableExcludesClosedOrder:

    @pytest.mark.asyncio
    async def test_rejected_amend_replacement_not_modifiable(
        self, mgr: tuple[ExecutionManager, list[TradeOutcome]], adapter: AsyncMock,
    ) -> None:
        from praxis.infrastructure.venue_adapter import VenueError

        em, _ = mgr
        command_id = await _rest_iceberg(em, adapter)
        assert command_id in em.modifiable_command_ids(_ACCT)

        adapter.submit_order.side_effect = VenueError('venue 5xx')
        em.submit_modify(_modify(command_id, limit_price=_NEW_PRICE))
        await asyncio.sleep(0.3)

        assert command_id not in em.modifiable_command_ids(_ACCT)
