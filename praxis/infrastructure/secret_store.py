'''
Secret storage for venue API credentials.

Resolve per-account Binance credentials from a backend — the OS keyring
for live trading, an in-memory mapping for paper trading and tests —
into a frozen, redacted `Credentials` value object.

The redaction on `Credentials` closes the accidental log/`repr` surface
only. It does NOT make generic serialization safe: `dataclasses.asdict`,
`vars`, and pickling still expose the fields, so credential objects must
never be handed to a generic serializer.
'''

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import keyring
import keyring.errors

__all__ = [
    'Credentials',
    'FileSecretStore',
    'KeyringSecretStore',
    'MappingSecretStore',
    'SecretBackendError',
    'SecretNotFoundError',
    'SecretStore',
]

_KEYRING_SERVICE = 'praxis-binance'
_REDACTED = 'Credentials(api_key=<redacted>, api_secret=<redacted>)'


class SecretNotFoundError(RuntimeError):

    '''Raised when no credential record exists for an account.'''


class SecretBackendError(RuntimeError):

    '''Raised when the secret backend is unavailable or a record is malformed.'''


@dataclass(frozen=True)
class Credentials:

    '''
    Frozen venue API credentials with a redacted representation.

    Args:
        api_key (str): Venue API key.
        api_secret (str): Venue API secret.
    '''

    api_key: str
    api_secret: str

    def __post_init__(self) -> None:

        '''Validate that both fields are non-empty strings.'''

        if not isinstance(self.api_key, str) or not isinstance(self.api_secret, str):
            msg = 'Credentials api_key and api_secret must be strings'
            raise TypeError(msg)

        if not self.api_key or not self.api_secret:
            msg = 'Credentials api_key and api_secret must be non-empty'
            raise ValueError(msg)

    def __repr__(self) -> str:

        '''Return a redacted representation that never exposes the secret.'''

        return _REDACTED

    def __str__(self) -> str:

        '''Return a redacted representation that never exposes the secret.'''

        return _REDACTED


@runtime_checkable
class SecretStore(Protocol):

    '''Resolve per-account credentials, raising when a record is absent.'''

    def get(self, account_id: str) -> Credentials:

        '''
        Return credentials for an account.

        Args:
            account_id (str): Account identifier.

        Returns:
            Credentials: The account's resolved credentials.

        Raises:
            SecretNotFoundError: If no record exists for the account.
            SecretBackendError: If the backend is unavailable or the
                record is malformed.
        '''

        ...


def _decode_record(account_id: str, raw: str) -> Credentials:

    '''
    Decode a stored JSON credential record into `Credentials`.

    Args:
        account_id (str): Account identifier, for error messages only.
        raw (str): Serialized `{"api_key": ..., "api_secret": ...}` record.

    Returns:
        Credentials: The decoded credentials.

    Raises:
        SecretBackendError: If the record is not valid JSON, not an
            object, or is missing a non-empty api_key/api_secret string.
    '''

    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f'malformed credential record for account {account_id!r}'
        raise SecretBackendError(msg) from exc

    return _credentials_from_record(account_id, record)


def _credentials_from_record(account_id: str, record: object) -> Credentials:

    '''
    Validate a decoded credential mapping into `Credentials`.

    Args:
        account_id (str): Account identifier, for error messages only.
        record (object): Decoded record, expected to be a mapping with
            `api_key` and `api_secret`.

    Returns:
        Credentials: The validated credentials.

    Raises:
        SecretBackendError: If the record is not an object or is missing a
            non-empty api_key/api_secret string.
    '''

    if not isinstance(record, dict):
        msg = f'malformed credential record for account {account_id!r}'
        raise SecretBackendError(msg)

    api_key = record.get('api_key')
    api_secret = record.get('api_secret')
    if (
        not isinstance(api_key, str)
        or not isinstance(api_secret, str)
        or not api_key
        or not api_secret
    ):
        msg = f'incomplete credential record for account {account_id!r}'
        raise SecretBackendError(msg)

    return Credentials(api_key=api_key, api_secret=api_secret)


