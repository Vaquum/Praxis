from __future__ import annotations

from collections.abc import MutableMapping
from types import MappingProxyType
from typing import cast

import pytest

from praxis.infrastructure.binance_urls import (
    TESTNET_REST_URL,
    TESTNET_WS_API_URL,
    TESTNET_WS_URL,
)
from praxis.infrastructure.secret_store import Credentials
from praxis.trading_config import TradingConfig


def test_trading_config_defaults() -> None:
    cfg = TradingConfig(epoch_id=1)

    assert cfg.venue_rest_url == TESTNET_REST_URL
    assert cfg.venue_ws_url == TESTNET_WS_URL
    assert cfg.venue_ws_api_url == TESTNET_WS_API_URL
    assert cfg.account_credentials == {}
    assert isinstance(cfg.account_credentials, MappingProxyType)
    assert cfg.on_trade_outcome is None


def test_trading_config_rejects_empty_venue_rest_url() -> None:
    with pytest.raises(ValueError, match='venue_rest_url must be non-empty'):
        TradingConfig(epoch_id=1, venue_rest_url='')


def test_trading_config_rejects_empty_venue_ws_url() -> None:
    with pytest.raises(ValueError, match='venue_ws_url must be non-empty'):
        TradingConfig(epoch_id=1, venue_ws_url='')


def test_trading_config_rejects_empty_venue_ws_api_url() -> None:
    with pytest.raises(ValueError, match='venue_ws_api_url must be non-empty'):
        TradingConfig(epoch_id=1, venue_ws_api_url='')


def test_trading_config_rejects_non_positive_epoch() -> None:
    with pytest.raises(ValueError, match='epoch_id must be positive'):
        TradingConfig(epoch_id=0)


def test_trading_config_rejects_empty_account_id() -> None:
    with pytest.raises(ValueError, match='keys must be non-empty'):
        TradingConfig(
            epoch_id=1,
            account_credentials={'': Credentials(api_key='key', api_secret='secret')},
        )


def test_trading_config_rejects_non_string_account_id() -> None:
    malformed = cast(
        MutableMapping[str, Credentials],
        {1: Credentials(api_key='key', api_secret='secret')},
    )

    with pytest.raises(ValueError, match='keys must be non-empty'):
        TradingConfig(epoch_id=1, account_credentials=malformed)


def test_trading_config_rejects_whitespace_account_id() -> None:
    with pytest.raises(ValueError, match='keys must be non-empty'):
        TradingConfig(
            epoch_id=1,
            account_credentials={'   ': Credentials(api_key='key', api_secret='secret')},
        )


def test_trading_config_rejects_empty_credential_parts() -> None:
    with pytest.raises(ValueError, match='non-empty'):
        TradingConfig(
            epoch_id=1,
            account_credentials={'acc-1': Credentials(api_key='', api_secret='secret')},
        )


def test_trading_config_rejects_non_credentials_value() -> None:
    malformed = cast(MutableMapping[str, Credentials], {'acc-1': ('key', 'secret')})

    with pytest.raises(ValueError, match='must be Credentials'):
        TradingConfig(epoch_id=1, account_credentials=malformed)


def test_trading_config_copies_credentials_mapping() -> None:
    credentials = {'acc-1': Credentials(api_key='key', api_secret='secret')}
    cfg = TradingConfig(epoch_id=1, account_credentials=credentials)
    credentials['acc-1'] = Credentials(api_key='changed', api_secret='changed')

    assert cfg.account_credentials['acc-1'] == Credentials(api_key='key', api_secret='secret')


def test_trading_config_credential_mapping_is_read_only() -> None:
    cfg = TradingConfig(
        epoch_id=1,
        account_credentials={'acc-1': Credentials(api_key='key', api_secret='secret')},
    )
    mutable = cast(MutableMapping[str, Credentials], cfg.account_credentials)

    with pytest.raises(TypeError):
        mutable['acc-2'] = Credentials(api_key='x', api_secret='y')
