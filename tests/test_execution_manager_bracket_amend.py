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
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

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
)
from praxis.core.domain.trade_modify import TradeModify
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.bracket_exit_command_id import bracket_exit_command_id
from praxis.core.execution_manager import ExecutionManager
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    CancelResult,
    DuplicateClientOrderIdError,
    ImmediateFill,
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


class TestBracketAmendPartialFill:

    @pytest.mark.asyncio
    async def test_partial_protective_fill_shrinks_replacement_qty(
        self, mgr_factory: Any,
    ) -> None:
        adapter = _make_adapter(leg_filled={_LEG_SL: Decimal('0.4')})
        em, _ = mgr_factory(adapter)
        command_id = await _protected_bracket(em)
        runtime = em._accounts[_ACCT]

        await em._process_modify(runtime, _modify(command_id, take_profit_price=_NEW_TP_PRICE))

        replacement = _oco_calls(adapter)[-1]
        assert replacement['args'][_QTY_ARG_INDEX] == Decimal('0.6')

    @pytest.mark.asyncio
    async def test_dust_remaining_places_no_replacement_and_drops_bracket(
        self, mgr_factory: Any, spine: EventSpine,
    ) -> None:
        adapter = _make_adapter(leg_filled={_LEG_SL: Decimal('0.9999')})
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
