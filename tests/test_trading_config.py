from __future__ import annotations

from collections.abc import MutableMapping
from types import MappingProxyType
from typing import cast

import pytest

from praxis.infrastructure.binance_adapter import TESTNET_REST_URL, TESTNET_WS_URL
from praxis.trading_config import TradingConfig


def test_trading_config_defaults() -> None:
    cfg = TradingConfig(epoch_id=1)

    assert cfg.sqlite_path == 'praxis.sqlite3'
    assert cfg.venue_rest_url == TESTNET_REST_URL
    assert cfg.venue_ws_url == TESTNET_WS_URL
    assert cfg.account_credentials == {}
    assert isinstance(cfg.account_credentials, MappingProxyType)
    assert cfg.on_trade_outcome is None


def test_trading_config_rejects_non_positive_epoch() -> None:
    with pytest.raises(ValueError, match='epoch_id must be positive'):
        TradingConfig(epoch_id=0)


def test_trading_config_rejects_empty_sqlite_path() -> None:
    with pytest.raises(ValueError, match='sqlite_path must be non-empty'):
        TradingConfig(epoch_id=1, sqlite_path='')


def test_trading_config_rejects_empty_account_id() -> None:
    with pytest.raises(ValueError, match='keys must be non-empty'):
        TradingConfig(epoch_id=1, account_credentials={'': ('key', 'secret')})


def test_trading_config_rejects_empty_credential_parts() -> None:
    with pytest.raises(ValueError, match='values must be'):
        TradingConfig(epoch_id=1, account_credentials={'acc-1': ('', 'secret')})


def test_trading_config_copies_credentials_mapping() -> None:
    credentials = {'acc-1': ('key', 'secret')}
    cfg = TradingConfig(epoch_id=1, account_credentials=credentials)
    credentials['acc-1'] = ('changed', 'changed')

    assert cfg.account_credentials['acc-1'] == ('key', 'secret')


def test_trading_config_credential_mapping_is_read_only() -> None:
    cfg = TradingConfig(epoch_id=1, account_credentials={'acc-1': ('key', 'secret')})
    mutable = cast(MutableMapping[str, tuple[str, str]], cfg.account_credentials)

    with pytest.raises(TypeError):
        mutable['acc-2'] = ('x', 'y')
