from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

import aiosqlite
import pytest

from praxis.core.domain.enums import (
    ExecutionMode,
    ExecutionType,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.health_snapshot import HealthSnapshot
from praxis.core.domain.position import Position
from praxis.core.domain.order import Order
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.domain.events import (
    CommandAccepted,
    FillReceived,
    OrderCanceled,
    OrderExpired,
    OrderRejected,
    OrderSubmitIntent,
    OrderSubmitted,
    TradeOutcomeProduced,
)
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.binance_urls import TESTNET_REST_URL, TESTNET_WS_URL
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import (
    BalanceEntry,
    CancelResult,
    ExecutionReport,
    NotFoundError,
    OrderBookSnapshot,
    SubmitResult,
    SymbolFilters,
    VenueAdapter,
    VenueError,
    VenueOrder,
    VenueTrade,
)
from praxis.trading import Trading
from praxis.trading_config import TradingConfig
from praxis.trading_inbound import TradingInbound

_CREATED_AT = datetime(2099, 1, 1, tzinfo=timezone.utc)


class _InjectedVenueAdapter:
    def register_account(self, account_id: str, api_key: str, api_secret: str) -> None:
        del account_id, api_key, api_secret

    def unregister_account(self, account_id: str) -> None:
        del account_id

    async def submit_order(
        self,
        account_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: Decimal,
        *,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        stop_limit_price: Decimal | None = None,
        client_order_id: str | None = None,
        time_in_force: str | None = None,
    ) -> SubmitResult:
        del (
            account_id,
            symbol,
            side,
            order_type,
            qty,
            price,
            stop_price,
            stop_limit_price,
            client_order_id,
            time_in_force,
        )
        raise NotImplementedError

    async def cancel_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:
        del account_id, symbol, venue_order_id, client_order_id
        raise NotImplementedError

    async def cancel_order_list(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:
        del account_id, symbol, venue_order_id, client_order_id
        raise NotImplementedError

    async def query_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> VenueOrder:
        del account_id, symbol, venue_order_id, client_order_id
        raise NotFoundError('not found')

    async def query_open_orders(self, account_id: str, symbol: str) -> list[VenueOrder]:
        del account_id, symbol
        return []

    async def query_balance(
        self,
        account_id: str,
        assets: frozenset[str],
    ) -> list[BalanceEntry]:
        del account_id, assets
        return []

    async def query_trades(
        self,
        account_id: str,
        symbol: str,
        *,
        start_time: datetime | None = None,
    ) -> list[VenueTrade]:
        del account_id, symbol, start_time
        return []

    async def get_exchange_info(self, symbol: str) -> SymbolFilters:
        del symbol
        raise NotImplementedError

    async def query_order_book(
        self,
        symbol: str,
        *,
        limit: int = 20,
    ) -> OrderBookSnapshot:
        del symbol, limit
        raise NotImplementedError

    async def get_server_time(self) -> int:
        raise NotImplementedError

    async def load_filters(self, symbols: Sequence[str]) -> None:
        self.loaded_symbols = list(symbols)

    def parse_execution_report(self, data: dict[str, object]) -> ExecutionReport:
        del data
        raise NotImplementedError

    def get_health_snapshot(self, account_id: str) -> HealthSnapshot:
        del account_id
        return HealthSnapshot()


class _FakeInbound:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.unregister_fail_once: set[str] = set()

    def register_account(self, account_id: str) -> None:
        self.calls.append(('register_account', account_id))

    async def unregister_account(self, account_id: str) -> None:
        self.calls.append(('unregister_account', account_id))
        if account_id in self.unregister_fail_once:
            self.unregister_fail_once.remove(account_id)
            msg = f'unregister failed for {account_id}'
            raise RuntimeError(msg)

    async def submit_command(self, **kwargs: object) -> str:
        self.calls.append(('submit_command', kwargs))
        return 'cmd-1'

    def submit_abort(self, abort: TradeAbort) -> None:
        self.calls.append(('submit_abort', abort))

    def pull_positions(self, account_id: str) -> dict[tuple[str, str], Position]:
        self.calls.append(('pull_positions', account_id))
        return {
            ('trade-1', account_id): Position(
                account_id=account_id,
                trade_id='trade-1',
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                qty=Decimal('1'),
                avg_entry_price=Decimal('50000'),
            )
        }



@pytest.mark.asyncio
async def test_trading_wires_default_dependencies(spine: EventSpine) -> None:
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)

    assert trading.config.epoch_id == 1
    assert trading.event_spine is spine
    assert isinstance(trading.venue_adapter, BinanceAdapter)
    assert isinstance(trading.execution_manager, ExecutionManager)
    assert trading.started is False


@pytest.mark.asyncio
async def test_trading_uses_injected_venue_adapter(spine: EventSpine) -> None:
    adapter = cast(VenueAdapter, _InjectedVenueAdapter())
    trading = Trading(
        config=TradingConfig(epoch_id=1),
        event_spine=spine,
        venue_adapter=adapter,
    )
    assert trading.venue_adapter is adapter


@pytest.mark.asyncio
async def test_trading_delegates_facade_methods(spine: EventSpine) -> None:
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)
    fake_inbound = _FakeInbound()
    trading._inbound = cast(TradingInbound, fake_inbound)
    await trading.start()

    trading.register_account('acc-1')
    trading._ready_accounts.add('acc-1')
    command_id = await trading.submit_command(
        trade_id='trade-1',
        account_id='acc-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        order_type=OrderType.LIMIT,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        execution_params=SingleShotParams(price=Decimal('50000')),
        timeout=300,
        reference_price=None,
        maker_preference=MakerPreference.NO_PREFERENCE,
        stp_mode=STPMode.NONE,
        created_at=_CREATED_AT,
    )
    trading.submit_abort(
        TradeAbort(
            account_id='acc-1',
            command_id='cmd-1',
            reason='cancel',
            created_at=_CREATED_AT,
        )
    )
    positions = trading.pull_positions('acc-1')
    await trading.unregister_account('acc-1')

    assert command_id == 'cmd-1'
    assert ('register_account', 'acc-1') in fake_inbound.calls
    assert ('unregister_account', 'acc-1') in fake_inbound.calls
    assert any(name == 'submit_command' for name, _ in fake_inbound.calls)
    assert any(name == 'submit_abort' for name, _ in fake_inbound.calls)
    assert any(name == 'pull_positions' for name, _ in fake_inbound.calls)
    assert positions[('trade-1', 'acc-1')].qty == Decimal('1')


