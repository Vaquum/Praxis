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
from nexus.core.domain.bracket_protection_failure_response import (
    BracketProtectionFailureResponse,
)

from praxis.core.domain.enums import ExecutionMode
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
    assert cfg.enabled_execution_modes == frozenset({ExecutionMode.SINGLE_SHOT})
    assert cfg.bracket_protection_failure_response == {}
    assert isinstance(cfg.bracket_protection_failure_response, MappingProxyType)


def test_trading_config_accepts_per_account_protection_response() -> None:
    cfg = TradingConfig(
        epoch_id=1,
        bracket_protection_failure_response={
            'acct-1': BracketProtectionFailureResponse.REDUCE_ONLY,
        },
    )

    assert (
        cfg.bracket_protection_failure_response['acct-1']
        is BracketProtectionFailureResponse.REDUCE_ONLY
    )
    assert isinstance(cfg.bracket_protection_failure_response, MappingProxyType)


def test_trading_config_rejects_non_enum_protection_response() -> None:
    with pytest.raises(ValueError, match='bracket_protection_failure_response'):
        TradingConfig(
            epoch_id=1,
            bracket_protection_failure_response={'acct-1': 'FLATTEN'},  # type: ignore[dict-item]
        )


def test_trading_config_rejects_empty_protection_response_key() -> None:
    with pytest.raises(ValueError, match='bracket_protection_failure_response keys'):
        TradingConfig(
            epoch_id=1,
            bracket_protection_failure_response={
                '': BracketProtectionFailureResponse.REDUCE_ONLY,
            },
        )


def test_trading_config_rejects_whitespace_protection_response_key() -> None:
    with pytest.raises(ValueError, match='bracket_protection_failure_response keys'):
        TradingConfig(
            epoch_id=1,
            bracket_protection_failure_response={
                '   ': BracketProtectionFailureResponse.REDUCE_ONLY,
            },
        )


def test_trading_config_copies_protection_response_mapping() -> None:
    responses = {'acct-1': BracketProtectionFailureResponse.REDUCE_ONLY}
    cfg = TradingConfig(epoch_id=1, bracket_protection_failure_response=responses)
    responses['acct-1'] = BracketProtectionFailureResponse.FLATTEN_THEN_HALT

    assert (
        cfg.bracket_protection_failure_response['acct-1']
        is BracketProtectionFailureResponse.REDUCE_ONLY
    )


def test_trading_config_protection_response_mapping_is_read_only() -> None:
    cfg = TradingConfig(
        epoch_id=1,
        bracket_protection_failure_response={
            'acct-1': BracketProtectionFailureResponse.REDUCE_ONLY,
        },
    )
    mutable = cast(
        MutableMapping[str, BracketProtectionFailureResponse],
        cfg.bracket_protection_failure_response,
    )

    with pytest.raises(TypeError):
        mutable['acct-2'] = BracketProtectionFailureResponse.FLATTEN_THEN_HALT


def test_response_for_returns_configured_account_policy() -> None:
    cfg = TradingConfig(
        epoch_id=1,
        bracket_protection_failure_response={
            'acct-1': BracketProtectionFailureResponse.REDUCE_ONLY,
        },
    )

    assert (
        cfg.response_for('acct-1')
        is BracketProtectionFailureResponse.REDUCE_ONLY
    )


def test_response_for_absent_account_falls_back_to_flatten_then_halt() -> None:
    cfg = TradingConfig(
        epoch_id=1,
        bracket_protection_failure_response={
            'acct-1': BracketProtectionFailureResponse.REDUCE_ONLY,
        },
    )

    assert (
        cfg.response_for('acct-unknown')
        is BracketProtectionFailureResponse.FLATTEN_THEN_HALT
    )


def test_response_for_empty_config_falls_back_to_flatten_then_halt() -> None:
    cfg = TradingConfig(epoch_id=1)

    assert (
        cfg.response_for('acct-1')
        is BracketProtectionFailureResponse.FLATTEN_THEN_HALT
    )


def test_trading_config_enabled_modes_are_frozen() -> None:
    cfg = TradingConfig(
        epoch_id=1,
        enabled_execution_modes=frozenset(
            {ExecutionMode.SINGLE_SHOT, ExecutionMode.TWAP},
        ),
    )

    assert ExecutionMode.TWAP in cfg.enabled_execution_modes
    assert isinstance(cfg.enabled_execution_modes, frozenset)


def test_trading_config_rejects_non_execution_mode_entry() -> None:
    with pytest.raises(ValueError, match='enabled_execution_modes'):
        TradingConfig(epoch_id=1, enabled_execution_modes=frozenset({'TWAP'}))  # type: ignore[arg-type]


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
