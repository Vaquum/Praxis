'''
Tests for praxis.infrastructure.secret_store.
'''

from __future__ import annotations

import json

import keyring
import keyring.errors
import pytest

from praxis.infrastructure.secret_store import (
    Credentials,
    KeyringSecretStore,
    MappingSecretStore,
    SecretBackendError,
    SecretNotFoundError,
    SecretStore,
)
from praxis.trading_config import TradingConfig

_ACCT = 'acc-1'
_API_KEY = 'the-secret-api-key'
_API_SECRET = 'the-secret-api-secret'


def test_credentials_repr_and_str_are_redacted() -> None:
    creds = Credentials(api_key=_API_KEY, api_secret=_API_SECRET)

    for rendered in (repr(creds), str(creds), f'{creds}'):
        assert '<redacted>' in rendered
        assert _API_KEY not in rendered
        assert _API_SECRET not in rendered


def test_credentials_redacted_inside_containers() -> None:
    creds = Credentials(api_key=_API_KEY, api_secret=_API_SECRET)

    assert _API_SECRET not in repr({_ACCT: creds})

    config = TradingConfig(epoch_id=1, account_credentials={_ACCT: creds})
    assert _API_KEY not in repr(config)
    assert _API_SECRET not in repr(config)


def test_credentials_rejects_non_string_fields() -> None:
    with pytest.raises(TypeError):
        Credentials(api_key=123, api_secret='s')  # type: ignore[arg-type]


def test_credentials_rejects_empty_fields() -> None:
    with pytest.raises(ValueError, match='non-empty'):
        Credentials(api_key='', api_secret='s')


def test_credentials_equality() -> None:
    assert Credentials(api_key='k', api_secret='s') == Credentials(api_key='k', api_secret='s')
    assert Credentials(api_key='k', api_secret='s') != Credentials(api_key='k', api_secret='x')


def test_mapping_store_returns_credentials() -> None:
    creds = Credentials(api_key=_API_KEY, api_secret=_API_SECRET)
    store = MappingSecretStore({_ACCT: creds})

    assert store.get(_ACCT) == creds


def test_mapping_store_missing_raises_not_found() -> None:
    store = MappingSecretStore({})

    with pytest.raises(SecretNotFoundError):
        store.get(_ACCT)


def test_stores_satisfy_protocol() -> None:
    assert isinstance(MappingSecretStore({}), SecretStore)
    assert isinstance(KeyringSecretStore(), SecretStore)


def test_keyring_store_returns_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    record = json.dumps({'api_key': _API_KEY, 'api_secret': _API_SECRET})

    def _fake_get(service: str, username: str) -> str:
        assert service == 'praxis-binance'
        assert username == _ACCT
        return record

    monkeypatch.setattr(keyring, 'get_password', _fake_get)

    assert KeyringSecretStore().get(_ACCT) == Credentials(
        api_key=_API_KEY,
        api_secret=_API_SECRET,
    )


def test_keyring_store_missing_record_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keyring, 'get_password', lambda *_: None)

    with pytest.raises(SecretNotFoundError):
        KeyringSecretStore().get(_ACCT)


def test_keyring_store_backend_error_raises_backend_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_: str) -> str:
        raise keyring.errors.KeyringError('backend down')

    monkeypatch.setattr(keyring, 'get_password', _boom)

    with pytest.raises(SecretBackendError):
        KeyringSecretStore().get(_ACCT)


def test_keyring_store_malformed_json_raises_backend_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keyring, 'get_password', lambda *_: 'not-json')

    with pytest.raises(SecretBackendError):
        KeyringSecretStore().get(_ACCT)


def test_keyring_store_non_object_json_raises_backend_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keyring, 'get_password', lambda *_: '["a", "b"]')

    with pytest.raises(SecretBackendError):
        KeyringSecretStore().get(_ACCT)


def test_keyring_store_incomplete_record_raises_backend_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = json.dumps({'api_key': _API_KEY})
    monkeypatch.setattr(keyring, 'get_password', lambda *_: record)

    with pytest.raises(SecretBackendError):
        KeyringSecretStore().get(_ACCT)


def test_keyring_store_empty_field_raises_backend_error(monkeypatch: pytest.MonkeyPatch) -> None:
    record = json.dumps({'api_key': '', 'api_secret': _API_SECRET})
    monkeypatch.setattr(keyring, 'get_password', lambda *_: record)

    with pytest.raises(SecretBackendError):
        KeyringSecretStore().get(_ACCT)