@pytest.mark.asyncio
async def test_trading_get_health_snapshot_delegates_to_adapter(
    spine: EventSpine,
) -> None:
    adapter = _InjectedVenueAdapter()
    trading = Trading(
        config=TradingConfig(epoch_id=1),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )
    await trading.start()

    snapshot = await trading.get_health_snapshot('acc-1')

    assert isinstance(snapshot, HealthSnapshot)
    assert snapshot.consecutive_failures == 0


@pytest.mark.asyncio
async def test_trading_get_health_snapshot_requires_started(
    spine: EventSpine,
) -> None:
    adapter = _InjectedVenueAdapter()
    trading = Trading(
        config=TradingConfig(epoch_id=1),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )

    with pytest.raises(RuntimeError, match=r'Trading\.start'):
        await trading.get_health_snapshot('acc-1')


@pytest.mark.asyncio
async def test_trading_requires_start_before_facade_operations(
    spine: EventSpine,
) -> None:
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)

    with pytest.raises(RuntimeError, match=r'Trading\.start'):
        trading.register_account('acc-1')

    with pytest.raises(RuntimeError, match=r'Trading\.start'):
        trading.pull_positions('acc-1')

    with pytest.raises(RuntimeError, match=r'Trading\.start'):
        trading.submit_abort(
            TradeAbort(
                account_id='acc-1',
                command_id='cmd-1',
                reason='cancel',
                created_at=_CREATED_AT,
            )
        )


@pytest.mark.asyncio
async def test_trading_stop_unregisters_managed_accounts(
    spine: EventSpine,
) -> None:
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)
    fake_inbound = _FakeInbound()
    trading._inbound = cast(TradingInbound, fake_inbound)

    await trading.start()
    trading.register_account('acc-1')
    trading.register_account('acc-2')
    await trading.stop()

    unregister_calls = [
        payload for name, payload in fake_inbound.calls if name == 'unregister_account'
    ]
    assert set(unregister_calls) == {'acc-1', 'acc-2'}
    assert trading.started is False


@pytest.mark.asyncio
async def test_trading_stop_preserves_state_when_unregister_fails(
    spine: EventSpine,
) -> None:
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)
    fake_inbound = _FakeInbound()
    fake_inbound.unregister_fail_once.add('acc-1')
    trading._inbound = cast(TradingInbound, fake_inbound)

    await trading.start()
    trading.register_account('acc-1')

    with pytest.raises(RuntimeError, match='unregister failed for acc-1'):
        await trading.stop()

    assert trading.started is True
    assert 'acc-1' in trading._managed_accounts

    await trading.stop()
    assert trading.started is False


@pytest.mark.asyncio
async def test_trading_start_ensures_event_spine_schema() -> None:
    conn = await aiosqlite.connect(':memory:')
    spine = EventSpine(conn)
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)

    await trading.start()

    async with conn.execute(
        'SELECT name FROM sqlite_master WHERE type=\'table\' AND name=\'events\''
    ) as cursor:
        row = await cursor.fetchone()
    await conn.close()

    assert row is not None


@pytest.mark.asyncio
async def test_trading_start_registers_config_accounts(spine: EventSpine) -> None:
    adapter = cast(VenueAdapter, _InjectedVenueAdapter())
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={
                'acc-1': ('key1', 'secret1'),
                'acc-2': ('key2', 'secret2'),
            },
        ),
        event_spine=spine,
        venue_adapter=adapter,
    )

    await trading.start()

    assert trading.execution_manager.has_account('acc-1')
    assert trading.execution_manager.has_account('acc-2')
    assert trading._managed_accounts == {'acc-1', 'acc-2'}

    await trading.stop()

@pytest.mark.asyncio
async def test_trading_stop_cleans_up_execution_account_task(spine: EventSpine) -> None:
    adapter = cast(VenueAdapter, _InjectedVenueAdapter())
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': ('key', 'secret')},
        ),
        event_spine=spine,
        venue_adapter=adapter,
    )

    await trading.start()
    trading.register_account('acc-1')

    assert trading.execution_manager.has_account('acc-1')
    runtime_task = trading.execution_manager._accounts['acc-1'].task
    assert runtime_task is not None
    assert runtime_task.get_name() == 'account-acc-1'
    assert runtime_task.done() is False

    await trading.stop()

    assert not trading.execution_manager.has_account('acc-1')
    assert runtime_task.done() is True


