'''Tests for the boot-time API-key permission assertion (B2).'''

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from praxis.infrastructure.secret_store import Credentials
from praxis.infrastructure.venue_adapter import ApiPermissions, AuthenticationError
from praxis.launcher import InstanceConfig, Launcher
from praxis.trading_config import TradingConfig

_ACCT = 'acc-1'


def _instance(account_id: str) -> InstanceConfig:
    return InstanceConfig(
        account_id=account_id,
        manifest_path=Path('manifest.yaml'),
        strategies_base_path=Path('strategies'),
        state_dir=Path('state'),
    )


def _launcher(*, enforce: bool, instances: list[InstanceConfig]) -> Launcher:
    config = TradingConfig(
        epoch_id=1,
        account_credentials={
            inst.account_id: Credentials(api_key='k', api_secret='s')
            for inst in instances
        },
    )

    return Launcher(
        trading_config=config,
        instances=instances,
        event_spine=Mock(),
        enforce_api_permissions=enforce,
    )


def _wire_trading(
    launcher: Launcher,
    *,
    return_value: object | None = None,
    side_effect: object | None = None,
) -> Mock:
    trading = Mock()
    trading.venue_adapter.query_api_permissions = AsyncMock(
        return_value=return_value,
        side_effect=side_effect,
    )
    trading.stop = AsyncMock()
    launcher._trading = trading

    return trading


@pytest.mark.asyncio
async def test_trade_only_key_passes() -> None:
    launcher = _launcher(enforce=True, instances=[_instance(_ACCT)])
    trading = _wire_trading(
        launcher,
        return_value=ApiPermissions(
            enable_withdrawals=False,
            enable_spot_and_margin_trading=True,
        ),
    )

    await launcher._verify_api_permissions()

    trading.stop.assert_not_called()


@pytest.mark.asyncio
async def test_withdrawal_enabled_key_aborts() -> None:
    launcher = _launcher(enforce=True, instances=[_instance(_ACCT)])
    trading = _wire_trading(
        launcher,
        return_value=ApiPermissions(
            enable_withdrawals=True,
            enable_spot_and_margin_trading=True,
        ),
    )

    with pytest.raises(RuntimeError, match='withdrawals'):
        await launcher._verify_api_permissions()

    trading.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_trading_key_aborts() -> None:
    launcher = _launcher(enforce=True, instances=[_instance(_ACCT)])
    trading = _wire_trading(
        launcher,
        return_value=ApiPermissions(
            enable_withdrawals=False,
            enable_spot_and_margin_trading=False,
        ),
    )

    with pytest.raises(RuntimeError, match='trade'):
        await launcher._verify_api_permissions()

    trading.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_error_aborts() -> None:
    launcher = _launcher(enforce=True, instances=[_instance(_ACCT)])
    trading = _wire_trading(launcher, side_effect=AuthenticationError('bad key'))

    with pytest.raises(AuthenticationError):
        await launcher._verify_api_permissions()

    trading.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_unexpected_error_aborts_fail_closed() -> None:
    launcher = _launcher(enforce=True, instances=[_instance(_ACCT)])
    trading = _wire_trading(launcher, side_effect=ValueError('surprise'))

    with pytest.raises(ValueError, match='surprise'):
        await launcher._verify_api_permissions()

    trading.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_query_timeout_aborts_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher = _launcher(enforce=True, instances=[_instance(_ACCT)])

    async def _hang(_account_id: str) -> object:
        await asyncio.sleep(10)
        return None

    trading = Mock()
    trading.venue_adapter.query_api_permissions = _hang
    trading.stop = AsyncMock()
    launcher._trading = trading
    monkeypatch.setattr('praxis.launcher._PERMISSION_QUERY_TIMEOUT', 0.05)

    with pytest.raises(TimeoutError):
        await launcher._verify_api_permissions()

    trading.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_partial_failure_across_accounts_aborts() -> None:
    launcher = _launcher(
        enforce=True,
        instances=[_instance('acc-1'), _instance('acc-2')],
    )
    trading = _wire_trading(
        launcher,
        side_effect=[
            ApiPermissions(enable_withdrawals=False, enable_spot_and_margin_trading=True),
            ApiPermissions(enable_withdrawals=True, enable_spot_and_margin_trading=True),
        ],
    )

    with pytest.raises(RuntimeError, match='withdrawals'):
        await launcher._verify_api_permissions()

    trading.stop.assert_awaited_once()


def test_paper_mode_skips_assertion() -> None:
    launcher = _launcher(enforce=False, instances=[_instance(_ACCT)])

    launcher._assert_api_permissions()
