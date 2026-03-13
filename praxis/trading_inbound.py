from __future__ import annotations

import contextlib
from collections.abc import Mapping
from typing import Protocol

__all__ = ['TradingInbound']


def _is_already_registered_error(account_id: str, error: ValueError) -> bool:
    reason = error.args[0] if error.args else str(error)
    expected = f"account_id '{account_id}' is already registered"
    return str(reason) == expected


class _ExecutionAccountRegistry(Protocol):
    def register_account(self, account_id: str) -> None: ...

    async def unregister_account(self, account_id: str) -> None: ...


class _VenueAccountRegistry(Protocol):
    def register_account(
        self,
        account_id: str,
        api_key: str,
        api_secret: str,
    ) -> None: ...

    def unregister_account(self, account_id: str) -> None: ...


class TradingInbound:
    '''
    Coordinate inbound account registration across venue and execution layers.

    Args:
        execution_manager (_ExecutionAccountRegistry): Execution account registry.
        venue_adapter (_VenueAccountRegistry): Venue credential registry.
        account_credentials (Mapping[str, tuple[str, str]]): Static account
            credential mapping keyed by account identifier.
    '''

    def __init__(
        self,
        execution_manager: _ExecutionAccountRegistry,
        venue_adapter: _VenueAccountRegistry,
        account_credentials: Mapping[str, tuple[str, str]],
    ) -> None:
        '''Store inbound dependencies and account credential configuration.'''

        self._execution_manager = execution_manager
        self._venue_adapter = venue_adapter
        self._account_credentials = dict(account_credentials)

    def register_account(self, account_id: str) -> None:
        '''
        Register account credentials and execution runtime for an account.

        Args:
            account_id (str): Account identifier.

        Raises:
            ValueError: If account_id is empty, credentials are missing,
                or execution account registration fails.
            RuntimeError: If execution account registration cannot start.

        Note:
            If execution runtime is already registered for account_id,
            registration is treated as idempotent success.
        '''

        if not account_id:
            msg = 'account_id must be a non-empty string'
            raise ValueError(msg)

        credentials = self._account_credentials.get(account_id)
        if credentials is None:
            msg = f"no credentials configured for account_id '{account_id}'"
            raise ValueError(msg)

        api_key, api_secret = credentials
        self._venue_adapter.register_account(account_id, api_key, api_secret)
        try:
            self._execution_manager.register_account(account_id)
        except (ValueError, RuntimeError) as exc:
            if isinstance(exc, ValueError) and _is_already_registered_error(
                account_id,
                exc,
            ):
                return
            with contextlib.suppress(KeyError):
                self._venue_adapter.unregister_account(account_id)
            raise

    async def unregister_account(self, account_id: str) -> None:
        '''
        Unregister execution runtime and venue credentials for an account.

        Args:
            account_id (str): Account identifier.

        Raises:
            AccountNotRegisteredError: If execution runtime is not registered.
            ValueError: If execution unregister fails for a non-registration
                reason.

        Note:
            Venue credentials are cleaned up in a finally block even when
            execution unregister raises.
        '''

        try:
            await self._execution_manager.unregister_account(account_id)
        finally:
            with contextlib.suppress(KeyError):
                self._venue_adapter.unregister_account(account_id)
