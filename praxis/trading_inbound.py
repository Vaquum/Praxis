from __future__ import annotations

import contextlib
from datetime import datetime
from collections.abc import Mapping
from decimal import Decimal
from typing import Protocol

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort

__all__ = ['TradingInbound']


class _ExecutionAccountRegistry(Protocol):
    def has_account(self, account_id: str) -> bool: ...

    def register_account(self, account_id: str) -> None: ...

    async def unregister_account(self, account_id: str) -> None: ...

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
    ) -> str: ...

    def submit_abort(self, abort: TradeAbort) -> None: ...


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
    Coordinate inbound account lifecycle and command routing.

    Handles account registration/unregistration orchestration and routes
    inbound trade commands/aborts to the execution layer.

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
            registration is treated as idempotent success based on
            execution registry state.
        '''

        if not account_id:
            msg = 'account_id must be a non-empty string'
            raise ValueError(msg)

        credentials = self._account_credentials.get(account_id)
        if credentials is None:
            msg = f"no credentials configured for account_id '{account_id}'"
            raise ValueError(msg)

        api_key, api_secret = credentials
        if self._execution_manager.has_account(account_id):
            self._venue_adapter.register_account(account_id, api_key, api_secret)
            return

        self._venue_adapter.register_account(account_id, api_key, api_secret)
        try:
            self._execution_manager.register_account(account_id)
        except (ValueError, RuntimeError):
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
            ValueError: If execution unregister fails and implementation
                raises ValueError for invalid unregister requests.

        Note:
            Venue credentials are cleaned up in a finally block even when
            execution unregister raises.
        '''

        try:
            await self._execution_manager.unregister_account(account_id)
        finally:
            with contextlib.suppress(KeyError):
                self._venue_adapter.unregister_account(account_id)

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
        '''
        Route inbound command submission to the execution layer.

        Args:
            trade_id (str): Manager correlation identifier.
            account_id (str): Target account identifier.
            symbol (str): Trading pair symbol.
            side (OrderSide): Order direction.
            qty (Decimal): Total quantity to execute.
            order_type (OrderType): Order type.
            execution_mode (ExecutionMode): Execution strategy.
            execution_params (SingleShotParams): Mode-specific parameters.
            timeout (int): Execution deadline in seconds.
            reference_price (Decimal | None): Optional reference price.
            maker_preference (MakerPreference): Maker/taker preference.
            stp_mode (STPMode): Self-trade prevention mode.
            created_at (datetime): Command creation time.

        Returns:
            str: Assigned command identifier.
        '''

        return await self._execution_manager.submit_command(
            trade_id=trade_id,
            account_id=account_id,
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            execution_mode=execution_mode,
            execution_params=execution_params,
            timeout=timeout,
            reference_price=reference_price,
            maker_preference=maker_preference,
            stp_mode=stp_mode,
            created_at=created_at,
        )

    def submit_abort(self, abort: TradeAbort) -> None:
        '''
        Route inbound abort submission to the execution layer.

        Args:
            abort (TradeAbort): Abort request targeting an existing command.
        '''

        self._execution_manager.submit_abort(abort)
