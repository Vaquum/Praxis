'''
Tests for the Bracket execution mode in ExecutionManager (WP-Praxis-0007
item 6.3, P1): a MARKET entry, then a protective OCO placed on the filled
entry with take-profit/stop-loss legs from absolute prices or bps offsets.
'''

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import asyncio

import pytest
import pytest_asyncio

from praxis.core.domain.bracket_params import BracketParams
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
    TradeStatus,
)
from praxis.core.bracket_exit_command_id import bracket_exit_command_id
from praxis.core.domain.events import FillReceived
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import ExecutionManager
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    ImmediateFill,
    OrderSubmitTimeoutError,
    SubmitResult,
    SymbolFilters,
    TransientError,
    VenueAdapter,
    VenueOrderList,
    VenueOrderListLeg,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_ENTRY_PRICE = Decimal('50000')
_ORDER_TYPE_ARG_INDEX = 3
_QTY_ARG_INDEX = 4
_SIDE_ARG_INDEX = 2


def _bracket_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'trade_id': _TRADE,
        'account_id': _ACCT,
        'symbol': 'BTCUSDT',
        'side': OrderSide.BUY,
        'qty': Decimal('1'),
        'order_type': OrderType.MARKET,
        'execution_mode': ExecutionMode.BRACKET,
        'execution_params': BracketParams(
            take_profit_price=Decimal('55000'),
            stop_loss_price=Decimal('48000'),
        ),
        'timeout': 3600,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


def _filters(tick_size: Decimal) -> SymbolFilters:
    return SymbolFilters(
        symbol='BTCUSDT',
        tick_size=tick_size,
        lot_step=Decimal('0.00001'),
        lot_min=Decimal('0.00001'),
        lot_max=Decimal('100'),
        min_notional=Decimal('10'),
    )


def _make_adapter(
    *,
    entry_fills: bool = True,
    entry_error: Exception | None = None,
    oco_error: Exception | None = None,
    oco_fills: bool = False,
    filters: SymbolFilters | None = None,
) -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    calls: list[dict[str, Any]] = []

    def _submit(*args: Any, **kwargs: Any) -> SubmitResult:
        order_type = args[_ORDER_TYPE_ARG_INDEX]
        calls.append({'args': args, 'kwargs': kwargs})

        if order_type is OrderType.OCO:
            if oco_error is not None:
                raise oco_error

            oco_immediate = (
                (
                    ImmediateFill(
                        venue_trade_id='t-oco',
                        qty=args[_QTY_ARG_INDEX],
                        price=kwargs['price'],
                        fee=Decimal('0'),
                        fee_asset='USDT',
                        is_maker=False,
                    ),
                )
                if oco_fills
                else ()
            )

            return SubmitResult(
                venue_order_id='ol-1',
                status=OrderStatus.FILLED if oco_fills else OrderStatus.OPEN,
                immediate_fills=oco_immediate,
                leg_client_order_ids=('leg-tp', 'leg-sl'),
            )

        if entry_error is not None:
            raise entry_error

        qty = args[_QTY_ARG_INDEX]
        fills = (
            (
                ImmediateFill(
                    venue_trade_id='t-entry',
                    qty=qty,
                    price=_ENTRY_PRICE,
                    fee=Decimal('0'),
                    fee_asset='USDT',
                    is_maker=False,
                ),
            )
            if entry_fills
            else ()
        )

        return SubmitResult(
            venue_order_id='v-entry',
            status=OrderStatus.FILLED if entry_fills else OrderStatus.OPEN,
            immediate_fills=fills,
        )

    mock.submit_order.side_effect = _submit
    mock.cached_filters.return_value = filters
    mock.submit_calls = calls
    return mock


@pytest_asyncio.fixture
async def mgr_factory(
    spine: EventSpine,
) -> AsyncGenerator[Any, None]:
    created: list[ExecutionManager] = []

    def _make(adapter: AsyncMock) -> tuple[ExecutionManager, list[TradeOutcome]]:
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
        created.append(em)
        return em, outcomes

    yield _make
    for em in created:
        for account_id in list(em._accounts):
            await em.unregister_account(account_id)


def _oco_call(adapter: AsyncMock) -> dict[str, Any]:
    return next(
        call
        for call in adapter.submit_calls
        if call['args'][_ORDER_TYPE_ARG_INDEX] is OrderType.OCO
    )


