from __future__ import annotations

import pytest

from praxis.trading_inbound import TradingInbound


class _FakeExecutionManager:
    def __init__(self) -> None:
        self.registered: list[str] = []
        self.unregistered: list[str] = []
        self.register_error: Exception | None = None
        self.unregister_error: Exception | None = None

    def register_account(self, account_id: str) -> None:
        if self.register_error is not None:
            raise self.register_error
        self.registered.append(account_id)

    async def unregister_account(self, account_id: str) -> None:
        if self.unregister_error is not None:
            raise self.unregister_error
        self.unregistered.append(account_id)


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
    execution.register_error = ValueError("account_id 'acc-1' is already registered")
    venue = _FakeVenueAdapter()
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    trading.register_account('acc-1')

    assert venue.credentials['acc-1'] == ('key-1', 'secret-1')


@pytest.mark.asyncio
async def test_unregister_account_removes_runtime_and_credentials() -> None:
    execution = _FakeExecutionManager()
    venue = _FakeVenueAdapter()
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
    venue.register_account('acc-1', 'key-1', 'secret-1')
    trading = TradingInbound(
        execution_manager=execution,
        venue_adapter=venue,
        account_credentials={'acc-1': ('key-1', 'secret-1')},
    )

    with pytest.raises(ValueError, match='account missing'):
        await trading.unregister_account('acc-1')

    assert 'acc-1' not in venue.credentials
