from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict
import pytest

from praxis.core.execution_manager import AccountNotRegisteredError
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.trading_inbound import TradingInbound


class _SubmitCommandKwargs(TypedDict):
    trade_id: str
    account_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    order_type: OrderType
    execution_mode: ExecutionMode
    execution_params: SingleShotParams
    timeout: int
    reference_price: Decimal | None
    maker_preference: MakerPreference
    stp_mode: STPMode
    created_at: datetime


_CREATED_AT = datetime(2099, 1, 1, tzinfo=timezone.utc)
_SUBMIT_COMMAND_KWARGS: _SubmitCommandKwargs = {
    'trade_id': 'trade-1',
    'account_id': 'acc-1',
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
    'created_at': _CREATED_AT,
}


class _FakeExecutionManager:
    def __init__(self) -> None:
        self.accounts: set[str] = set()
        self.has_account_calls: list[str] = []
        self.registered: list[str] = []
        self.unregistered: list[str] = []
        self.submit_command_calls: list[str] = []
        self.submit_abort_calls: list[str] = []
        self.last_submit_command: dict[str, object] | None = None
        self.register_error: Exception | None = None
        self.unregister_error: Exception | None = None
        self.submit_command_error: Exception | None = None
        self.submit_abort_error: Exception | None = None

    def has_account(self, account_id: str) -> bool:
        self.has_account_calls.append(account_id)
        return account_id in self.accounts

    def register_account(self, account_id: str) -> None:
        if self.register_error is not None:
            raise self.register_error
        self.accounts.add(account_id)
        self.registered.append(account_id)

    async def unregister_account(self, account_id: str) -> None:
        if self.unregister_error is not None:
            raise self.unregister_error
        if account_id not in self.accounts:
            msg = f"account_id '{account_id}' is not registered"
            raise AccountNotRegisteredError(msg)
        self.accounts.remove(account_id)
        self.unregistered.append(account_id)

    async def submit_command(
        self,
        *,
        trade_id: str,
        account_id: str,
        symbol: str,
        side: OrderSide,
        qty: Decimal,
        order_type: OrderType,
        execution_mode: ExecutionMode,
        execution_params: SingleShotParams,
        timeout: int,
        reference_price: Decimal | None,
        maker_preference: MakerPreference,
        stp_mode: STPMode,
        created_at: datetime,
    ) -> str:
        if self.submit_command_error is not None:
            raise self.submit_command_error
        self.submit_command_calls.append(account_id)
        self.last_submit_command = {
            'trade_id': trade_id,
            'account_id': account_id,
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'order_type': order_type,
            'execution_mode': execution_mode,
            'execution_params': execution_params,
            'timeout': timeout,
            'reference_price': reference_price,
            'maker_preference': maker_preference,
            'stp_mode': stp_mode,
            'created_at': created_at,
        }
        return 'cmd-123'

    def submit_abort(self, abort: TradeAbort) -> None:
        if self.submit_abort_error is not None:
            raise self.submit_abort_error
        self.submit_abort_calls.append(abort.account_id)


class _FakeVenueAdapter:
    def __init__(self) -> None:
        self.credentials: dict[str, tuple[str, str]] = {}

    def register_account(
        self,
        account_id: str,
        api_key: str,
        api_secret: str,
    ) -> None:
        self.credentials[account_id] = (api_key, api_secret)

    def unregister_account(self, account_id: str) -> None:
        del self.credentials[account_id]


def test_register_account_happy_path() -> None:
    execution = _FakeExecutionManager()
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    trading.register_account('acc-1')

    assert execution.has_account_calls == ['acc-1']
    assert execution.registered == ['acc-1']
    assert venue.credentials['acc-1'] == ('key-1', 'secret-1')


def test_register_account_unknown_credentials_raises() -> None:
    trading = TradingInbound(
        execution_manager=_FakeExecutionManager(),
        venue_adapter=_FakeVenueAdapter(),
        account_credentials={},
    )

    with pytest.raises(ValueError, match='no credentials configured'):
        trading.register_account('missing')


def test_register_account_empty_account_id_raises() -> None:
    trading = TradingInbound(
        execution_manager=_FakeExecutionManager(),
        venue_adapter=_FakeVenueAdapter(),
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    with pytest.raises(ValueError, match='non-empty string'):
        trading.register_account('')


def test_register_account_rolls_back_venue_on_execution_failure() -> None:
    execution = _FakeExecutionManager()
    execution.register_error = ValueError('execution register failed')
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    with pytest.raises(ValueError, match='execution register failed'):
        trading.register_account('acc-1')

    assert 'acc-1' not in venue.credentials


def test_register_account_rolls_back_venue_on_runtime_error() -> None:
    execution = _FakeExecutionManager()
    execution.register_error = RuntimeError('no running event loop')
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    with pytest.raises(RuntimeError, match='no running event loop'):
        trading.register_account('acc-1')

    assert 'acc-1' not in venue.credentials


def test_register_account_already_registered_does_not_rollback() -> None:
    execution = _FakeExecutionManager()
    execution.accounts.add('acc-1')
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    trading.register_account('acc-1')

    assert execution.registered == []
    assert venue.credentials['acc-1'] == ('key-1', 'secret-1')


@pytest.mark.asyncio
async def test_unregister_account_removes_runtime_and_credentials() -> None:
    execution = _FakeExecutionManager()
    venue = _FakeVenueAdapter()
    execution.register_account('acc-1')
    venue.register_account('acc-1', 'key-1', 'secret-1')
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    await trading.unregister_account('acc-1')

    assert execution.unregistered == ['acc-1']
    assert 'acc-1' not in venue.credentials


@pytest.mark.asyncio
async def test_unregister_account_cleans_up_venue_when_execution_raises() -> None:
    execution = _FakeExecutionManager()
    execution.unregister_error = ValueError('account missing')
    venue = _FakeVenueAdapter()
    execution.register_account('acc-1')
    venue.register_account('acc-1', 'key-1', 'secret-1')
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    with pytest.raises(ValueError, match='account missing'):
        await trading.unregister_account('acc-1')

    assert 'acc-1' not in venue.credentials


@pytest.mark.asyncio
async def test_submit_command_routes_and_returns_command_id() -> None:
    execution = _FakeExecutionManager()
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    command_id = await trading.submit_command(**_SUBMIT_COMMAND_KWARGS)

    assert command_id == 'cmd-123'
    assert execution.submit_command_calls == ['acc-1']
    assert execution.last_submit_command == _SUBMIT_COMMAND_KWARGS


@pytest.mark.asyncio
async def test_submit_command_propagates_execution_errors() -> None:
    execution = _FakeExecutionManager()
    execution.submit_command_error = AccountNotRegisteredError('missing account')
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    with pytest.raises(AccountNotRegisteredError, match='missing account'):
        await trading.submit_command(**_SUBMIT_COMMAND_KWARGS)


def test_submit_abort_routes_to_execution_layer() -> None:
    execution = _FakeExecutionManager()
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    trading.submit_abort(
        TradeAbort(
            account_id='acc-1',
            command_id='cmd-1',
            reason='cancel',
            created_at=_CREATED_AT,
        )
    )

    assert execution.submit_abort_calls == ['acc-1']


def test_submit_abort_propagates_execution_errors() -> None:
    execution = _FakeExecutionManager()
    execution.submit_abort_error = AccountNotRegisteredError('missing account')
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    with pytest.raises(AccountNotRegisteredError, match='missing account'):
        trading.submit_abort(
            TradeAbort(
                account_id='acc-1',
                command_id='cmd-1',
                reason='cancel',
                created_at=_CREATED_AT,
            )
        )
