from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.infrastructure.binance_adapter import TESTNET_REST_URL, TESTNET_WS_URL

__all__ = ['TradingConfig']

_CREDENTIAL_PARTS = 2


@dataclass(frozen=True)
class TradingConfig:
    '''
    Runtime wiring configuration for the MMVP Trading orchestrator.

    Args:
        epoch_id (int): Event epoch identifier used for Event Spine appends.
        venue_rest_url (str): Venue REST base URL.
        venue_ws_url (str): Venue WebSocket base URL.
        account_credentials (Mapping[str, tuple[str, str]]): Mapping of account_id
            to (api_key, api_secret).
        on_trade_outcome (Callable[[TradeOutcome], Awaitable[None]] | None):
            Optional async callback invoked by execution outcomes.
    '''

    epoch_id: int
    venue_rest_url: str = TESTNET_REST_URL
    venue_ws_url: str = TESTNET_WS_URL
    account_credentials: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    on_trade_outcome: Callable[[TradeOutcome], Awaitable[None]] | None = None

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

        credentials_copy = dict(self.account_credentials)
        for account_id, credentials in credentials_copy.items():
            if not account_id:
                msg = 'TradingConfig.account_credentials keys must be non-empty'
                raise ValueError(msg)

            if (
                not isinstance(credentials, tuple)
                or len(credentials) != _CREDENTIAL_PARTS
            ):
                msg = (
                    'TradingConfig.account_credentials values must be '
                    '(api_key, api_secret) with non-empty strings'
                )
                raise ValueError(msg)

            api_key, api_secret = credentials
            if not isinstance(api_key, str) or not isinstance(api_secret, str):
                msg = (
                    'TradingConfig.account_credentials values must be '
                    '(api_key, api_secret) with non-empty strings'
                )
                raise ValueError(msg)

            if not api_key or not api_secret:
                msg = (
                    'TradingConfig.account_credentials values must be '
                    '(api_key, api_secret) with non-empty strings'
                )
                raise ValueError(msg)

        object.__setattr__(
            self,
            'account_credentials',
            MappingProxyType(credentials_copy),
        )