@pytest.mark.asyncio
async def test_trading_start_replays_events_into_account_state() -> None:
    conn = await aiosqlite.connect(':memory:')
    spine = EventSpine(conn)
    await spine.ensure_schema()
    epoch = 1
    ts = _CREATED_AT

    await spine.append(CommandAccepted(
        account_id='acc-1', timestamp=ts, command_id='cmd-1', trade_id='trade-1',
    ), epoch)
    await spine.append(OrderSubmitIntent(
        account_id='acc-1', timestamp=ts, command_id='cmd-1', trade_id='trade-1',
        client_order_id='SS-abc-00', symbol='BTCUSDT', side=OrderSide.BUY,
        order_type=OrderType.MARKET, qty=Decimal('2'),
        price=None, stop_price=None, stop_limit_price=None,
    ), epoch)
    await spine.append(OrderSubmitted(
        account_id='acc-1', timestamp=ts,
        client_order_id='SS-abc-00', venue_order_id='v-1',
    ), epoch)
    await spine.append(FillReceived(
        account_id='acc-1', timestamp=ts, client_order_id='SS-abc-00',
        venue_order_id='v-1', venue_trade_id='t-1', trade_id='trade-1',
        command_id='cmd-1', symbol='BTCUSDT', side=OrderSide.BUY,
        qty=Decimal('1'), price=Decimal('50000'), fee=Decimal('0.001'),
        fee_asset='BTC', is_maker=False,
    ), epoch)
    await spine.append(CommandAccepted(
        account_id='acc-1', timestamp=ts, command_id='cmd-2', trade_id='trade-2',
    ), epoch)
    await spine.append(TradeOutcomeProduced(
        account_id='acc-1', timestamp=ts, command_id='cmd-2', trade_id='trade-2',
        status=TradeStatus.REJECTED, reason='test',
    ), epoch)

    adapter = cast(VenueAdapter, _InjectedVenueAdapter())
    trading = Trading(
        config=TradingConfig(
            epoch_id=epoch,
            account_credentials={'acc-1': ('key', 'secret')},
        ),
        event_spine=spine,
        venue_adapter=adapter,
    )
    await trading.start()

    state = trading.execution_manager._accounts['acc-1'].trading_state
    assert ('trade-1', 'acc-1') in state.positions
    assert state.positions[('trade-1', 'acc-1')].qty == Decimal('1')
    assert 'SS-abc-00' in state.orders
    assert trading.execution_manager._accepted_commands == {
        'cmd-1': 'acc-1', 'cmd-2': 'acc-1',
    }
    assert 'cmd-2' in trading.execution_manager._terminal_commands
    assert 'cmd-1' not in trading.execution_manager._terminal_commands

    await trading.stop()
    await conn.close()


@pytest.mark.asyncio
async def test_trading_start_preloads_filters_for_active_symbols() -> None:
    conn = await aiosqlite.connect(':memory:')
    spine = EventSpine(conn)
    await spine.ensure_schema()
    epoch = 1
    ts = _CREATED_AT

    await spine.append(CommandAccepted(
        account_id='acc-1', timestamp=ts, command_id='cmd-1', trade_id='trade-1',
    ), epoch)
    await spine.append(OrderSubmitIntent(
        account_id='acc-1', timestamp=ts, command_id='cmd-1', trade_id='trade-1',
        client_order_id='SS-abc-00', symbol='BTCUSDT', side=OrderSide.BUY,
        order_type=OrderType.MARKET, qty=Decimal('1'),
        price=None, stop_price=None, stop_limit_price=None,
    ), epoch)

    adapter = _InjectedVenueAdapter()
    trading = Trading(
        config=TradingConfig(
            epoch_id=epoch,
            account_credentials={'acc-1': ('key', 'secret')},
        ),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )
    await trading.start()

    assert adapter.loaded_symbols == ['BTCUSDT']

    await trading.stop()
    await conn.close()


@pytest.mark.asyncio
async def test_trading_start_creates_user_stream_for_binance_adapter() -> None:
    conn = await aiosqlite.connect(':memory:')
    spine = EventSpine(conn)
    await spine.ensure_schema()

    adapter = BinanceAdapter(
        base_url=TESTNET_REST_URL,
        ws_base_url=TESTNET_WS_URL,
        credentials={'acc-1': ('key', 'secret')},
    )
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': ('key', 'secret')},
        ),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )

    import unittest.mock
    with (
        unittest.mock.patch.object(
            adapter, '_create_listen_key', return_value='mock-listen-key',
    ), unittest.mock.patch.object(
            adapter, '_ensure_session',
            return_value=unittest.mock.AsyncMock(),
        ),
        unittest.mock.patch(
            'praxis.trading.BinanceUserStream.initiate_connection',
            new_callable=unittest.mock.AsyncMock,
        ),
    ):
        await trading.start()

    assert 'acc-1' in trading._user_streams

    with unittest.mock.patch(
        'praxis.trading.BinanceUserStream.close',
        new_callable=unittest.mock.AsyncMock,
    ):
        await trading.stop()

    assert trading._user_streams == {}

    await conn.close()


@pytest.mark.asyncio
async def test_trading_rejects_commands_for_unready_account(spine: EventSpine) -> None:
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)
    await trading.start()

    trading._managed_accounts.add('acc-pending')

    with pytest.raises(RuntimeError, match='account acc-pending startup not complete'):
        await trading.submit_command(
            trade_id='trade-1',
            account_id='acc-pending',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            order_type=OrderType.LIMIT,
            execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(price=Decimal('50000')),
            timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE,
            created_at=_CREATED_AT,
        )


@pytest.mark.asyncio
async def test_trading_rejects_aborts_for_unready_account(spine: EventSpine) -> None:
    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)
    await trading.start()

    trading._managed_accounts.add('acc-pending')

    with pytest.raises(RuntimeError, match='account acc-pending startup not complete'):
        trading.submit_abort(
            TradeAbort(
                account_id='acc-pending',
                command_id='cmd-1',
                reason='cancel',
                created_at=_CREATED_AT,
            )
        )