class KeyringSecretStore:

    '''
    Resolve credentials from the OS keyring (live trading).

    One record per account under service `praxis-binance`, username
    `account_id`, holding a JSON object with `api_key` and `api_secret`.
    Provisioning is out of band (the operator writes records via the
    `keyring` CLI); this store is read-only.
    '''

    def get(self, account_id: str) -> Credentials:

        '''
        Resolve an account's credentials from the keyring.

        Args:
            account_id (str): Account identifier.

        Returns:
            Credentials: The resolved credentials.

        Raises:
            SecretNotFoundError: If the keyring has no record for the account.
            SecretBackendError: If the keyring is unavailable or the
                record is malformed.
        '''

        try:
            raw = keyring.get_password(_KEYRING_SERVICE, account_id)
        except keyring.errors.KeyringError as exc:
            msg = f'keyring backend unavailable for account {account_id!r}'
            raise SecretBackendError(msg) from exc

        if raw is None:
            msg = f'no keyring credential record for account {account_id!r}'
            raise SecretNotFoundError(msg)

        return _decode_record(account_id, raw)


class MappingSecretStore:

    '''
    Resolve credentials from an in-memory mapping (paper trading and tests).

    Args:
        credentials (Mapping[str, Credentials]): Account-keyed credentials.
    '''

    def __init__(self, credentials: Mapping[str, Credentials]) -> None:

        '''Store a copy of the credential mapping.'''

        self._credentials = dict(credentials)

    def get(self, account_id: str) -> Credentials:

        '''
        Resolve an account's credentials from the mapping.

        Args:
            account_id (str): Account identifier.

        Returns:
            Credentials: The resolved credentials.

        Raises:
            SecretNotFoundError: If the mapping has no record for the account.
        '''

        try:
            return self._credentials[account_id]
        except KeyError as exc:
            msg = f'no credential record for account {account_id!r}'
            raise SecretNotFoundError(msg) from exc


class FileSecretStore:

    '''
    Resolve credentials from a JSON secrets file (headless live trading).

    The file holds a JSON object mapping `account_id` to a
    `{"api_key": ..., "api_secret": ...}` record. It is intended for a
    container or orchestrator secret mounted at a fixed path where an OS
    keyring is unavailable. Provisioning is out of band; this store is
    read-only and loads the file once on first access.

    Args:
        path (Path): Path to the JSON secrets file.
    '''

    def __init__(self, path: Path) -> None:

        '''Record the secrets-file path without reading it.'''

        self._path = path
        self._records: dict[str, Credentials] | None = None

    def _load(self) -> dict[str, Credentials]:

        '''
        Read and validate the secrets file, caching the parsed records.

        Returns:
            dict[str, Credentials]: Account-keyed credentials.

        Raises:
            SecretBackendError: If the file is unreadable, is not valid
                JSON, is not a JSON object, or holds a malformed record.
        '''

        if self._records is not None:
            return self._records

        try:
            raw = self._path.read_text()
        except OSError as exc:
            msg = f'secrets file unreadable at {self._path}'
            raise SecretBackendError(msg) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            msg = f'secrets file is not valid JSON at {self._path}'
            raise SecretBackendError(msg) from exc

        if not isinstance(data, dict):
            msg = f'secrets file must be a JSON object at {self._path}'
            raise SecretBackendError(msg)

        records = {
            account_id: _credentials_from_record(account_id, record)
            for account_id, record in data.items()
        }
        self._records = records

        return records

    def get(self, account_id: str) -> Credentials:

        '''
        Resolve an account's credentials from the secrets file.

        Args:
            account_id (str): Account identifier.

        Returns:
            Credentials: The resolved credentials.

        Raises:
            SecretNotFoundError: If the file has no record for the account.
            SecretBackendError: If the file is unreadable or malformed.
        '''

        records = self._load()
        try:
            return records[account_id]
        except KeyError as exc:
            msg = f'no credential record for account {account_id!r}'
            raise SecretNotFoundError(msg) from exc
