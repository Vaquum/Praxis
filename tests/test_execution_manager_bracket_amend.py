'''
Tests for the bracket protective-OCO amend (WP-Praxis-0009 deferred, bracket
OCO amend sub-item 3): the happy-path cancel-then-replace that drives the
durable Protection* state machine on a live bracket.

The bracket entry command is terminal once its entry fills, but its protective
OCO stays amendable: `modifiable_command_ids` re-admits the entry id while the
protection is ACTIVE (and drops the exit `-x` id), and `validate_trade_modify`
resolves the terminal entry to its live bracket, so a strategy `MODIFY` reaches
`submit_modify` and enqueues. The execution tests drive `_process_modify`
directly; the public-path tests drive `submit_modify` end to end.
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

from nexus.core.domain.bracket_protection_failure_response import (
    BracketProtectionFailureResponse,
)

from praxis.core.domain.bracket_modify import BracketModify
from praxis.core.domain.bracket_params import BracketParams
from praxis.core.domain.enums import (
    BracketProtectionStatus,
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
)
from praxis.core.domain.events import (
    Event,
    OrderCanceled,
    OrderSubmitIntent,
    OrderSubmitted,
    ProtectionActive,
    ProtectionAmendRequested,
    ProtectionCancelConfirmed,
    ProtectionFailed,
    ProtectionReplaceSubmitted,
    ProtectionStateUnknown,
    ProtectionRemediationDelivered,
    FlattenInitiated,
    SchemeFrozen,
    SchemeInitialized,
)
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.domain.twap_params import TwapParams
from praxis.core.domain.trade_modify import TradeModify
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.bracket_exit_command_id import bracket_exit_command_id
from praxis.core.execution_manager import ExecutionManager, _LiveScheme
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    BalanceEntry,
    CancelResult,
    DuplicateClientOrderIdError,
    ImmediateFill,
    NotFoundError,
    VenueTrade,
    SubmitResult,
    SymbolFilters,
    TransientError,
    VenueAdapter,
    VenueOrder,
    VenueOrderList,
    VenueOrderListLeg,
)

_T0 = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1
_ENTRY_PRICE = Decimal('50000')
_TP_PRICE = Decimal('55000')
_SL_PRICE = Decimal('48000')
_NEW_TP_PRICE = Decimal('56000')
_SIDE_ARG_INDEX = 2
_ORDER_TYPE_ARG_INDEX = 3
_QTY_ARG_INDEX = 4
_LEG_TP = 'leg-tp'
_LEG_SL = 'leg-sl'


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
            take_profit_price=_TP_PRICE,
            stop_loss_price=_SL_PRICE,
        ),
        'timeout': 3600,
        'reference_price': None,
        'maker_preference': MakerPreference.NO_PREFERENCE,
        'stp_mode': STPMode.NONE,
        'created_at': _T0,
    }
    kwargs.update(overrides)
    return kwargs


def _filters() -> SymbolFilters:
    return SymbolFilters(
        symbol='BTCUSDT',
        tick_size=Decimal('0.01'),
        lot_step=Decimal('0.00001'),
        lot_min=Decimal('0.00001'),
        lot_max=Decimal('100'),
        min_notional=Decimal('10'),
        base_asset='BTC',
    )


def _make_adapter(
    *,
    replacement_error: Exception | None = None,
    cancel_error: Exception | None = None,
    reconcile_error: Exception | None = None,
    replacement_query_error: Exception | None = None,
    leg_filled: dict[str, Decimal] | None = None,
    new_list_status: str | None = None,
) -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    submit_calls: list[dict[str, Any]] = []
    oco_count = {'n': 0}
    qlist_count = {'n': 0}
    filled = leg_filled or {}

    def _submit(*args: Any, **kwargs: Any) -> SubmitResult:
        order_type = args[_ORDER_TYPE_ARG_INDEX]
        submit_calls.append({'args': args, 'kwargs': kwargs})

        if order_type is OrderType.OCO:
            oco_count['n'] += 1

            if oco_count['n'] >= 2 and replacement_error is not None:
                raise replacement_error

            return SubmitResult(
                venue_order_id=f'ol-{oco_count["n"]}',
                status=OrderStatus.OPEN,
                immediate_fills=(),
                leg_client_order_ids=(_LEG_TP, _LEG_SL),
            )

        return SubmitResult(
            venue_order_id='v-entry',
            status=OrderStatus.FILLED,
            immediate_fills=(
                ImmediateFill(
                    venue_trade_id='t-entry',
                    qty=args[_QTY_ARG_INDEX],
                    price=_ENTRY_PRICE,
                    fee=Decimal('0'),
                    fee_asset='USDT',
                    is_maker=False,
                ),
            ),
        )

    def _query_order_list(*_args: Any, **kwargs: Any) -> VenueOrderList:
        qlist_count['n'] += 1

        if reconcile_error is not None:
            raise reconcile_error

        if replacement_query_error is not None and qlist_count['n'] >= 2:
            raise replacement_query_error

        return VenueOrderList(
            order_list_id='ol-q',
            list_client_order_id=kwargs['list_client_order_id'],
            list_status_type='EXEC_STARTED',
            list_order_status=new_list_status or 'EXECUTING',
            legs=(
                VenueOrderListLeg(
                    venue_order_id='v-tp', client_order_id=_LEG_TP, symbol='BTCUSDT',
                ),
                VenueOrderListLeg(
                    venue_order_id='v-sl', client_order_id=_LEG_SL, symbol='BTCUSDT',
                ),
            ),
        )

    def _query_order(*_args: Any, **kwargs: Any) -> VenueOrder:
        client_order_id = kwargs['client_order_id']
        return VenueOrder(
            venue_order_id=f'v-{client_order_id}',
            client_order_id=client_order_id,
            status=OrderStatus.CANCELED,
            symbol='BTCUSDT',
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            qty=Decimal('1'),
            filled_qty=filled.get(client_order_id, Decimal('0')),
            price=_TP_PRICE,
        )

    mock.submit_order.side_effect = _submit
    mock.cancel_order_list.side_effect = cancel_error
    if cancel_error is None:
        mock.cancel_order_list.side_effect = None
        mock.cancel_order_list.return_value = CancelResult(
            venue_order_id='ol-1', status=OrderStatus.CANCELED,
        )
    mock.query_order_list.side_effect = _query_order_list
    mock.query_order.side_effect = _query_order
    mock.cached_filters.return_value = _filters()
    mock.query_trades.return_value = []
    mock.submit_calls = submit_calls
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


async def _protected_bracket(
    em: ExecutionManager, **overrides: Any,
) -> str:
    em.register_account(_ACCT)
    command_id = await em.submit_command(**_bracket_kwargs(**overrides))
    await asyncio.sleep(0.3)
    return command_id


def _modify(command_id: str, **params: Any) -> TradeModify:
    return TradeModify(
        command_id=command_id,
        account_id=_ACCT,
        reason='amend protection',
        modify_params=BracketModify(**params),
        created_at=_T0,
    )


async def _truncate_after_flatten(
    spine: EventSpine,
) -> list[tuple[int, Any]]:
    '''Return events up to and including FlattenInitiated (crash before submit).'''

    rows = await spine.read(epoch_id=_EPOCH)
    truncated: list[tuple[int, Any]] = []
    for seq, event in rows:
        truncated.append((seq, event))
        if isinstance(event, FlattenInitiated):
            break

    return truncated


async def _truncate_after_protection_failed(
    spine: EventSpine,
) -> list[tuple[int, Any]]:
    '''Return events up to and including ProtectionFailed (crash before intent).'''

    rows = await spine.read(epoch_id=_EPOCH)
    truncated: list[tuple[int, Any]] = []
    for seq, event in rows:
        truncated.append((seq, event))
        if isinstance(event, ProtectionFailed):
            break

    return truncated


def _twap_scheme_init(command_id: str) -> SchemeInitialized:
    return SchemeInitialized(
        account_id=_ACCT, timestamp=_T0, command_id=command_id,
        trade_id='twap-trade', execution_mode=ExecutionMode.TWAP,
        symbol='BTCUSDT', side=OrderSide.BUY, total_qty=Decimal('1'),
        slices_total=4, interval_seconds=10, timeout_seconds=3600,
        volume_weights=(),
    )


def _inject_twap_scheme(runtime: Any, command_id: str) -> None:
    cmd = TradeCommand(
        command_id=command_id, trade_id='twap-trade', account_id=_ACCT,
        symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('1'),
        order_type=OrderType.MARKET, execution_mode=ExecutionMode.TWAP,
        execution_params=TwapParams(num_slices=4, interval_seconds=10),
        timeout=3600, reference_price=None,
        maker_preference=MakerPreference.NO_PREFERENCE, stp_mode=STPMode.NONE,
        created_at=_T0,
    )
    runtime.schemes[command_id] = _LiveScheme(
        command=cmd, slice_qtys=[Decimal('0.25')] * 4, slices_total=4,
        interval_seconds=10, cursor=1, next_run_at=None,
    )


async def _protection_events(spine: EventSpine) -> list[Event]:
    _protection_types = (
        ProtectionAmendRequested,
        ProtectionCancelConfirmed,
        ProtectionReplaceSubmitted,
        ProtectionActive,
        ProtectionStateUnknown,
        ProtectionFailed,
    )
    rows = await spine.read(epoch_id=_EPOCH)
    return [event for _seq, event in rows if isinstance(event, _protection_types)]


async def _order_events(spine: EventSpine) -> list[Event]:
    _order_types = (OrderSubmitIntent, OrderSubmitted, OrderCanceled)
    rows = await spine.read(epoch_id=_EPOCH)
    return [event for _seq, event in rows if isinstance(event, _order_types)]


def _oco_calls(adapter: AsyncMock) -> list[dict[str, Any]]:
    return [
        call
        for call in adapter.submit_calls
        if call['args'][_ORDER_TYPE_ARG_INDEX] is OrderType.OCO
    ]


class TestBracketAmendHappyPath:

    @pytest.mark.asyncio
    async def test_amend_take_profit_cancels_old_replaces_new(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)

        runtime = em._accounts[_ACCT]
        old_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1,
        )
        new_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1, retry=1,
        )

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
            'ProtectionReplaceSubmitted',
            'ProtectionActive',
        ]

        adapter.cancel_order_list.assert_awaited_once()
        assert adapter.cancel_order_list.await_args.kwargs['client_order_id'] == old_list

        replacement = _oco_calls(adapter)[-1]
        assert replacement['kwargs']['client_order_id'] == new_list
        assert replacement['args'][_SIDE_ARG_INDEX] is OrderSide.SELL
        assert replacement['args'][_QTY_ARG_INDEX] == Decimal('1')
        assert replacement['kwargs']['price'] == _NEW_TP_PRICE
        assert replacement['kwargs']['stop_price'] == _SL_PRICE

        bracket = runtime.brackets[command_id]
        assert bracket.protection_client_order_id == new_list
        assert bracket.protection_version == 1
        assert bracket.protection_status is BracketProtectionStatus.ACTIVE
        assert bracket.current_tp_price == _NEW_TP_PRICE
        assert bracket.current_sl_stop_price == _SL_PRICE

    @pytest.mark.asyncio
    async def test_amend_tracks_new_oco_and_terminalizes_old(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)

        runtime = em._accounts[_ACCT]
        old_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1,
        )
        new_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1, retry=1,
        )
        exit_command_id = bracket_exit_command_id(command_id)

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert runtime.command_to_order[exit_command_id] == new_list
        assert new_list in runtime.trading_state.orders
        assert new_list not in runtime.trading_state.closed_orders
        assert old_list not in runtime.trading_state.orders
        assert old_list in runtime.trading_state.closed_orders
        assert runtime.trading_state.closed_orders[old_list].status is OrderStatus.CANCELED

        events = await _order_events(spine)
        order_lifecycle = [
            (type(e).__name__, e.client_order_id)
            for e in events
            if e.client_order_id in (old_list, new_list)
        ]
        assert order_lifecycle == [
            ('OrderSubmitIntent', old_list),
            ('OrderSubmitted', old_list),
            ('OrderCanceled', old_list),
            ('OrderSubmitIntent', new_list),
            ('OrderSubmitted', new_list),
        ]

    @pytest.mark.asyncio
    async def test_amend_survives_replay_repointing_at_new_oco(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        old_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1,
        )
        new_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1, retry=1,
        )
        exit_command_id = bracket_exit_command_id(command_id)

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        rows = await spine.read(epoch_id=_EPOCH)
        resumed, _ = mgr_factory(_make_adapter())
        resumed.register_account(_ACCT)
        resumed.replay_events(_ACCT, rows)

        resumed_runtime = resumed._accounts[_ACCT]
        assert resumed_runtime.command_to_order[exit_command_id] == new_list
        assert new_list in resumed_runtime.trading_state.orders
        assert old_list in resumed_runtime.trading_state.closed_orders

    @pytest.mark.asyncio
    async def test_amend_requested_snapshot_merges_unchanged_stop_loss(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        events = await _protection_events(spine)
        requested = events[0]
        assert isinstance(requested, ProtectionAmendRequested)
        assert requested.take_profit_price == _NEW_TP_PRICE
        assert requested.stop_loss_price == _SL_PRICE
        assert requested.protection_version == 1


def _leg_trade(client_order_id: str, qty: Decimal) -> VenueTrade:
    return VenueTrade(
        venue_trade_id=f'vt-{client_order_id}',
        venue_order_id=f'v-{client_order_id}',
        client_order_id=client_order_id,
        symbol='BTCUSDT',
        side=OrderSide.SELL,
        qty=qty,
        price=_TP_PRICE,
        fee=Decimal('0'),
        fee_asset='USDT',
        is_maker=True,
        timestamp=_T0,
    )


class TestBracketAmendPartialFill:

    @pytest.mark.asyncio
    async def test_partial_protective_fill_shrinks_replacement_qty(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(leg_filled={_LEG_SL: Decimal('0.4')})
        adapter.query_trades.return_value = [_leg_trade(_LEG_SL, Decimal('0.4'))]
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        replacement = _oco_calls(adapter)[-1]
        assert replacement['args'][_QTY_ARG_INDEX] == Decimal('0.6')

    @pytest.mark.asyncio
    async def test_amend_backfills_missed_protective_fill_before_terminalize(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(leg_filled={_LEG_SL: Decimal('0.4')})
        adapter.query_trades.return_value = [_leg_trade(_LEG_SL, Decimal('0.4'))]
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        position = runtime.trading_state.positions.get((_TRADE, _ACCT))
        assert position is not None
        assert position.qty == Decimal('0.6')

    @pytest.mark.asyncio
    async def test_unreconciled_protective_backfill_parks_and_scan_completes(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(leg_filled={_LEG_SL: Decimal('0.4')})
        adapter.query_trades.side_effect = TransientError('myTrades lag')
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        bracket = runtime.brackets[command_id]
        assert bracket.protection_status is BracketProtectionStatus.CANCEL_CONFIRMED
        assert bracket.amend_backfill_since is not None
        assert len(_oco_calls(adapter)) == 1

        adapter.query_trades.side_effect = None
        adapter.query_trades.return_value = [_leg_trade(_LEG_SL, Decimal('0.4'))]
        await em.resolve_held_protection_amends(_ACCT)

        assert bracket.protection_status is BracketProtectionStatus.ACTIVE
        assert bracket.amend_backfill_since is None
        assert len(_oco_calls(adapter)) == 2

    @pytest.mark.asyncio
    async def test_dust_remaining_places_no_replacement_and_drops_bracket(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(leg_filled={_LEG_SL: Decimal('0.9999')})
        adapter.query_trades.return_value = [_leg_trade(_LEG_SL, Decimal('0.9999'))]
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert len(_oco_calls(adapter)) == 1

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
        ]

        assert command_id not in runtime.brackets
        assert command_id not in em.modifiable_command_ids(_ACCT)

    @pytest.mark.asyncio
    async def test_full_protective_fill_places_no_replacement(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(leg_filled={_LEG_SL: Decimal('1')})
        adapter.query_trades.return_value = [_leg_trade(_LEG_SL, Decimal('1'))]
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert len(_oco_calls(adapter)) == 1

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
        ]

        assert command_id not in runtime.brackets
        assert command_id not in em.modifiable_command_ids(_ACCT)


class TestBracketAmendCancelAmbiguous:

    @pytest.mark.asyncio
    async def test_cancel_timeout_halts_at_state_unknown(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(cancel_error=TransientError('venue 5xx'))
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionStateUnknown',
        ]

        assert len(_oco_calls(adapter)) == 1

        bracket = runtime.brackets[command_id]
        assert bracket.protection_status is BracketProtectionStatus.STATE_UNKNOWN


class TestBracketAmendReplaceFails:

    @pytest.mark.asyncio
    async def test_replacement_venue_error_unconfirmable_halts_state_unknown(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'),
            replacement_query_error=TransientError('venue 5xx'),
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
            'ProtectionReplaceSubmitted',
            'ProtectionStateUnknown',
        ]

        bracket = runtime.brackets[command_id]
        assert bracket.protection_status is BracketProtectionStatus.STATE_UNKNOWN

    @pytest.mark.asyncio
    async def test_replacement_confirmed_reject_marks_protection_failed(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'),
            new_list_status='REJECT',
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
            'ProtectionReplaceSubmitted',
            'ProtectionFailed',
        ]

        bracket = runtime.brackets[command_id]
        assert bracket.protection_status is BracketProtectionStatus.FAILED

    @pytest.mark.asyncio
    async def test_flatten_then_halt_market_sells_remainder_on_failure(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'),
            new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert runtime.brackets[command_id].protection_status is BracketProtectionStatus.FAILED

        flatten_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=999,
        )
        rows = await spine.read(epoch_id=_EPOCH)
        flattens = [e for _s, e in rows if isinstance(e, FlattenInitiated)]
        assert len(flattens) == 1
        assert flattens[0].qty == Decimal('1')
        assert flattens[0].client_order_id == flatten_id

        market_sells = [
            c for c in adapter.submit_calls
            if c['args'][3] is OrderType.MARKET
            and c['args'][2] is OrderSide.SELL
            and c['kwargs'].get('client_order_id') == flatten_id
        ]
        assert len(market_sells) == 1
        assert market_sells[0]['args'][4] == Decimal('1')

    @pytest.mark.asyncio
    async def test_flatten_aborts_when_a_protective_leg_is_live(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        adapter.query_order.side_effect = None
        adapter.query_order.return_value = VenueOrder(
            venue_order_id='v-leg', client_order_id='leg', status=OrderStatus.PARTIALLY_FILLED,
            symbol='BTCUSDT', side=OrderSide.SELL, order_type=OrderType.LIMIT,
            qty=Decimal('1'), filled_qty=Decimal('0'), price=Decimal('56000'),
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        rows = await spine.read(epoch_id=_EPOCH)
        assert not any(isinstance(e, FlattenInitiated) for _s, e in rows)
        assert not any(
            c['args'][3] is OrderType.MARKET and c['args'][2] is OrderSide.SELL
            for c in adapter.submit_calls
        )

    @pytest.mark.asyncio
    async def test_flatten_skips_dust_remainder(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('0'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        rows = await spine.read(epoch_id=_EPOCH)
        assert not any(isinstance(e, FlattenInitiated) for _s, e in rows)
        assert not any(
            c['args'][3] is OrderType.MARKET and c['args'][2] is OrderSide.SELL
            for c in adapter.submit_calls
        )

    @pytest.mark.asyncio
    async def test_reduce_only_does_not_flatten_on_failure(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'),
            new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        em._protection_failure_response = (
            lambda _account_id: BracketProtectionFailureResponse.REDUCE_ONLY
        )
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert runtime.brackets[command_id].protection_status is BracketProtectionStatus.FAILED
        rows = await spine.read(epoch_id=_EPOCH)
        assert not any(isinstance(e, FlattenInitiated) for _s, e in rows)

    @pytest.mark.asyncio
    async def test_flatten_recovery_reflattens_when_never_submitted(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        flatten_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=999,
        )
        truncated = await _truncate_after_flatten(spine)
        await em.unregister_account(_ACCT)

        recover_adapter = _make_adapter()
        recover_adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        recover_adapter.query_order.side_effect = NotFoundError('no such order')
        em2, _ = mgr_factory(recover_adapter)
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, truncated)
        await em2.recover_incomplete_flattens(_ACCT, truncated)

        market_sells = [
            c for c in recover_adapter.submit_calls
            if c['args'][3] is OrderType.MARKET
            and c['args'][2] is OrderSide.SELL
            and c['kwargs'].get('client_order_id') == flatten_id
        ]
        assert len(market_sells) == 1
        assert market_sells[0]['args'][4] == Decimal('1')

        await em2.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_boot_reflatten_holds_when_leg_still_live(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        live_leg = VenueOrder(
            venue_order_id='v-leg', client_order_id='leg',
            status=OrderStatus.PARTIALLY_FILLED, symbol='BTCUSDT',
            side=OrderSide.SELL, order_type=OrderType.LIMIT,
            qty=Decimal('1'), filled_qty=Decimal('0'), price=Decimal('56000'),
        )
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        adapter.query_order.side_effect = None
        adapter.query_order.return_value = live_leg
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        rows = await spine.read(epoch_id=_EPOCH)
        protection_failed = next(e for _s, e in rows if isinstance(e, ProtectionFailed))
        assert protection_failed.oco_list_client_order_ids
        assert not any(isinstance(e, FlattenInitiated) for _s, e in rows)

        truncated = await _truncate_after_protection_failed(spine)
        flatten_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=999,
        )
        await em.unregister_account(_ACCT)

        recover_adapter = _make_adapter()
        recover_adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )

        def _query(*_args: Any, client_order_id: str = '', **_kwargs: Any) -> VenueOrder:
            if client_order_id == flatten_id:
                raise NotFoundError('no flatten order')

            return live_leg

        recover_adapter.query_order.side_effect = _query
        em2, _ = mgr_factory(recover_adapter)
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, truncated)
        await em2.recover_incomplete_flattens(_ACCT, truncated)

        assert not any(
            c['args'][3] is OrderType.MARKET for c in recover_adapter.submit_calls
        )

        await em2.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_flatten_recovery_reflattens_when_intent_never_persisted(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        flatten_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=999,
        )
        truncated = await _truncate_after_protection_failed(spine)
        assert not any(isinstance(e, FlattenInitiated) for _s, e in truncated)
        await em.unregister_account(_ACCT)

        recover_adapter = _make_adapter()
        recover_adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        recover_adapter.query_order.side_effect = NotFoundError('no such order')
        em2, _ = mgr_factory(recover_adapter)
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, truncated)
        await em2.recover_incomplete_flattens(_ACCT, truncated)

        market_sells = [
            c for c in recover_adapter.submit_calls
            if c['args'][3] is OrderType.MARKET
            and c['args'][2] is OrderSide.SELL
            and c['kwargs'].get('client_order_id') == flatten_id
        ]
        assert len(market_sells) == 1
        assert market_sells[0]['args'][4] == Decimal('1')

        await em2.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_flatten_recovery_reconciles_venue_fills(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        flatten_id = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=999,
        )
        truncated = await _truncate_after_flatten(spine)
        await em.unregister_account(_ACCT)

        recover_adapter = _make_adapter()
        recover_adapter.query_order.side_effect = None
        recover_adapter.query_order.return_value = VenueOrder(
            venue_order_id='v-flat', client_order_id=flatten_id,
            status=OrderStatus.FILLED, symbol='BTCUSDT', side=OrderSide.SELL,
            order_type=OrderType.MARKET, qty=Decimal('1'), filled_qty=Decimal('1'),
            price=None,
        )
        recover_adapter.query_trades = AsyncMock(return_value=[
            VenueTrade(
                venue_trade_id='t-flat', venue_order_id='v-flat',
                client_order_id=flatten_id, symbol='BTCUSDT', side=OrderSide.SELL,
                qty=Decimal('1'), price=Decimal('49000'), fee=Decimal('0'),
                fee_asset='USDT', is_maker=False, timestamp=_T0,
            ),
        ])
        em2, _ = mgr_factory(recover_adapter)
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, truncated)
        await em2.recover_incomplete_flattens(_ACCT, truncated)

        assert not any(
            c['args'][3] is OrderType.MARKET
            and c['kwargs'].get('client_order_id') == flatten_id
            for c in recover_adapter.submit_calls
        )
        flat_order = em2._scheme_child_order(em2._accounts[_ACCT], flatten_id)
        assert flat_order is not None
        assert flat_order.filled_qty == Decimal('1')

        await em2.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_failed_protection_records_and_drains_remediation(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        delivered: list[Any] = []

        async def _capture(remediation: Any) -> None:
            delivered.append(remediation)

        em.set_on_protection_remediation(_capture)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        assert len(delivered) == 1
        assert delivered[0].command_id == command_id
        assert delivered[0].account_id == _ACCT

        await em.drain_protection_remediations(_ACCT)
        assert len(delivered) == 1

    @pytest.mark.asyncio
    async def test_remediation_delivery_retries_on_failure(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        calls = {'n': 0}

        async def _flaky(_remediation: Any) -> None:
            calls['n'] += 1
            if calls['n'] == 1:
                msg = 'nexus not ready'
                raise RuntimeError(msg)

        em.set_on_protection_remediation(_flaky)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        await em.drain_protection_remediations(_ACCT)
        await em.drain_protection_remediations(_ACCT)

        assert calls['n'] == 2

    @pytest.mark.asyncio
    async def test_seed_protection_remediations_redelivers_after_restart(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )
        events = await spine.read(epoch_id=_EPOCH)
        await em.unregister_account(_ACCT)

        em2, _ = mgr_factory(_make_adapter())
        delivered: list[Any] = []

        async def _capture(remediation: Any) -> None:
            delivered.append(remediation)

        em2.set_on_protection_remediation(_capture)
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, events)
        em2.seed_protection_remediations(events)
        await em2.drain_protection_remediations(_ACCT)

        assert len(delivered) == 1
        assert delivered[0].command_id == command_id

        await em2.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_delivered_remediation_not_redelivered_after_restart(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'), new_list_status='REJECT',
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)

        async def _ok(_remediation: Any) -> None:
            return

        em.set_on_protection_remediation(_ok)
        command_id = await _protected_bracket(em)
        await em._process_modify(
            em._accounts[_ACCT], _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )
        events = await spine.read(epoch_id=_EPOCH)
        assert any(
            isinstance(e, ProtectionRemediationDelivered) for _s, e in events
        )
        await em.unregister_account(_ACCT)

        em2, _ = mgr_factory(_make_adapter())
        delivered: list[Any] = []

        async def _capture(remediation: Any) -> None:
            delivered.append(remediation)

        em2.set_on_protection_remediation(_capture)
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, events)
        em2.seed_protection_remediations(events)
        await em2.drain_protection_remediations(_ACCT)

        assert delivered == []

        await em2.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_protection_failure_freezes_account_schemes(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'),
            new_list_status='REJECT',
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]
        _inject_twap_scheme(runtime, 'twap-1')

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert runtime.brackets[command_id].protection_status is BracketProtectionStatus.FAILED
        assert runtime.schemes['twap-1'].frozen is True
        assert runtime.schemes['twap-1'].protection_frozen is True

        rows = await spine.read(epoch_id=_EPOCH)
        frozen = [(seq, e) for seq, e in rows if isinstance(e, SchemeFrozen)]
        assert len(frozen) == 1
        assert frozen[0][1].command_id == 'twap-1'

        failed_seq = next(seq for seq, e in rows if isinstance(e, ProtectionFailed))
        assert frozen[0][0] < failed_seq

    @pytest.mark.asyncio
    async def test_scheme_freeze_survives_crash_before_failure_record(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        em, _ = mgr_factory(_make_adapter())
        em.register_account(_ACCT)
        runtime = em._accounts[_ACCT]

        await spine.append(_twap_scheme_init('twap-1'), _EPOCH)
        _inject_twap_scheme(runtime, 'twap-1')

        await em._freeze_account_schemes(runtime, 'bracket protection failed')
        await em.unregister_account(_ACCT)

        events = await spine.read(epoch_id=_EPOCH)
        assert any(isinstance(e, SchemeFrozen) for _s, e in events)
        assert not any(isinstance(e, ProtectionFailed) for _s, e in events)

        restarted = ExecutionManager(
            event_spine=spine, epoch_id=_EPOCH, venue_adapter=_make_adapter(),
            on_trade_outcome=None, clock=lambda: _T0,
        )
        restarted.register_account(_ACCT)
        restarted.replay_events(_ACCT, events)

        resumed = restarted._accounts[_ACCT].schemes['twap-1']
        assert resumed.frozen is True
        assert resumed.protection_frozen is True

        await restarted.unregister_account(_ACCT)


class TestBracketProtectionWatchdog:

    @staticmethod
    def _order_list(status: str) -> VenueOrderList:
        return VenueOrderList(
            order_list_id='ol-w', list_client_order_id='list-x',
            list_status_type='EXEC_STARTED', list_order_status=status,
            legs=(
                VenueOrderListLeg(
                    venue_order_id='v-tp', client_order_id=_LEG_TP, symbol='BTCUSDT',
                ),
                VenueOrderListLeg(
                    venue_order_id='v-sl', client_order_id=_LEG_SL, symbol='BTCUSDT',
                ),
            ),
        )

    async def _unknown_bracket(
        self, mgr_factory: Any, leg_filled: dict[str, Any] | None = None,
    ) -> Any:
        adapter = _make_adapter(
            replacement_error=TransientError('venue 5xx'),
            replacement_query_error=TransientError('venue 5xx'),
            leg_filled=leg_filled,
        )
        adapter.query_balance = AsyncMock(
            return_value=[BalanceEntry(asset='BTC', free=Decimal('1'), locked=Decimal('0'))],
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]
        await em._process_modify(
            runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )
        assert (
            runtime.brackets[command_id].protection_status
            is BracketProtectionStatus.STATE_UNKNOWN
        )
        return em, adapter, command_id, runtime

    @pytest.mark.asyncio
    async def test_watchdog_reactivates_when_protection_working(
        self, mgr_factory: Any,
    ) -> None:
        em, adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)

        adapter.query_order_list.side_effect = None
        adapter.query_order_list.return_value = self._order_list('EXECUTING')

        await em.resolve_unknown_protection(_ACCT)

        assert (
            runtime.brackets[command_id].protection_status
            is BracketProtectionStatus.ACTIVE
        )
        assert runtime.brackets[command_id].unknown_since is None

    @pytest.mark.asyncio
    async def test_watchdog_remediates_when_confirmed_naked(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        em, adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)

        adapter.query_order_list.side_effect = None
        adapter.query_order_list.return_value = self._order_list('ALL_DONE')

        await em.resolve_unknown_protection(_ACCT)

        assert (
            runtime.brackets[command_id].protection_status
            is BracketProtectionStatus.FAILED
        )
        rows = await spine.read(epoch_id=_EPOCH)
        assert any(isinstance(e, FlattenInitiated) for _s, e in rows)

    @pytest.mark.asyncio
    async def test_watchdog_closes_bracket_when_protective_leg_filled(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        em, adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)

        adapter.query_order_list.side_effect = None
        adapter.query_order_list.return_value = self._order_list('ALL_DONE')

        def _tp_filled(*_args: Any, **kwargs: Any) -> VenueOrder:
            coid = kwargs['client_order_id']
            leg_filled = coid == _LEG_TP
            return VenueOrder(
                venue_order_id=f'v-{coid}', client_order_id=coid,
                status=OrderStatus.FILLED if leg_filled else OrderStatus.CANCELED,
                symbol='BTCUSDT', side=OrderSide.SELL, order_type=OrderType.LIMIT,
                qty=Decimal('1'),
                filled_qty=Decimal('1') if leg_filled else Decimal('0'),
                price=_TP_PRICE,
            )

        adapter.query_order.side_effect = _tp_filled

        await em.resolve_unknown_protection(_ACCT)

        assert command_id not in runtime.brackets
        rows = await spine.read(epoch_id=_EPOCH)
        assert not any(isinstance(e, FlattenInitiated) for _s, e in rows)
        assert not any(isinstance(e, ProtectionFailed) for _s, e in rows)
        assert not any(isinstance(e, SchemeFrozen) for _s, e in rows)

    @pytest.mark.asyncio
    async def test_watchdog_holds_while_unconfirmable_before_deadline(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        em, _adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)

        runtime.brackets[command_id].unknown_since = _T0

        await em.resolve_unknown_protection(_ACCT)

        assert (
            runtime.brackets[command_id].protection_status
            is BracketProtectionStatus.STATE_UNKNOWN
        )
        rows = await spine.read(epoch_id=_EPOCH)
        assert not any(isinstance(e, FlattenInitiated) for _s, e in rows)

    @pytest.mark.asyncio
    async def test_watchdog_remediates_unconfirmable_past_deadline(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        em, _adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)

        runtime.brackets[command_id].unknown_since = _T0 - timedelta(seconds=400)

        await em.resolve_unknown_protection(_ACCT)

        assert (
            runtime.brackets[command_id].protection_status
            is BracketProtectionStatus.FAILED
        )
        rows = await spine.read(epoch_id=_EPOCH)
        assert any(isinstance(e, ProtectionFailed) for _s, e in rows)

    @pytest.mark.asyncio
    async def test_deadline_flatten_guards_replacement_candidate(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        em, adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)
        bracket = runtime.brackets[command_id]
        pending_id = bracket.pending_replacement_client_order_id
        assert pending_id is not None
        bracket.unknown_since = _T0 - timedelta(seconds=400)

        def _qlist(*_args: Any, list_client_order_id: str = '', **_kwargs: Any) -> VenueOrderList:
            if list_client_order_id == pending_id:
                raise TransientError('venue 5xx')

            return self._order_list('ALL_DONE')

        adapter.query_order_list.side_effect = _qlist
        adapter.query_order.side_effect = None
        adapter.query_order.return_value = VenueOrder(
            venue_order_id='v', client_order_id='leg', status=OrderStatus.CANCELED,
            symbol='BTCUSDT', side=OrderSide.SELL, order_type=OrderType.LIMIT,
            qty=Decimal('1'), filled_qty=Decimal('0'), price=Decimal('56000'),
        )

        await em.resolve_unknown_protection(_ACCT)

        assert bracket.protection_status is BracketProtectionStatus.FAILED
        rows = await spine.read(epoch_id=_EPOCH)
        assert not any(isinstance(e, FlattenInitiated) for _s, e in rows)

    @pytest.mark.asyncio
    async def test_request_protection_scan_runs_on_writer(
        self, mgr_factory: Any,
    ) -> None:
        em, adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)

        adapter.query_order_list.side_effect = None
        adapter.query_order_list.return_value = self._order_list('EXECUTING')

        em.request_protection_scan(_ACCT)
        assert runtime.protection_scan_requested is True

        runtime.protection_scan_requested = False
        await em._run_protection_scan(runtime)

        assert (
            runtime.brackets[command_id].protection_status
            is BracketProtectionStatus.ACTIVE
        )

    @pytest.mark.asyncio
    async def test_unknown_protection_survives_restart(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        em, _adapter, command_id, runtime = await self._unknown_bracket(mgr_factory)
        pre = runtime.brackets[command_id]
        old_list_id = pre.protection_client_order_id
        new_list_id = pre.pending_replacement_client_order_id
        assert old_list_id is not None
        assert new_list_id is not None

        events = await spine.read(epoch_id=_EPOCH)
        await em.unregister_account(_ACCT)

        em2, _ = mgr_factory(_make_adapter())
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, events)

        resumed = em2._accounts[_ACCT].brackets[command_id]
        assert resumed.protection_status is BracketProtectionStatus.STATE_UNKNOWN
        assert resumed.protection_client_order_id == old_list_id
        assert resumed.pending_replacement_client_order_id == new_list_id
        assert resumed.unknown_since == _T0

        await em2.unregister_account(_ACCT)

    @pytest.mark.asyncio
    async def test_resume_rebuilds_bracket_from_amend_requested(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]
        await em._process_modify(
            runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE),
        )

        events = await spine.read(epoch_id=_EPOCH)
        boot: list[tuple[int, Any]] = []
        for seq, event in events:
            boot.append((seq, event))
            if type(event).__name__ == 'ProtectionAmendRequested':
                break

        await em.unregister_account(_ACCT)

        em2, _ = mgr_factory(_make_adapter())
        em2.register_account(_ACCT)
        em2.replay_events(_ACCT, boot)

        resumed = em2._accounts[_ACCT].brackets[command_id]
        assert resumed.protection_status is BracketProtectionStatus.STATE_UNKNOWN
        assert resumed.protection_client_order_id is not None
        assert resumed.pending_replacement_client_order_id is not None

        await em2.unregister_account(_ACCT)


class TestBracketAmendIdempotentPlace:

    @pytest.mark.asyncio
    async def test_duplicate_place_with_live_list_treated_as_success(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(
            replacement_error=DuplicateClientOrderIdError('dup', 'new-list'),
            new_list_status='EXECUTING',
        )
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]
        new_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1, retry=1,
        )
        exit_command_id = bracket_exit_command_id(command_id)

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
            'ProtectionReplaceSubmitted',
            'ProtectionActive',
        ]

        assert len(_oco_calls(adapter)) == 2

        bracket = runtime.brackets[command_id]
        assert bracket.protection_status is BracketProtectionStatus.ACTIVE
        assert runtime.command_to_order[exit_command_id] == new_list
        assert new_list in runtime.trading_state.orders


class TestBracketAmendReconcileFails:

    @pytest.mark.asyncio
    async def test_reconcile_query_failure_halts_without_stale_replacement(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(reconcile_error=TransientError('venue 5xx'))
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
            'ProtectionStateUnknown',
        ]

        assert len(_oco_calls(adapter)) == 1

        bracket = runtime.brackets[command_id]
        assert bracket.protection_status is BracketProtectionStatus.STATE_UNKNOWN


class TestBracketAmendRejectsWhenNotActive:

    @pytest.mark.asyncio
    async def test_amend_rejected_when_amend_already_in_flight(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        bracket = runtime.brackets[command_id]
        bracket.protection_status = BracketProtectionStatus.AMEND_REQUESTED

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        adapter.cancel_order_list.assert_not_awaited()
        assert await _protection_events(spine) == []
        assert len(_oco_calls(adapter)) == 1

    @pytest.mark.asyncio
    async def test_bracket_awaiting_protection_is_not_modifiable(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        bracket = runtime.brackets[command_id]
        bracket.protection_placed = False
        bracket.protection_client_order_id = None

        assert command_id not in em.modifiable_command_ids(_ACCT)

        em.submit_modify(_modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert runtime.priority_queue.empty()


class TestBracketAmendPublicPath:

    @pytest.mark.asyncio
    async def test_submit_modify_enqueues_and_executes_amend_for_filled_bracket(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]
        new_list = generate_client_order_id(
            ExecutionMode.BRACKET, command_id, sequence=1, retry=1,
        )
        exit_command_id = bracket_exit_command_id(command_id)

        assert command_id in em._terminal_commands
        assert (
            runtime.brackets[command_id].protection_status
            is BracketProtectionStatus.ACTIVE
        )
        assert runtime.priority_queue.empty()

        em.submit_modify(_modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert not runtime.priority_queue.empty()

        await asyncio.sleep(0.3)

        assert runtime.priority_queue.empty()

        events = await _protection_events(spine)
        assert [type(e).__name__ for e in events] == [
            'ProtectionAmendRequested',
            'ProtectionCancelConfirmed',
            'ProtectionReplaceSubmitted',
            'ProtectionActive',
        ]
        assert runtime.command_to_order[exit_command_id] == new_list
        assert runtime.brackets[command_id].protection_client_order_id == new_list

    @pytest.mark.asyncio
    async def test_modifiable_command_ids_admits_entry_drops_exit(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)

        modifiable = em.modifiable_command_ids(_ACCT)

        assert command_id in modifiable
        assert bracket_exit_command_id(command_id) not in modifiable

    @pytest.mark.asyncio
    async def test_modifiable_snapshot_matches_live_set(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        await asyncio.sleep(0.1)

        snapshot = em.modifiable_command_ids_snapshot(_ACCT)
        assert snapshot == frozenset(em.modifiable_command_ids(_ACCT))
        assert command_id in snapshot

    @pytest.mark.asyncio
    async def test_submit_modify_noop_when_protection_not_active(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter()
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]
        runtime.brackets[command_id].protection_status = (
            BracketProtectionStatus.FAILED
        )

        em.submit_modify(_modify(command_id, take_profit_price=_NEW_TP_PRICE))

        assert runtime.priority_queue.empty()
        assert command_id not in em.modifiable_command_ids(_ACCT)