class _CancelTrackingVenueAdapter(_InjectedVenueAdapter):

    def __init__(self) -> None:
        self.cancel_calls: list[tuple[str, str]] = []
        self.cancel_list_calls: list[tuple[str, str]] = []

    async def cancel_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:
        del symbol, venue_order_id
        self.cancel_calls.append((account_id, client_order_id or ''))
        return CancelResult(venue_order_id='venue-1', status=OrderStatus.CANCELED)

    async def cancel_order_list(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:
        del symbol, venue_order_id
        self.cancel_list_calls.append((account_id, client_order_id or ''))
        return CancelResult(venue_order_id='venue-1', status=OrderStatus.CANCELED)


@pytest.mark.asyncio
async def test_trading_shutdown_rejects_commands(spine: EventSpine) -> None:
    adapter = cast(VenueAdapter, _InjectedVenueAdapter())
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': ('key', 'secret')},
        ),
        event_spine=spine,
        venue_adapter=adapter,
    )

    await trading.start()
    trading.register_account('acc-1')
    trading._ready_accounts.add('acc-1')
    trading._stopping = True

    with pytest.raises(RuntimeError, match='shutting down'):
        await trading.submit_command(
            trade_id='trade-1',
            account_id='acc-1',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1'),
            order_type=OrderType.LIMIT,
            execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(price=Decimal('50000')),
            timeout=300,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE,
            created_at=_CREATED_AT,
        )

    trading._stopping = False
    await trading.stop()


@pytest.mark.asyncio
async def test_trading_shutdown_rejects_aborts(spine: EventSpine) -> None:
    adapter = cast(VenueAdapter, _InjectedVenueAdapter())
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': ('key', 'secret')},
        ),
        event_spine=spine,
        venue_adapter=adapter,
    )

    await trading.start()
    trading.register_account('acc-1')
    trading._ready_accounts.add('acc-1')
    trading._stopping = True

    with pytest.raises(RuntimeError, match='shutting down'):
        trading.submit_abort(
            TradeAbort(
                account_id='acc-1',
                command_id='cmd-1',
                reason='cancel',
                created_at=_CREATED_AT,
            )
        )

    trading._stopping = False
    await trading.stop()


@pytest.mark.asyncio
async def test_trading_shutdown_cancels_open_orders(spine: EventSpine) -> None:
    from praxis.core.domain.order import Order

    adapter = _CancelTrackingVenueAdapter()
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': ('key', 'secret')},
            shutdown_timeout=0.1,
        ),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )

    await trading.start()
    trading.register_account('acc-1')
    trading._ready_accounts.add('acc-1')

    fake_order = Order(
        client_order_id='coid-1',
        venue_order_id='venue-1',
        account_id='acc-1',
        command_id='cmd-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        cumulative_notional=Decimal('0'),
        price=Decimal('50000'),
        stop_price=None,
        status=OrderStatus.OPEN,
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
    )
    trading._execution_manager._accounts['acc-1'].trading_state.orders['coid-1'] = fake_order

    await trading.stop()

    assert ('acc-1', 'coid-1') in adapter.cancel_calls


@pytest.mark.asyncio
async def test_trading_shutdown_cancels_oco_orders_via_cancel_order_list(
    spine: EventSpine,
) -> None:
    from praxis.core.domain.order import Order

    adapter = _CancelTrackingVenueAdapter()
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': ('key', 'secret')},
            shutdown_timeout=0.1,
        ),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )

    await trading.start()
    trading.register_account('acc-1')
    trading._ready_accounts.add('acc-1')

    oco_order = Order(
        client_order_id='oco-list-1',
        venue_order_id='venue-oco-1',
        account_id='acc-1',
        command_id='cmd-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.OCO,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        cumulative_notional=Decimal('0'),
        price=Decimal('50000'),
        stop_price=Decimal('48000'),
        status=OrderStatus.OPEN,
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
    )
    trading._execution_manager._accounts['acc-1'].trading_state.orders['oco-list-1'] = oco_order

    await trading.stop()

    assert ('acc-1', 'oco-list-1') in adapter.cancel_list_calls
    assert ('acc-1', 'oco-list-1') not in adapter.cancel_calls


class _ReconVenueAdapter(_InjectedVenueAdapter):

    def __init__(self) -> None:
        self._venue_orders: dict[str, VenueOrder] = {}
        self._venue_trades: list[VenueTrade] = []

    async def query_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> VenueOrder:
        del account_id, symbol, venue_order_id
        key = client_order_id or ''
        if key in self._venue_orders:
            return self._venue_orders[key]
        raise NotFoundError('not found')

    async def query_trades(
        self,
        account_id: str,
        symbol: str,
        *,
        start_time: datetime | None = None,
    ) -> list[VenueTrade]:
        del account_id, symbol, start_time
        return self._venue_trades

    async def cancel_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:
        del account_id, symbol, venue_order_id, client_order_id
        return CancelResult(venue_order_id='v-1', status=OrderStatus.CANCELED)


def _make_order(
    client_order_id: str = 'SS-cmd1-00',
    venue_order_id: str = 'v-1',
    command_id: str = 'cmd-1',
    status: OrderStatus = OrderStatus.OPEN,
    filled_qty: Decimal = Decimal('0'),
    cumulative_notional: Decimal = Decimal('0'),
) -> Order:
    return Order(
        client_order_id=client_order_id,
        venue_order_id=venue_order_id,
        account_id='acc-1',
        command_id=command_id,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=filled_qty,
        cumulative_notional=cumulative_notional,
        price=None,
        stop_price=None,
        status=status,
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
    )


