from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from praxis.core.domain.enums import BracketProtectionFailureResponse, ExecutionMode
from praxis.core.domain.events import FundTransaction, ReconciliationMismatch
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.infrastructure.binance_urls import (
    TESTNET_REST_URL,
    TESTNET_WS_API_URL,
    TESTNET_WS_URL,
)
from praxis.infrastructure.secret_store import Credentials

__all__ = ['TradingConfig']


@dataclass(frozen=True)
class TradingConfig:
    '''
    Runtime wiring configuration for the MMVP Trading orchestrator.

    Args:
        epoch_id (int): Event epoch identifier used for Event Spine appends.
        venue_rest_url (str): Venue REST base URL.
        venue_ws_url (str): Venue WebSocket stream base URL (market data).
        venue_ws_api_url (str): Venue WebSocket API base URL (signed requests
            and user-data-stream subscription).
        account_credentials (Mapping[str, Credentials]): Mapping of account_id
            to resolved venue Credentials.
        on_trade_outcome (Callable[[TradeOutcome], Awaitable[None]] | None):
            Optional async callback invoked by execution outcomes.
        on_fund_transaction (Callable[[FundTransaction], Awaitable[None]] | None):
            Optional callback invoked by the reconciliation engine after a
            fund transaction is durably appended to the Event Spine. The
            launcher wires it to push the transaction to Nexus.
        on_reconciliation_mismatch
            (Callable[[ReconciliationMismatch], Awaitable[None]] | None):
            Optional callback invoked by the reconciliation engine after a
            per-asset balance mismatch is appended to the Event Spine. The
            launcher wires it to push the mismatch to Nexus.
        shutdown_timeout (float): Seconds to wait for orders to reach terminal
            state during shutdown. Default: 30.0.
        reconcile_interval_seconds (float): Seconds between background
            reconciliation cycles (fund-transaction polling). Default: 60.0.
        enabled_execution_modes (frozenset[ExecutionMode]): Execution modes the
            host may drive. Default-off: only SINGLE_SHOT is enabled unless a
            mode is explicitly added, so a new mode cannot be driven live until
            it is turned on for the deployment. SINGLE_SHOT is always unioned in
            at construction, so the stored set always includes it.
        bracket_protection_failure_response (BracketProtectionFailureResponse):
            How the account reacts when a bracket protective-OCO amend leaves
            the position naked. Default FLATTEN_THEN_HALT (fail-safe);
            REDUCE_ONLY is a supervised override.
    '''

    epoch_id: int
    venue_rest_url: str = TESTNET_REST_URL
    venue_ws_url: str = TESTNET_WS_URL
    venue_ws_api_url: str = TESTNET_WS_API_URL
    account_credentials: Mapping[str, Credentials] = field(default_factory=dict)
    on_trade_outcome: Callable[[TradeOutcome], Awaitable[None]] | None = None
    on_fund_transaction: (
        Callable[[FundTransaction], None]
        | Callable[[FundTransaction], Awaitable[None]]
        | None
    ) = None
    on_reconciliation_mismatch: (
        Callable[[ReconciliationMismatch], None]
        | Callable[[ReconciliationMismatch], Awaitable[None]]
        | None
    ) = None
    shutdown_timeout: float = 30.0
    reconcile_interval_seconds: float = 60.0
    enabled_execution_modes: frozenset[ExecutionMode] = field(
        default_factory=lambda: frozenset({ExecutionMode.SINGLE_SHOT}),
    )
    bracket_protection_failure_response: BracketProtectionFailureResponse = (
        BracketProtectionFailureResponse.FLATTEN_THEN_HALT
    )

    def __post_init__(self) -> None:
        '''Validate runtime configuration invariants.'''

        if self.epoch_id <= 0:
            msg = 'TradingConfig.epoch_id must be positive'
            raise ValueError(msg)

        if not self.venue_rest_url:
            msg = 'TradingConfig.venue_rest_url must be non-empty'
            raise ValueError(msg)

        if not self.venue_ws_url:
            msg = 'TradingConfig.venue_ws_url must be non-empty'
            raise ValueError(msg)

        if not self.venue_ws_api_url:
            msg = 'TradingConfig.venue_ws_api_url must be non-empty'
            raise ValueError(msg)

        if self.shutdown_timeout <= 0:
            msg = 'TradingConfig.shutdown_timeout must be positive'
            raise ValueError(msg)

        credentials_copy = dict(self.account_credentials)
        for account_id, credentials in credentials_copy.items():
            if not isinstance(account_id, str) or not account_id.strip():
                msg = 'TradingConfig.account_credentials keys must be non-empty strings'
                raise ValueError(msg)

            if not isinstance(credentials, Credentials):
                msg = 'TradingConfig.account_credentials values must be Credentials'
                raise ValueError(msg)

            if not credentials.api_key or not credentials.api_secret:
                msg = (
                    'TradingConfig.account_credentials Credentials must have '
                    'a non-empty api_key and api_secret'
                )
                raise ValueError(msg)

        object.__setattr__(
            self,
            'account_credentials',
            MappingProxyType(credentials_copy),
        )

        for mode in self.enabled_execution_modes:
            if not isinstance(mode, ExecutionMode):
                msg = 'TradingConfig.enabled_execution_modes entries must be ExecutionMode'
                raise ValueError(msg)

        object.__setattr__(
            self,
            'enabled_execution_modes',
            frozenset(self.enabled_execution_modes) | {ExecutionMode.SINGLE_SHOT},
        )

        if not isinstance(
            self.bracket_protection_failure_response, BracketProtectionFailureResponse,
        ):
            msg = (
                'TradingConfig.bracket_protection_failure_response must be a '
                'BracketProtectionFailureResponse'
            )
            raise ValueError(msg)
