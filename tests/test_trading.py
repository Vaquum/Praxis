from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

import aiosqlite
import pytest
import pytest_asyncio

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.position import Position
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.events import (
    CommandAccepted,
    FillReceived,
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


@pytest_asyncio.fixture
async def spine() -> AsyncGenerator[EventSpine, None]:
    conn = await aiosqlite.connect(':memory:')
    es = EventSpine(conn)
    await es.ensure_schema()
    try:
        yield es
    finally:
        await conn.close()


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
