from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import cast

from praxis.core.execution_manager import ExecutionManager
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.position import Position
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.trading_config import TradingConfig
from praxis.trading_inbound import TradingInbound

__all__ = ['Trading']


class Trading:
    '''
    Main trading composition root for MMVP wiring.

    Wires venue adapter, execution manager, and inbound facade into a single
    manager-facing object with MMVP lifecycle supervision (`start`/`stop`).

    Args:
        config (TradingConfig): Runtime wiring configuration.
        event_spine (EventSpine): Event Spine instance to use.
        venue_adapter (VenueAdapter | None): Optional injected venue adapter.
            If omitted, a BinanceAdapter is created from config URLs.
    '''

    def __init__(
        self,
        *,
        config: TradingConfig,
        event_spine: EventSpine,
        venue_adapter: VenueAdapter | None = None,
    ) -> None:
        '''Compose core trading dependencies and manager-facing facade.'''

        self._config = config
        self._event_spine = event_spine
        if venue_adapter is None:
            self._venue_adapter = cast(
                VenueAdapter,
                BinanceAdapter(
                    base_url=config.venue_rest_url,
                    ws_base_url=config.venue_ws_url,
                    credentials=dict(config.account_credentials),
                ),
            )
        else:
            self._venue_adapter = venue_adapter
        self._execution_manager = ExecutionManager(
            event_spine=event_spine,
            epoch_id=config.epoch_id,
            venue_adapter=self._venue_adapter,
            on_trade_outcome=config.on_trade_outcome,
        )
        self._inbound = TradingInbound(
            execution_manager=self._execution_manager,
            venue_adapter=self._venue_adapter,
            account_credentials=config.account_credentials,
        )
        self._started = False
        self._managed_accounts: set[str] = set()

    @property
    def config(self) -> TradingConfig:
        '''Runtime wiring configuration for this trading instance.'''

        return self._config

    @property
    def event_spine(self) -> EventSpine:
        '''Event Spine used by this trading instance.'''

        return self._event_spine

    @property
    def venue_adapter(self) -> VenueAdapter:
        '''Venue adapter wired for this trading instance.'''

        return self._venue_adapter

    @property
    def execution_manager(self) -> ExecutionManager:
        '''Execution manager wired for this trading instance.'''

        return self._execution_manager

    @property
    def started(self) -> bool:
        '''Whether the trading runtime has been started.'''

        return self._started

    async def start(self) -> None:
        '''Initialize runtime prerequisites for facade operations.'''

        if self._started:
            return

        await self._event_spine.ensure_schema()
        self._started = True

    async def stop(self) -> None:
        '''Stop runtime and cleanup managed account registrations.'''

        if not self._started:
            return

        first_error: Exception | None = None
        for account_id in sorted(self._managed_accounts):
            try:
                await self._inbound.unregister_account(account_id)
                self._managed_accounts.discard(account_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                if first_error is None:
                    first_error = exc

        if first_error is not None:
            raise first_error

        self._started = False

    def _require_started(self) -> None:
        if not self._started:
            msg = 'Trading.start() must be awaited before using trading operations'
            raise RuntimeError(msg)

    def register_account(self, account_id: str) -> None:
        '''Register account in venue + execution via inbound facade.'''

        self._require_started()
        self._inbound.register_account(account_id)
        self._managed_accounts.add(account_id)

    async def unregister_account(self, account_id: str) -> None:
        '''Unregister account in execution + venue via inbound facade.'''

        self._require_started()
        await self._inbound.unregister_account(account_id)
        self._managed_accounts.discard(account_id)

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
        '''Submit trade command through inbound facade.'''

        self._require_started()
        return await self._inbound.submit_command(
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
        '''Submit trade abort through inbound facade.'''

        self._require_started()
        self._inbound.submit_abort(abort)

    def pull_positions(self, account_id: str) -> dict[tuple[str, str], Position]:
        '''Pull detached positions snapshot through inbound facade.'''

        self._require_started()
        return self._inbound.pull_positions(account_id)