async def _started_trading_with_recon_adapter(
    spine: EventSpine,
) -> tuple[Trading, _ReconVenueAdapter]:
    adapter = _ReconVenueAdapter()
    trading = Trading(
        config=TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': ('key', 'secret')},
            shutdown_timeout=0.1,
        ),
        event_spine=spine,
        venue_adapter=cast(VenueAdapter, adapter),
    )
    await trading.start()
    return trading, adapter


@pytest.mark.asyncio
async def test_reconcile_account_skips_terminal_orders(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order(status=OrderStatus.FILLED, filled_qty=Decimal('1'))
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order

    await trading._reconcile_account('acc-1')

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_account_handles_not_found(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order

    await trading._reconcile_account('acc-1')

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_account_reconciles_fills_when_venue_has_more(
    spine: EventSpine,
) -> None:
    trading, adapter = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order
    trading._execution_manager._command_trade_ids['cmd-1'] = 'trade-1'

    adapter._venue_orders['SS-cmd1-00'] = VenueOrder(
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        status=OrderStatus.OPEN,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=Decimal('1'),
        price=None,
    )
    adapter._venue_trades = [VenueTrade(
        venue_trade_id='t-1',
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal('50000'),
        fee=Decimal('0.001'),
        fee_asset='BTC',
        is_maker=False,
        timestamp=_CREATED_AT,
    )]

    await trading._reconcile_account('acc-1')
    await asyncio.sleep(0.15)

    events = await spine.read(1)
    assert len(events) == 1
    _, event = events[0]
    assert isinstance(event, FillReceived)
    assert event.venue_trade_id == 't-1'
    assert event.trade_id == 'trade-1'
    state = trading._execution_manager._accounts['acc-1'].trading_state
    assert ('trade-1', 'acc-1') in state.positions
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_account_emits_terminal_when_venue_is_terminal(
    spine: EventSpine,
) -> None:
    trading, adapter = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order

    adapter._venue_orders['SS-cmd1-00'] = VenueOrder(
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        status=OrderStatus.CANCELED,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        price=None,
    )

    await trading._reconcile_account('acc-1')

    events = await spine.read(1)
    assert len(events) == 1
    _, event = events[0]
    assert isinstance(event, OrderCanceled)
    assert event.client_order_id == 'SS-cmd1-00'
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_fills_deduplicates(spine: EventSpine) -> None:
    trading, adapter = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order
    trading._execution_manager._command_trade_ids['cmd-1'] = 'trade-1'

    trade = VenueTrade(
        venue_trade_id='t-1',
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal('50000'),
        fee=Decimal('0.001'),
        fee_asset='BTC',
        is_maker=False,
        timestamp=_CREATED_AT,
    )
    adapter._venue_trades = [trade]

    await trading._reconcile_fills('acc-1', order)
    events_after_first = await spine.read(1)
    assert len(events_after_first) == 1

    await trading._reconcile_fills('acc-1', order)
    events_after_second = await spine.read(1)
    assert len(events_after_second) == 1
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_fills_skips_unknown_account(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)

    order = _make_order()
    await trading._reconcile_fills('unknown-acc', order)

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_fills_handles_venue_error(spine: EventSpine) -> None:
    trading, adapter = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order

    async def fail_trades(
        account_id: str,
        symbol: str,
        *,
        start_time: datetime | None = None,
    ) -> list[VenueTrade]:
        del account_id, symbol, start_time
        raise VenueError('connection lost')

    adapter.query_trades = fail_trades  # type: ignore[method-assign]

    await trading._reconcile_fills('acc-1', order)

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_fills_skips_mismatched_client_order_id(
    spine: EventSpine,
) -> None:
    trading, adapter = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order
    trading._execution_manager._command_trade_ids['cmd-1'] = 'trade-1'

    adapter._venue_trades = [VenueTrade(
        venue_trade_id='t-1',
        venue_order_id='v-1',
        client_order_id='DIFFERENT-ORDER',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal('50000'),
        fee=Decimal('0.001'),
        fee_asset='BTC',
        is_maker=False,
        timestamp=_CREATED_AT,
    )]

    await trading._reconcile_fills('acc-1', order)

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_fills_skips_missing_trade_id_mapping(
    spine: EventSpine,
) -> None:
    trading, adapter = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order

    adapter._venue_trades = [VenueTrade(
        venue_trade_id='t-1',
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal('50000'),
        fee=Decimal('0.001'),
        fee_asset='BTC',
        is_maker=False,
        timestamp=_CREATED_AT,
    )]

    await trading._reconcile_fills('acc-1', order)

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_terminal_emits_canceled(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    venue_order = VenueOrder(
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        status=OrderStatus.CANCELED,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        price=None,
    )

    await trading._reconcile_terminal('acc-1', order, venue_order)

    events = await spine.read(1)
    assert len(events) == 1
    _, event = events[0]
    assert isinstance(event, OrderCanceled)
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_terminal_emits_expired(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    venue_order = VenueOrder(
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        status=OrderStatus.EXPIRED,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        price=None,
    )

    await trading._reconcile_terminal('acc-1', order, venue_order)

    events = await spine.read(1)
    assert len(events) == 1
    _, event = events[0]
    assert isinstance(event, OrderExpired)
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_terminal_emits_rejected(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    venue_order = VenueOrder(
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        status=OrderStatus.REJECTED,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        price=None,
    )

    await trading._reconcile_terminal('acc-1', order, venue_order)

    events = await spine.read(1)
    assert len(events) == 1
    _, event = events[0]
    assert isinstance(event, OrderRejected)
    await trading.stop()


@pytest.mark.asyncio
async def test_reconcile_terminal_skips_non_terminal_venue_status(
    spine: EventSpine,
) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    venue_order = VenueOrder(
        venue_order_id='v-1',
        client_order_id='SS-cmd1-00',
        status=OrderStatus.OPEN,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=Decimal('0'),
        price=None,
    )

    await trading._reconcile_terminal('acc-1', order, venue_order)

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_on_execution_report_ignores_non_execution_report(
    spine: EventSpine,
) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)

    await trading._on_execution_report('acc-1', {'e': 'outboundAccountPosition'})

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_on_execution_report_ignores_non_binance_adapter(
    spine: EventSpine,
) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)

    await trading._on_execution_report('acc-1', {'e': 'executionReport'})

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_on_execution_report_skips_unknown_account(
    spine: EventSpine,
) -> None:
    import unittest.mock
    trading, _ = await _started_trading_with_recon_adapter(spine)
    trading._venue_adapter = cast(VenueAdapter, unittest.mock.MagicMock(spec=BinanceAdapter))

    await trading._on_execution_report('unknown-acc', {'e': 'executionReport'})

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_on_execution_report_processes_fill(spine: EventSpine) -> None:
    import unittest.mock
    trading, _ = await _started_trading_with_recon_adapter(spine)

    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order
    trading._execution_manager._command_trade_ids['cmd-1'] = 'trade-1'

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.TRADE,
        order_status=OrderStatus.FILLED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('1'),
        last_filled_price=Decimal('50000'),
        cumulative_filled_qty=Decimal('1'),
        commission=Decimal('0.001'),
        commission_asset='BTC',
        transaction_time=_CREATED_AT,
        venue_trade_id='t-ws-1',
        is_maker=False,
    )

    mock_adapter = unittest.mock.MagicMock(spec=BinanceAdapter)
    mock_adapter.parse_execution_report.return_value = report
    trading._venue_adapter = cast(VenueAdapter, mock_adapter)

    await trading._on_execution_report('acc-1', {'e': 'executionReport'})
    await asyncio.sleep(0.15)

    events = await spine.read(1)
    assert len(events) == 1
    _, event = events[0]
    assert isinstance(event, FillReceived)
    assert event.venue_trade_id == 't-ws-1'
    assert event.trade_id == 'trade-1'

    state = trading._execution_manager._accounts['acc-1'].trading_state
    assert ('trade-1', 'acc-1') in state.positions
    await trading.stop()


@pytest.mark.asyncio
async def test_on_execution_report_skips_terminal_for_closed_order(
    spine: EventSpine,
) -> None:
    import unittest.mock
    trading, _ = await _started_trading_with_recon_adapter(spine)

    order = _make_order(status=OrderStatus.FILLED, filled_qty=Decimal('1'))
    trading._execution_manager._accounts['acc-1'].trading_state.closed_orders['SS-cmd1-00'] = order

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.CANCELED,
        order_status=OrderStatus.CANCELED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('0'),
        last_filled_price=Decimal('0'),
        cumulative_filled_qty=Decimal('1'),
        commission=Decimal('0'),
        commission_asset=None,
        transaction_time=_CREATED_AT,
        venue_trade_id=None,
        is_maker=False,
    )

    mock_adapter = unittest.mock.MagicMock(spec=BinanceAdapter)
    mock_adapter.parse_execution_report.return_value = report
    trading._venue_adapter = cast(VenueAdapter, mock_adapter)

    await trading._on_execution_report('acc-1', {'e': 'executionReport'})

    events = await spine.read(1)
    assert len(events) == 0
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_trade(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd1-00'] = order
    trading._execution_manager._command_trade_ids['cmd-1'] = 'trade-1'

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.TRADE,
        order_status=OrderStatus.FILLED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('1'),
        last_filled_price=Decimal('50000'),
        cumulative_filled_qty=Decimal('1'),
        commission=Decimal('0.001'),
        commission_asset='BTC',
        transaction_time=_CREATED_AT,
        venue_trade_id='t-1',
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert isinstance(event, FillReceived)
    assert event.venue_trade_id == 't-1'
    assert event.trade_id == 'trade-1'
    assert event.qty == Decimal('1')
    assert event.price == Decimal('50000')
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_canceled(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.CANCELED,
        order_status=OrderStatus.CANCELED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('0'),
        last_filled_price=Decimal('0'),
        cumulative_filled_qty=Decimal('0'),
        commission=Decimal('0'),
        commission_asset=None,
        transaction_time=_CREATED_AT,
        venue_trade_id=None,
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert isinstance(event, OrderCanceled)
    assert event.client_order_id == 'SS-cmd1-00'
    assert event.reason == 'canceled via WebSocket'
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_rejected(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.REJECTED,
        order_status=OrderStatus.REJECTED,
        reject_reason='INSUFFICIENT_BALANCE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('0'),
        last_filled_price=Decimal('0'),
        cumulative_filled_qty=Decimal('0'),
        commission=Decimal('0'),
        commission_asset=None,
        transaction_time=_CREATED_AT,
        venue_trade_id=None,
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert isinstance(event, OrderRejected)
    assert event.reason == 'INSUFFICIENT_BALANCE'
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_expired(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.EXPIRED,
        order_status=OrderStatus.EXPIRED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('0'),
        last_filled_price=Decimal('0'),
        cumulative_filled_qty=Decimal('0'),
        commission=Decimal('0'),
        commission_asset=None,
        transaction_time=_CREATED_AT,
        venue_trade_id=None,
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert isinstance(event, OrderExpired)
    assert event.client_order_id == 'SS-cmd1-00'
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_unknown_type(spine: EventSpine) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.NEW,
        order_status=OrderStatus.OPEN,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('0'),
        last_filled_price=Decimal('0'),
        cumulative_filled_qty=Decimal('0'),
        commission=Decimal('0'),
        commission_asset=None,
        transaction_time=_CREATED_AT,
        venue_trade_id=None,
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert event is None
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_trade_missing_venue_trade_id(
    spine: EventSpine,
) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._command_trade_ids['cmd-1'] = 'trade-1'

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.TRADE,
        order_status=OrderStatus.FILLED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('1'),
        last_filled_price=Decimal('50000'),
        cumulative_filled_qty=Decimal('1'),
        commission=Decimal('0.001'),
        commission_asset='BTC',
        transaction_time=_CREATED_AT,
        venue_trade_id=None,
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert event is None
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_trade_missing_commission_asset(
    spine: EventSpine,
) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()
    trading._execution_manager._command_trade_ids['cmd-1'] = 'trade-1'

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.TRADE,
        order_status=OrderStatus.FILLED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('1'),
        last_filled_price=Decimal('50000'),
        cumulative_filled_qty=Decimal('1'),
        commission=Decimal('0.001'),
        commission_asset=None,
        transaction_time=_CREATED_AT,
        venue_trade_id='t-1',
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert event is None
    await trading.stop()


@pytest.mark.asyncio
async def test_convert_execution_report_trade_missing_trade_id_mapping(
    spine: EventSpine,
) -> None:
    trading, _ = await _started_trading_with_recon_adapter(spine)
    order = _make_order()

    report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd1-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.TRADE,
        order_status=OrderStatus.FILLED,
        reject_reason='NONE',
        venue_order_id='v-1',
        last_filled_qty=Decimal('1'),
        last_filled_price=Decimal('50000'),
        cumulative_filled_qty=Decimal('1'),
        commission=Decimal('0.001'),
        commission_asset='BTC',
        transaction_time=_CREATED_AT,
        venue_trade_id='t-1',
        is_maker=False,
    )

    event = trading._convert_execution_report('acc-1', report, order)
    assert event is None
    await trading.stop()


@pytest.mark.asyncio
async def test_concurrent_ws_fills_no_corruption(spine: EventSpine) -> None:
    import unittest.mock
    trading, _ = await _started_trading_with_recon_adapter(spine)

    for i in range(5):
        order = _make_order(
            client_order_id=f'SS-cmd{i}-00',
            command_id=f'cmd-{i}',
        )
        trading._execution_manager._accounts['acc-1'].trading_state.orders[f'SS-cmd{i}-00'] = order
        trading._execution_manager._command_trade_ids[f'cmd-{i}'] = f'trade-{i}'

    def make_report(idx: int) -> ExecutionReport:
        return ExecutionReport(
            event_time=_CREATED_AT,
            symbol='BTCUSDT',
            client_order_id=f'SS-cmd{idx}-00',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            original_qty=Decimal('1'),
            original_price=Decimal('0'),
            execution_type=ExecutionType.TRADE,
            order_status=OrderStatus.FILLED,
            reject_reason='NONE',
            venue_order_id=f'v-{idx}',
            last_filled_qty=Decimal('1'),
            last_filled_price=Decimal('50000'),
            cumulative_filled_qty=Decimal('1'),
            commission=Decimal('0.001'),
            commission_asset='BTC',
            transaction_time=_CREATED_AT,
            venue_trade_id=f't-ws-{idx}',
            is_maker=False,
        )

    mock_adapter = unittest.mock.MagicMock(spec=BinanceAdapter)
    mock_adapter.parse_execution_report.side_effect = [make_report(i) for i in range(5)]
    trading._venue_adapter = cast(VenueAdapter, mock_adapter)

    await asyncio.gather(*[
        trading._on_execution_report('acc-1', {'e': 'executionReport'})
        for _ in range(5)
    ])
    await asyncio.sleep(0.2)

    state = trading._execution_manager._accounts['acc-1'].trading_state
    assert len(state.positions) == 5
    for i in range(5):
        assert (f'trade-{i}', 'acc-1') in state.positions
        pos = state.positions[(f'trade-{i}', 'acc-1')]
        assert pos.qty == Decimal('1')

    await trading.stop()


@pytest.mark.asyncio
async def test_concurrent_fills_and_reconciliation_no_corruption(spine: EventSpine) -> None:
    import unittest.mock
    trading, adapter = await _started_trading_with_recon_adapter(spine)

    order_ws = _make_order(client_order_id='SS-cmd-ws-00', command_id='cmd-ws')
    order_recon = _make_order(client_order_id='SS-cmd-recon-00', command_id='cmd-recon')
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd-ws-00'] = order_ws
    trading._execution_manager._accounts['acc-1'].trading_state.orders['SS-cmd-recon-00'] = order_recon
    trading._execution_manager._command_trade_ids['cmd-ws'] = 'trade-ws'
    trading._execution_manager._command_trade_ids['cmd-recon'] = 'trade-recon'

    adapter._venue_orders['SS-cmd-recon-00'] = VenueOrder(
        venue_order_id='v-recon',
        client_order_id='SS-cmd-recon-00',
        status=OrderStatus.OPEN,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal('1'),
        filled_qty=Decimal('1'),
        price=None,
    )
    adapter._venue_trades = [VenueTrade(
        venue_trade_id='t-recon',
        venue_order_id='v-recon',
        client_order_id='SS-cmd-recon-00',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal('50000'),
        fee=Decimal('0.001'),
        fee_asset='BTC',
        is_maker=False,
        timestamp=_CREATED_AT,
    )]

    ws_report = ExecutionReport(
        event_time=_CREATED_AT,
        symbol='BTCUSDT',
        client_order_id='SS-cmd-ws-00',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        original_qty=Decimal('1'),
        original_price=Decimal('0'),
        execution_type=ExecutionType.TRADE,
        order_status=OrderStatus.FILLED,
        reject_reason='NONE',
        venue_order_id='v-ws',
        last_filled_qty=Decimal('1'),
        last_filled_price=Decimal('50000'),
        cumulative_filled_qty=Decimal('1'),
        commission=Decimal('0.001'),
        commission_asset='BTC',
        transaction_time=_CREATED_AT,
        venue_trade_id='t-ws',
        is_maker=False,
    )

    mock_adapter = unittest.mock.MagicMock(spec=BinanceAdapter)
    mock_adapter.parse_execution_report.return_value = ws_report
    mock_adapter.query_order.side_effect = adapter.query_order
    mock_adapter.query_trades.side_effect = adapter.query_trades
    trading._venue_adapter = cast(VenueAdapter, mock_adapter)

    await asyncio.gather(
        trading._on_execution_report('acc-1', {'e': 'executionReport'}),
        trading._reconcile_account('acc-1'),
    )
    await asyncio.sleep(0.2)

    state = trading._execution_manager._accounts['acc-1'].trading_state
    assert ('trade-ws', 'acc-1') in state.positions
    assert ('trade-recon', 'acc-1') in state.positions
    assert state.positions[('trade-ws', 'acc-1')].qty == Decimal('1')
    assert state.positions[('trade-recon', 'acc-1')].qty == Decimal('1')

    await trading.stop()


@pytest.mark.asyncio
async def test_loop_available_after_start(spine: EventSpine) -> None:
    '''Trading.loop returns event loop after start().'''

    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)
    await trading.start()

    loop = trading.loop

    assert loop is asyncio.get_running_loop()

    await trading.stop()


@pytest.mark.asyncio
async def test_loop_raises_before_start(spine: EventSpine) -> None:
    '''Trading.loop raises RuntimeError before start().'''

    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)

    with pytest.raises(RuntimeError, match='start\\(\\) must be awaited'):
        _ = trading.loop


@pytest.mark.asyncio
async def test_outcome_routing_to_correct_queue(spine: EventSpine) -> None:
    '''route_outcome puts outcome on correct account queue.'''

    import queue as queue_mod

    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)

    q1: queue_mod.Queue[TradeOutcome] = queue_mod.Queue()
    q2: queue_mod.Queue[TradeOutcome] = queue_mod.Queue()
    trading.register_outcome_queue('acc-1', q1)
    trading.register_outcome_queue('acc-2', q2)

    outcome1 = TradeOutcome(
        command_id='cmd-1',
        trade_id='trade-1',
        account_id='acc-1',
        status=TradeStatus.FILLED,
        target_qty=Decimal('1'),
        filled_qty=Decimal('1'),
        avg_fill_price=Decimal('50000'),
        slices_completed=1,
        slices_total=1,
        reason=None,
        created_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    outcome2 = TradeOutcome(
        command_id='cmd-2',
        trade_id='trade-2',
        account_id='acc-2',
        status=TradeStatus.REJECTED,
        target_qty=Decimal('1'),
        filled_qty=Decimal('0'),
        avg_fill_price=None,
        slices_completed=0,
        slices_total=1,
        reason='insufficient balance',
        created_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )

    trading.route_outcome(outcome1)
    trading.route_outcome(outcome2)

    assert q1.get_nowait() is outcome1
    assert q2.get_nowait() is outcome2
    assert q1.empty()
    assert q2.empty()


@pytest.mark.asyncio
async def test_outcome_routing_unknown_account_drops(spine: EventSpine) -> None:
    '''route_outcome drops outcome for unregistered account.'''

    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)

    outcome = TradeOutcome(
        command_id='cmd-1',
        trade_id='trade-1',
        account_id='unknown',
        status=TradeStatus.FILLED,
        target_qty=Decimal('1'),
        filled_qty=Decimal('1'),
        avg_fill_price=Decimal('50000'),
        slices_completed=1,
        slices_total=1,
        reason=None,
        created_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )

    trading.route_outcome(outcome)


@pytest.mark.asyncio
async def test_unregister_outcome_queue(spine: EventSpine) -> None:
    '''unregister_outcome_queue removes queue.'''

    import queue as queue_mod

    trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)

    q: queue_mod.Queue[TradeOutcome] = queue_mod.Queue()
    trading.register_outcome_queue('acc-1', q)
    trading.unregister_outcome_queue('acc-1')

    outcome = TradeOutcome(
        command_id='cmd-1',
        trade_id='trade-1',
        account_id='acc-1',
        status=TradeStatus.FILLED,
        target_qty=Decimal('1'),
        filled_qty=Decimal('1'),
        avg_fill_price=Decimal('50000'),
        slices_completed=1,
        slices_total=1,
        reason=None,
        created_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )

    trading.route_outcome(outcome)
    assert q.empty()


@pytest.mark.asyncio
async def test_loop_cleared_on_failed_start(spine: EventSpine) -> None:
    '''Trading.loop raises after start() fails, _loop is not left stale.'''

    from unittest.mock import AsyncMock

    config = TradingConfig(
        epoch_id=1,
        account_credentials={'acc-1': ('key', 'secret')},
    )
    trading = Trading(config=config, event_spine=spine, venue_adapter=_InjectedVenueAdapter())
    trading._event_spine.read = AsyncMock(side_effect=RuntimeError('db error'))

    with pytest.raises(RuntimeError, match='db error'):
        await trading.start()

    assert trading.started is False

    with pytest.raises(RuntimeError, match=r'Trading\.start'):
        _ = trading.loop