class TestBracketEntryAndProtection:

    @pytest.mark.asyncio
    async def test_filled_entry_places_protective_oco_and_reports_entry(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        command_id = await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        assert len(outcomes) == 1
        outcome = outcomes[0]
        assert outcome.status is TradeStatus.FILLED
        assert outcome.command_id == command_id
        assert outcome.filled_qty == Decimal('1')
        assert outcome.avg_fill_price == _ENTRY_PRICE

        oco = _oco_call(adapter)
        assert oco['args'][_SIDE_ARG_INDEX] is OrderSide.SELL
        assert oco['args'][_QTY_ARG_INDEX] == Decimal('1')
        assert oco['kwargs']['price'] == Decimal('55000')
        assert oco['kwargs']['stop_price'] == Decimal('48000')

    @pytest.mark.asyncio
    async def test_short_entry_places_buy_protective_oco(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(
            **_bracket_kwargs(
                side=OrderSide.SELL,
                execution_params=BracketParams(
                    take_profit_price=Decimal('45000'),
                    stop_loss_price=Decimal('52000'),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        oco = _oco_call(adapter)
        assert oco['args'][_SIDE_ARG_INDEX] is OrderSide.BUY
        assert oco['kwargs']['price'] == Decimal('45000')
        assert oco['kwargs']['stop_price'] == Decimal('52000')

    @pytest.mark.asyncio
    async def test_offset_bps_long_places_tp_above_sl_below_snapped(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(filters=_filters(Decimal('10')))
        em, _ = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(
            **_bracket_kwargs(
                execution_params=BracketParams(
                    take_profit_offset_bps=Decimal('200'),
                    stop_loss_offset_bps=Decimal('100'),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        oco = _oco_call(adapter)
        assert oco['kwargs']['price'] == Decimal('51000')
        assert oco['kwargs']['stop_price'] == Decimal('49500')

    @pytest.mark.asyncio
    async def test_offset_bps_short_inverts_direction(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(filters=_filters(Decimal('10')))
        em, _ = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(
            **_bracket_kwargs(
                side=OrderSide.SELL,
                execution_params=BracketParams(
                    take_profit_offset_bps=Decimal('200'),
                    stop_loss_offset_bps=Decimal('100'),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        oco = _oco_call(adapter)
        assert oco['kwargs']['price'] == Decimal('49000')
        assert oco['kwargs']['stop_price'] == Decimal('50500')

    @pytest.mark.asyncio
    async def test_protective_oco_carries_deterministic_exit_command_id(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        em.register_account(_ACCT)

        command_id = await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        exit_command_id = bracket_exit_command_id(command_id)
        oco_client_order_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1,
        )
        order = em.get_trading_state(_ACCT).orders[oco_client_order_id]
        assert order.command_id == exit_command_id


class TestBracketDegenerate:

    @pytest.mark.asyncio
    async def test_entry_submit_failure_rejects_without_protection(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(entry_error=TransientError('venue 5xx'))
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        assert outcomes[0].status is TradeStatus.REJECTED
        assert not any(
            call['args'][_ORDER_TYPE_ARG_INDEX] is OrderType.OCO
            for call in adapter.submit_calls
        )

    @pytest.mark.asyncio
    async def test_unfilled_entry_is_pending_without_protection(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(entry_fills=False)
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        assert outcomes[0].status is TradeStatus.PENDING
        assert outcomes[0].filled_qty == Decimal('0')
        assert not any(
            call['args'][_ORDER_TYPE_ARG_INDEX] is OrderType.OCO
            for call in adapter.submit_calls
        )

    @pytest.mark.asyncio
    async def test_protective_oco_failure_still_reports_filled_entry(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(oco_error=TransientError('oco 5xx'))
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        assert outcomes[0].status is TradeStatus.FILLED
        assert outcomes[0].filled_qty == Decimal('1')


def _fill(
    *,
    client_order_id: str,
    command_id: str,
    side: OrderSide,
    qty: Decimal,
    price: Decimal,
    venue_trade_id: str,
    venue_order_id: str,
) -> FillReceived:
    return FillReceived(
        account_id=_ACCT,
        timestamp=_T0,
        client_order_id=client_order_id,
        venue_order_id=venue_order_id,
        venue_trade_id=venue_trade_id,
        trade_id=_TRADE,
        command_id=command_id,
        symbol='BTCUSDT',
        side=side,
        qty=qty,
        price=price,
        fee=Decimal('0'),
        fee_asset='USDT',
        is_maker=False,
    )


class TestBracketLifecycle:

    @pytest.mark.asyncio
    async def test_protective_leg_fill_emits_exit_outcome(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        command_id = await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        exit_command_id = bracket_exit_command_id(command_id)
        oco_client_order_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1,
        )
        em.enqueue_ws_event(
            _ACCT,
            _fill(
                client_order_id=oco_client_order_id,
                command_id=exit_command_id,
                side=OrderSide.SELL,
                qty=Decimal('1'),
                price=Decimal('55000'),
                venue_trade_id='t-exit',
                venue_order_id='ol-1',
            ),
        )
        await asyncio.sleep(0.3)

        exit_outcomes = [o for o in outcomes if o.command_id == exit_command_id]
        assert len(exit_outcomes) == 1
        assert exit_outcomes[0].status is TradeStatus.FILLED
        assert exit_outcomes[0].filled_qty == Decimal('1')
        assert exit_outcomes[0].trade_id == _TRADE

    @pytest.mark.asyncio
    async def test_async_entry_fill_places_protection(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(entry_fills=False)
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        command_id = await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        assert not any(
            call['args'][_ORDER_TYPE_ARG_INDEX] is OrderType.OCO
            for call in adapter.submit_calls
        )
        assert outcomes[-1].status is TradeStatus.PENDING

        entry_client_order_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=0,
        )
        em.enqueue_ws_event(
            _ACCT,
            _fill(
                client_order_id=entry_client_order_id,
                command_id=command_id,
                side=OrderSide.BUY,
                qty=Decimal('1'),
                price=_ENTRY_PRICE,
                venue_trade_id='t-entry-ws',
                venue_order_id='v-entry',
            ),
        )
        await asyncio.sleep(0.3)

        oco = _oco_call(adapter)
        assert oco['args'][_SIDE_ARG_INDEX] is OrderSide.SELL
        assert oco['args'][_QTY_ARG_INDEX] == Decimal('1')

        entry_outcomes = [o for o in outcomes if o.command_id == command_id]
        assert entry_outcomes[-1].status is TradeStatus.FILLED

    @pytest.mark.asyncio
    async def test_protective_oco_timeout_is_rescued(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(
            oco_error=OrderSubmitTimeoutError('timeout', client_order_id='x'),
        )
        adapter.query_order_list.return_value = VenueOrderList(
            order_list_id='ol-1',
            list_client_order_id='x',
            list_status_type='EXEC_STARTED',
            list_order_status='EXECUTING',
            legs=(
                VenueOrderListLeg(venue_order_id='v-a', client_order_id='leg-a', symbol='BTCUSDT'),
                VenueOrderListLeg(venue_order_id='v-b', client_order_id='leg-b', symbol='BTCUSDT'),
            ),
        )
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        command_id = await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        assert outcomes[0].status is TradeStatus.FILLED
        assert bracket_exit_command_id(command_id) in em._commands
        adapter.query_order_list.assert_awaited()

    @pytest.mark.asyncio
    async def test_stop_loss_limit_price_propagates(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(
            **_bracket_kwargs(
                execution_params=BracketParams(
                    take_profit_price=Decimal('55000'),
                    stop_loss_price=Decimal('48000'),
                    stop_loss_limit_price=Decimal('47900'),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        oco = _oco_call(adapter)
        assert oco['kwargs']['stop_limit_price'] == Decimal('47900')

    @pytest.mark.asyncio
    async def test_immediately_filled_protective_oco_emits_exit_outcome(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(oco_fills=True)
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        command_id = await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        exit_command_id = bracket_exit_command_id(command_id)
        exit_outcomes = [o for o in outcomes if o.command_id == exit_command_id]
        assert len(exit_outcomes) == 1
        assert exit_outcomes[0].status is TradeStatus.FILLED
        assert exit_outcomes[0].filled_qty == Decimal('1')

    @pytest.mark.asyncio
    async def test_entry_command_to_order_is_set_for_abort(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(entry_fills=False)
        em, _ = mgr_factory(adapter)
        em.register_account(_ACCT)

        command_id = await em.submit_command(**_bracket_kwargs())
        await asyncio.sleep(0.3)

        entry_client_order_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=0,
        )
        assert (
            em._accounts[_ACCT].command_to_order[command_id]
            == entry_client_order_id
        )


class TestBracketProtectionGuard:

    @pytest.mark.asyncio
    async def test_absolute_tp_on_wrong_side_of_fill_skips_protection(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, outcomes = mgr_factory(adapter)
        em.register_account(_ACCT)

        await em.submit_command(
            **_bracket_kwargs(
                execution_params=BracketParams(
                    take_profit_price=Decimal('49000'),
                    stop_loss_price=Decimal('48000'),
                ),
            ),
        )
        await asyncio.sleep(0.3)

        assert outcomes[0].status is TradeStatus.FILLED
        assert not any(
            call['args'][_ORDER_TYPE_ARG_INDEX] is OrderType.OCO
            for call in adapter.submit_calls
        )


class TestBracketExitCommandId:

    def test_derivation_is_deterministic_and_suffixed(self) -> None:
        assert bracket_exit_command_id('cmd-abc') == 'cmd-abc-x'
