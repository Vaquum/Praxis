'''Process launcher for Praxis + Nexus + Limen.

Single entry point that starts the Trading service, market data poller,
and one Nexus Manager thread per account.
'''

from __future__ import annotations

import asyncio
import logging
import math
import os
import queue
import re
import signal
import sys
import threading
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiosqlite
import polars as pl
from aiohttp import web
from binance.client import Client

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.enums import OperationalMode, OrderSide
from praxis.core.domain.enums import OrderType
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.position import Position
from nexus.core.health_evaluator import HealthEvaluator, HealthThresholds
from nexus.core.health_loop import HealthLoop
from nexus.core.mtm_loop import MtmLoop
from nexus.core.outcome_loop import OutcomeLoop
from nexus.core.stp_mode import STPMode
from nexus.core.validator import (
    HealthStagePolicy,
    HealthStageSnapshot,
    PlatformLimitsStageLimits,
    PlatformLimitsStageSnapshot,
    PriceCheckSnapshot,
    RiskStageLimits,
    StageValidator,
    ValidationAction,
    ValidationDecision,
    ValidationPipeline,
    ValidationRequestContext,
    ValidationStage,
    build_default_intake_hooks,
    build_price_stage_limits_from_config,
    validate_capital_stage,
    validate_health_stage,
    validate_intake_stage,
    validate_platform_limits_stage,
    validate_price_stage,
    validate_risk_stage,
)
from nexus.infrastructure.manifest import Manifest, load_manifest
from nexus.infrastructure.praxis_connector.order_context import OrderContext
from nexus.infrastructure.praxis_connector.outcome_processor import OutcomeProcessor
from nexus.infrastructure.praxis_connector.praxis_inbound import PraxisInbound
from nexus.infrastructure.praxis_connector.praxis_outbound import PraxisOutbound
from nexus.infrastructure.snapshot_scheduler import SnapshotScheduler
from nexus.infrastructure.praxis_connector.trade_outcome import (
    TradeOutcome as NexusTradeOutcome,
)
from nexus.infrastructure.state_store import StateStore
from nexus.instance_config import InstanceConfig as NexusInstanceConfig
from nexus.startup.sequencer import StartupSequencer
from nexus.startup.shutdown_sequencer import ShutdownSequencer
from nexus.strategy.action import Action, ActionType
from nexus.strategy.action_submit import SubmissionStatus, submit_actions
from nexus.strategy.context import StrategyContext
from nexus.strategy.predict_loop import PredictLoop
from nexus.strategy.runner import StrategyRunner
from nexus.strategy.timer_loop import TimerLoop

from praxis.command_translator import (
    build_single_shot_params,
    translate_execution_mode,
    translate_maker_preference,
    translate_order_side,
    translate_order_type,
    translate_stp_mode,
)
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.events import OutcomeAcked
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.infrastructure.binance_urls import (
    MAINNET_REST_URL,
    MAINNET_WS_API_URL,
    MAINNET_WS_URL,
    TESTNET_REST_URL,
    TESTNET_WS_API_URL,
    TESTNET_WS_URL,
)
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.observability import bind_context, configure_logging
from praxis.market_data_cache import CacheScheduler, MainCache
from praxis.market_data_poller import MarketDataPoller, StaleMarketDataError
from praxis.outcome_translator import OutcomeTranslator
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.trading import Trading
from praxis.trading_config import TradingConfig

__all__ = ['InstanceConfig', 'Launcher', 'main']

_log = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = (
    'EPOCH_ID',
    'TRADE_MODE',
    'MANIFESTS_DIR',
    'STRATEGIES_BASE_PATH',
    'STATE_BASE',
)
_TRADE_MODE_PAPER = 'paper'
_TRADE_MODE_LIVE = 'live'
_TRADE_MODES = (_TRADE_MODE_PAPER, _TRADE_MODE_LIVE)
_DEFAULT_SHUTDOWN_TIMEOUT = '30'
_DEFAULT_HEALTHZ_PORT = 8080
_DEFAULT_DUPLICATE_WINDOW_MS = 1000
_DEFAULT_VENUE = 'binance_spot'
_DEFAULT_FEE_RATE = Decimal('0.001')
_DEFAULT_SYMBOL = 'BTCUSDT'
_DEFAULT_HEALTH_INTERVAL_SECONDS = 5.0
_DEFAULT_SNAPSHOT_INTERVAL_SECONDS = 300.0
_DEFAULT_MTM_INTERVAL_SECONDS = 30.0


def _positive_float_env(name: str, default: float) -> float:
    '''Parse a positive-numeric env var with operator-visible error on typo.

    Bare `float(os.environ.get(name, default))` crashes with an opaque
    `ValueError: could not convert string to float: ...` that surfaces
    as a per-account thread death (caught by `_run_nexus_instance`'s
    BLE001) with no operator-actionable signal. This helper validates
    the value and raises `RuntimeError` with the env var name + value +
    expected shape, which propagates through the same catch and is
    visible in the launcher's structured log.
    '''

    raw = os.environ.get(name)
    if raw is None or raw == '':
        return default

    try:
        value = float(raw)
    except ValueError as exc:
        msg = (
            f'env var {name}={raw!r} is not a valid number; '
            f'expected positive float (e.g. {default!r})'
        )
        raise RuntimeError(msg) from exc

    if not math.isfinite(value) or value <= 0:
        msg = (
            f'env var {name}={raw!r} must be a positive, finite number; '
            f'got {value!r} (expected > 0 and finite — `inf` makes '
            'threading.Timer wait forever, `nan` is undefined)'
        )
        raise RuntimeError(msg)

    return value
_ZERO = Decimal('0')
_HUNDRED = Decimal('100')

_ACTION_TYPE_TO_VALIDATION_ACTION = {
    ActionType.ENTER: ValidationAction.ENTER,
    ActionType.EXIT: ValidationAction.EXIT,
    ActionType.MODIFY: ValidationAction.MODIFY,
    ActionType.ABORT: ValidationAction.ABORT,
}


def _build_nexus_instance_config(
    praxis_inst: InstanceConfig,
    manifest: Manifest,
) -> NexusInstanceConfig:
    '''Build a Nexus runtime `InstanceConfig` for one account.

    Used by the launcher when wiring the per-account `submit_actions`
    closure (PT.1.4.4). The Nexus `InstanceConfig` is consumed by the
    validator pipeline and by `translate_to_trade_command`; it is
    distinct from the Praxis-side launcher `InstanceConfig` (per-account
    paths and manifest reference).

    Carries MMVP-conservative defaults — duplicate-window 1s,
    `STPMode.CANCEL_TAKER`, no per-process rate limit, no Stage-3 price
    thresholds. The per-strategy `capital_pct` map mirrors the
    manifest's strategy-spec percentages so capital-stage validation
    sees the same allocation the manifest declares.

    Args:
        praxis_inst: Per-account launcher config (used for `account_id`).
        manifest: Loaded strategy manifest (used to populate
            `capital_pct` from `manifest.strategies[*].capital_pct`).

    Returns:
        Nexus runtime `InstanceConfig` ready to pass into
        `ValidationPipeline` stages and `translate_to_trade_command`.
    '''

    capital_pct = {
        spec.strategy_id: spec.capital_pct for spec in manifest.strategies
    }

    return NexusInstanceConfig(
        account_id=praxis_inst.account_id,
        venue=_DEFAULT_VENUE,
        duplicate_window_ms=_DEFAULT_DUPLICATE_WINDOW_MS,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct=capital_pct,
    )


def _build_praxis_outbound(
    trading: Trading,
    loop: asyncio.AbstractEventLoop,
) -> PraxisOutbound:
    '''Build a fully-wired `PraxisOutbound` for one account.

    Wires every outbound call Nexus needs against the Praxis `Trading`
    singleton: command submission, account register / unregister,
    position pulls, abort submission, and health snapshot pulls.

    `Trading.submit_abort` is sync (it enqueues onto the account
    coroutine), but `PraxisOutbound` expects
    `Callable[..., Coroutine[Any, Any, None]]` so it can schedule the
    call via `run_coroutine_threadsafe` from the Nexus thread. A thin
    async adapter bridges the shape without touching the Praxis-side
    signature.

    Without the `submit_abort_fn` wiring, `PraxisOutbound.send_abort`
    raises `RuntimeError('submit_abort_fn not configured')` at first
    use — silently regressing `ShutdownSequencer` abort escalation
    and `submit_actions` ABORT handling. Without
    `get_health_snapshot_fn`, the runtime `HealthLoop` cannot pull
    snapshots and `operational_mode` never transitions.
    '''

    async def submit_abort_async(
        *,
        command_id: str,
        account_id: str,
        reason: str,
        created_at: datetime,
    ) -> None:
        trading.submit_abort(
            TradeAbort(
                command_id=command_id,
                account_id=account_id,
                reason=reason,
                created_at=created_at,
            ),
        )

    async def submit_command_with_translated_params(
        *,
        side: Any,
        order_type: Any,
        execution_mode: Any,
        maker_preference: Any,
        stp_mode: Any,
        execution_params: Any,
        **kwargs: Any,
    ) -> str:
        return await trading.submit_command(
            side=translate_order_side(side),
            order_type=translate_order_type(order_type),
            execution_mode=translate_execution_mode(execution_mode),
            maker_preference=translate_maker_preference(maker_preference),
            stp_mode=translate_stp_mode(stp_mode),
            execution_params=build_single_shot_params(execution_params),
            **kwargs,
        )

    return PraxisOutbound(
        submit_fn=submit_command_with_translated_params,
        loop=loop,
        register_fn=trading.register_account,
        unregister_fn=trading.unregister_account,
        pull_positions_fn=trading.pull_positions,
        submit_abort_fn=submit_abort_async,
        get_health_snapshot_fn=trading.get_health_snapshot,
    )


def _build_health_loop(
    trading: Trading,
    state: InstanceState,
    account_id: str,
    interval_seconds: float = _DEFAULT_HEALTH_INTERVAL_SECONDS,
    state_store: StateStore | None = None,
) -> HealthLoop:
    '''Build a per-account `HealthLoop` wired to Praxis health pulls.

    Each tick: pulls a `HealthSnapshot` via
    `Trading.get_health_snapshot_sync(account_id)`, which reads the
    `BinanceAdapter`'s in-memory trackers under their own lock without
    crossing the asyncio loop. Going through `PraxisOutbound`'s async
    bridge (`run_coroutine_threadsafe` + 30 s `future.result` timeout)
    blocked the per-account `HealthLoop` thread for up to 30 s when
    the loop was busy with a slow venue REST call, starving subsequent
    health snapshots. The sync accessor sidesteps the loop entirely.

    Each snapshot is evaluated through `HealthEvaluator(HealthThresholds())`
    with MMVP-default thresholds (200/500/1000 ms latency warn/breach/halt,
    3/5/10 consecutive failures, 10%/20%/40% failure rate,
    70%/85%/90% rate-limit utilisation (`rate_limit_headroom`; 0.0
    idle, 1.0 at limit — higher is worse), 500 ms clock drift), and
    updates `state.mode` on transition. The validator `HealthStagePolicy`
    (Decimal-typed) and the evaluator `HealthThresholds` (float-typed)
    are separate policy objects today; aligning them is a post-MMVP
    concern tracked separately.

    The Praxis `HealthSnapshot` dataclass is field-compatible with the
    Nexus `HealthSnapshot` that `HealthEvaluator.evaluate` reads (same
    `latency_p99_ms` / `consecutive_failures` / `failure_rate` /
    `rate_limit_headroom` / `clock_drift_ms` attribute names), so the
    provider returns Praxis's type and `evaluate` duck-types it without
    conversion.

    When `state_store` is provided, `state_store.refresh_rolling_losses`
    is wired as the `HealthLoop.rolling_loss_refresher` callback. It
    runs once per tick on the same daemon timer thread BEFORE
    `snapshot_provider`, recomputing the 24h/7d/30d rolling-loss
    aggregates from the WAL so the validator's
    `RISK_ROLLING_LOSS_*_LIMIT` enforcement (Nexus MAJOR-H) sees decay
    on idle windows instead of monotonically growing values. Failure
    is best-effort: a refresh exception is logged at WARN by the
    HealthLoop and the rest of the tick proceeds. When `state_store`
    is None, no refresher is wired (legacy / lightweight test paths).
    '''

    def snapshot_provider() -> Any:
        return trading.get_health_snapshot_sync(account_id)

    rolling_loss_refresher = (
        state_store.refresh_rolling_losses
        if state_store is not None
        else None
    )

    return HealthLoop(
        snapshot_provider=snapshot_provider,
        evaluator=HealthEvaluator(HealthThresholds()),
        state=state,
        interval_seconds=interval_seconds,
        rolling_loss_refresher=rolling_loss_refresher,
    )


def _default_health_snapshot() -> HealthStageSnapshot:
    '''Return a neutral `HealthStageSnapshot` for MMVP-lenient health stage.

    All policy thresholds default to `None`, so the health stage allows
    every action regardless of snapshot values; this constant snapshot
    only needs to satisfy `HealthStageSnapshot`'s field invariants.
    '''

    return HealthStageSnapshot(
        latency_ms=Decimal(0),
        consecutive_failures=Decimal(0),
        failure_rate=Decimal(0),
        rate_limit_headroom=Decimal(1),
        clock_drift_ms=Decimal(0),
    )


def _default_platform_snapshot() -> PlatformLimitsStageSnapshot:
    '''Return an empty `PlatformLimitsStageSnapshot` for MMVP defaults.'''

    return PlatformLimitsStageSnapshot()


def _default_price_snapshot() -> PriceCheckSnapshot | None:
    '''Return `None`; MMVP `PriceStageLimits` are all unset.'''

    return None


def _build_validation_pipeline(
    nexus_config: NexusInstanceConfig,
    capital_controller: CapitalController,
    *,
    health_snapshot_provider: Callable[[], HealthStageSnapshot] = (
        _default_health_snapshot
    ),
    platform_snapshot_provider: Callable[[], PlatformLimitsStageSnapshot] = (
        _default_platform_snapshot
    ),
    price_snapshot_provider: Callable[[], PriceCheckSnapshot | None] = (
        _default_price_snapshot
    ),
) -> ValidationPipeline:
    '''Build a six-stage `ValidationPipeline` for one account.

    Each stage closure captures stage-specific configuration that is
    derived once from `nexus_config`; mutable runtime state (health
    snapshot, platform-limits snapshot, price-check snapshot) is read on
    every call via the supplied providers.

    MMVP defaults are deliberately lenient: `RiskStageLimits`,
    `PlatformLimitsStageLimits`, and `HealthStagePolicy` are constructed
    with all thresholds unset so each stage allows every action;
    `PriceStageLimits` is derived from `nexus_config` and inherits the
    same all-unset posture from `_build_nexus_instance_config`.
    Operator-supplied limits are dialed in pre-live by passing a
    pre-configured `nexus_config` and richer snapshot providers.

    Intake hooks are built once via `build_default_intake_hooks` so the
    duplicate-order window state is preserved across ticks. Both
    `active_command_ids` and `modifiable_command_ids` default to empty;
    `ABORT` and `MODIFY` are not exercised by the action-submission
    helper (`submit_actions` bypasses the validator for `ABORT`, and
    MMVP strategies do not emit `MODIFY`).

    Args:
        nexus_config: Per-account Nexus runtime config built by
            `_build_nexus_instance_config`.
        capital_controller: Per-account capital controller wrapping the
            mutable `CapitalState` from `sequencer.instance_state.capital`.
        health_snapshot_provider: Callable returning the current health
            snapshot. Defaults to a neutral-healthy snapshot.
        platform_snapshot_provider: Callable returning the current
            platform-limits snapshot. Defaults to an empty snapshot.
        price_snapshot_provider: Callable returning the current
            price-check snapshot. Defaults to `None`.

    Returns:
        Six-stage `ValidationPipeline` ready for use by `submit_actions`.
    '''

    intake_hooks = build_default_intake_hooks(nexus_config)
    risk_limits = RiskStageLimits()
    price_limits = build_price_stage_limits_from_config(nexus_config)
    platform_limits = PlatformLimitsStageLimits()
    health_policy = HealthStagePolicy()

    def intake(context: ValidationRequestContext) -> ValidationDecision:
        return validate_intake_stage(context, hooks=intake_hooks)

    def risk(context: ValidationRequestContext) -> ValidationDecision:
        return validate_risk_stage(context, risk_limits)

    def price(context: ValidationRequestContext) -> ValidationDecision:
        return validate_price_stage(
            context,
            price_limits,
            price_snapshot_provider(),
        )

    def capital(context: ValidationRequestContext) -> ValidationDecision:
        return validate_capital_stage(context, capital_controller)

    def health(context: ValidationRequestContext) -> ValidationDecision:
        return validate_health_stage(
            context,
            health_snapshot_provider(),
            health_policy,
        )

    def platform_limits_stage(
        context: ValidationRequestContext,
    ) -> ValidationDecision:
        return validate_platform_limits_stage(
            context,
            platform_limits,
            platform_snapshot_provider(),
        )

    validators: dict[ValidationStage, StageValidator] = {
        ValidationStage.INTAKE: intake,
        ValidationStage.RISK: risk,
        ValidationStage.PRICE: price,
        ValidationStage.CAPITAL: capital,
        ValidationStage.HEALTH: health,
        ValidationStage.PLATFORM_LIMITS: platform_limits_stage,
    }

    return ValidationPipeline(validators)


def _build_validation_context(
    action: Action,
    strategy_id: str,
    *,
    nexus_config: NexusInstanceConfig,
    capital_controller: CapitalController,
    state: InstanceState,
    capital_pct: Decimal,
    fallback_price_provider: Callable[[], Decimal | None],
    fee_rate: Decimal = _DEFAULT_FEE_RATE,
    enter_symbol: str = _DEFAULT_SYMBOL,
    venue_adapter: VenueAdapter | None = None,
) -> ValidationRequestContext | None:
    '''Build a `ValidationRequestContext` from a strategy `Action`.

    Maps each `ActionType` to its `ValidationAction` counterpart and
    derives the validator's request-shape fields:

    - `ENTER`: when `venue_adapter` is supplied, `action.size` is
      routed through `venue_adapter.quantize_for_command(...)` to
      floor-snap to the symbol's `LOT_SIZE.stepSize` and gate against
      `minQty` / `minNotional`; on rejection the helper logs and
      returns `None` so the caller drops the action. `order_notional`
      is then `snapped_qty * reference_price` (or `action.size *
      reference_price` when `venue_adapter` is `None`, e.g. tests).
      `reference_price` falls back to `fallback_price_provider()` when
      `action.reference_price` is unset. Returns `None` (and logs) when
      no price is available — the action cannot be validated without
      one. Uses `enter_symbol` (MMVP default `BTCUSDT`) and generates a
      command id when the action does not carry one.
    - `EXIT`: same quantization pipeline runs against
      `state.positions[action.trade_id].entry_price` as the reference
      price; `order_notional` is `snapped_qty * entry_price` (or
      `action.size * entry_price` when `venue_adapter` is `None`).
      Returns `None` (and logs) when the referenced trade is missing
      from instance state — the helper skips the action and the caller
      drops it.
    - `MODIFY`: returns `None` and logs a TD-tracked warning. The
      `current_order_notional` source is non-trivial and deferred; MMVP
      strategies do not emit `MODIFY`.
    - `ABORT`: returns `None`. `submit_actions` bypasses the validator
      for `ABORT` and never calls this helper for that action type.

    `estimated_fees = order_notional * fee_rate` (Binance taker default
    `0.001` for MMVP). `strategy_budget` is computed via
    `CapitalController.compute_strategy_budget(strategy_id, capital_pct)`
    so capital-stage validation sees the same allocation as the
    manifest's `capital_pct` declaration.

    Args:
        action: Strategy-emitted action being validated.
        strategy_id: Owning strategy identifier.
        nexus_config: Per-account Nexus runtime config.
        capital_controller: Per-account capital controller.
        state: Current mutable instance state (live, not a snapshot).
        capital_pct: Strategy's manifest capital allocation percentage.
        fallback_price_provider: Returns the latest reference price
            (e.g. last `MarketDataPoller` close) or `None` when no
            market data is available yet.
        fee_rate: Effective taker fee rate for fee estimation.
        enter_symbol: Symbol used for `ENTER` actions when the action
            itself does not carry one.

    Returns:
        `ValidationRequestContext` for `ENTER`/`EXIT`, or `None` when
        the action cannot be validated (missing price, missing trade,
        unsupported `MODIFY`/`ABORT`).
    '''

    validation_action = _ACTION_TYPE_TO_VALIDATION_ACTION.get(action.action_type)
    if validation_action is None:
        _log.warning(
            'unknown action_type for validation context',
            extra={
                'strategy_id': strategy_id,
                'action_type': action.action_type,
            },
        )
        return None

    if validation_action == ValidationAction.MODIFY:
        _log.warning(
            'MODIFY validation context not implemented (TD); skipping action',
            extra={
                'strategy_id': strategy_id,
                'command_id': action.command_id or f'cmd-{uuid.uuid4().hex}',
            },
        )
        return None

    if validation_action == ValidationAction.ABORT:
        return None

    strategy_budget = capital_controller.compute_strategy_budget(
        strategy_id=strategy_id,
        capital_pct=capital_pct,
    )

    if validation_action == ValidationAction.ENTER:
        return _build_enter_context(
            action=action,
            strategy_id=strategy_id,
            nexus_config=nexus_config,
            state=state,
            strategy_budget=strategy_budget,
            fallback_price_provider=fallback_price_provider,
            fee_rate=fee_rate,
            enter_symbol=enter_symbol,
            venue_adapter=venue_adapter,
        )

    return _build_exit_context(
        action=action,
        strategy_id=strategy_id,
        nexus_config=nexus_config,
        state=state,
        strategy_budget=strategy_budget,
        fee_rate=fee_rate,
        venue_adapter=venue_adapter,
    )


def _build_enter_context(
    *,
    action: Action,
    strategy_id: str,
    nexus_config: NexusInstanceConfig,
    state: InstanceState,
    strategy_budget: Decimal,
    fallback_price_provider: Callable[[], Decimal | None],
    fee_rate: Decimal,
    enter_symbol: str,
    venue_adapter: VenueAdapter | None = None,
) -> ValidationRequestContext | None:
    command_id = action.command_id or f'cmd-{uuid.uuid4().hex}'
    reference_price = action.reference_price

    if reference_price is None:
        reference_price = fallback_price_provider()

    if reference_price is None:
        _log.warning(
            'no reference price available for ENTER; skipping action',
            extra={
                'strategy_id': strategy_id,
                'command_id': command_id,
            },
        )
        return None

    if action.size is None:
        _log.warning(
            'ENTER action has no size; skipping',
            extra={
                'strategy_id': strategy_id,
                'command_id': command_id,
            },
        )
        return None

    order_size = action.size

    if venue_adapter is not None:
        quantize_order_type = (
            translate_order_type(action.order_type)
            if action.order_type is not None
            else OrderType.MARKET
        )
        quantization = venue_adapter.quantize_for_command(
            enter_symbol,
            action.size,
            quantize_order_type,
            reference_price=reference_price,
        )

        if quantization.rejection_reason is not None:
            _log.warning(
                'ENTER action rejected by venue filters at intake; skipping',
                extra={
                    'strategy_id': strategy_id,
                    'command_id': command_id,
                    'symbol': enter_symbol,
                    'reference_price': str(reference_price),
                    'requested_size': str(action.size),
                    'reason': quantization.rejection_reason,
                },
            )
            return None

        assert quantization.snapped_qty is not None
        order_size = quantization.snapped_qty

    order_notional = order_size * reference_price
    estimated_fees = order_notional * fee_rate
    order_side = action.direction or OrderSide.BUY

    return ValidationRequestContext(
        strategy_id=strategy_id,
        action=ValidationAction.ENTER,
        symbol=enter_symbol,
        order_side=order_side,
        order_size=order_size,
        command_id=command_id,
        trade_id=None,
        order_notional=order_notional,
        estimated_fees=estimated_fees,
        strategy_budget=strategy_budget,
        state=state,
        config=nexus_config,
    )


def _build_exit_context(
    *,
    action: Action,
    strategy_id: str,
    nexus_config: NexusInstanceConfig,
    state: InstanceState,
    strategy_budget: Decimal,
    fee_rate: Decimal,
    venue_adapter: VenueAdapter | None = None,
) -> ValidationRequestContext | None:
    trade_id = action.trade_id
    if trade_id is None or trade_id not in state.positions:
        _log.warning(
            'EXIT trade_id not found in state.positions; skipping action',
            extra={
                'strategy_id': strategy_id,
                'trade_id': trade_id,
            },
        )
        return None

    position = state.positions[trade_id]

    if action.size is None:
        _log.warning(
            'EXIT action has no size; skipping',
            extra={
                'strategy_id': strategy_id,
                'trade_id': trade_id,
            },
        )
        return None

    order_size = action.size

    if venue_adapter is not None:
        quantize_order_type = (
            translate_order_type(action.order_type)
            if action.order_type is not None
            else OrderType.MARKET
        )
        quantization = venue_adapter.quantize_for_command(
            position.symbol,
            action.size,
            quantize_order_type,
            reference_price=position.entry_price,
        )

        if quantization.rejection_reason is not None:
            _log.warning(
                'EXIT action rejected by venue filters at intake; skipping',
                extra={
                    'strategy_id': strategy_id,
                    'trade_id': trade_id,
                    'symbol': position.symbol,
                    'entry_price': str(position.entry_price),
                    'requested_size': str(action.size),
                    'reason': quantization.rejection_reason,
                },
            )
            return None

        assert quantization.snapped_qty is not None
        order_size = quantization.snapped_qty

    order_notional = position.entry_price * order_size
    estimated_fees = order_notional * fee_rate
    command_id = action.command_id or f'cmd-{uuid.uuid4().hex}'
    order_side = action.direction or OrderSide.SELL

    return ValidationRequestContext(
        strategy_id=strategy_id,
        action=ValidationAction.EXIT,
        symbol=position.symbol,
        order_side=order_side,
        order_size=order_size,
        command_id=command_id,
        trade_id=trade_id,
        order_notional=order_notional,
        estimated_fees=estimated_fees,
        strategy_budget=strategy_budget,
        state=state,
        config=nexus_config,
    )


def _ensure_entry_position(
    *,
    state: InstanceState,
    action: Action,
    strategy_id: str,
    trade_id: str,
    fallback_price_provider: Callable[[], Decimal | None],
    positions_lock: threading.Lock | None = None,
) -> None:
    '''Pre-populate `state.positions[trade_id]` with a size=0 placeholder.

    `OutcomeProcessor._handle_fill` → `_grow_position` requires both
    `OrderContext.trade_id` to be non-`None` and a `Position` record at
    `state.positions[trade_id]`. ENTER actions don't have a Nexus-side
    `trade_id` until we mint one (PT-FIX-20), and Nexus has no
    auto-create-on-first-fill path. The launcher therefore inserts a
    `size=0` placeholder keyed by the Praxis-assigned command_id at
    submission time so the first FILLED outcome can grow it via VWAP
    (`_grow_position` math collapses to `new_entry_price = fill_price`
    when `old_size == 0`).

    Idempotent via `dict.setdefault` — repeated calls are no-ops.
    Skips silently when no reference price is available; the action
    would already have been rejected by `_build_enter_context`'s
    no-price guard, so reaching this branch with `ref_price is None`
    means a deeper bug — logging the skip rather than raising keeps
    the submitter loop alive.
    '''

    ref_price = action.reference_price
    if ref_price is None:
        ref_price = fallback_price_provider()

    if ref_price is None:
        _log.warning(
            'cannot pre-populate entry Position: no reference price',
            extra={'strategy_id': strategy_id, 'trade_id': trade_id},
        )
        return

    placeholder = Position(
        trade_id=trade_id,
        strategy_id=strategy_id,
        symbol=_DEFAULT_SYMBOL,
        side=action.direction or OrderSide.BUY,
        size=_ZERO,
        entry_price=ref_price,
    )

    if positions_lock is not None:
        with positions_lock:
            state.positions.setdefault(trade_id, placeholder)
    else:
        state.positions.setdefault(trade_id, placeholder)


def _build_order_context(
    *,
    action: Action,
    strategy_id: str,
    command_id: str,
    build_context: Callable[[Action, str], ValidationRequestContext | None],
    forced_trade_id: str | None = None,
) -> OrderContext | None:
    '''Reconstruct an `OrderContext` for a successfully submitted action.

    Re-runs `build_context(action, strategy_id)` to recover the
    `ValidationRequestContext` that the validator already used, then
    maps its fields onto the `OrderContext` shape `OutcomeProcessor`
    expects. Returns `None` (and logs) when the validation context
    cannot be rebuilt or when the resulting fields fail
    `OrderContext.__post_init__` invariants — the launcher then logs
    and proceeds without registering the context, so the outcome
    processor will skip the command rather than corrupt capital
    state on a malformed input.

    Args:
        action: Strategy action that produced the command.
        strategy_id: Owning strategy identifier.
        command_id: Praxis-assigned command id from the SUBMITTED outcome.
        build_context: Same closure used by `submit_actions` to rebuild
            the validation request context for `action`.
        forced_trade_id: When set, overrides `validation_context.trade_id`
            on the returned `OrderContext`. The launcher uses this for
            ENTER actions (where the validator's trade_id is `None`) so
            `OutcomeProcessor._grow_position` can find a `Position`
            record keyed by the same id.

    Returns:
        `OrderContext` ready for `OutcomeProcessor.process(...)`, or
        `None` when the context cannot be safely constructed.
    '''

    validation_context = build_context(action, strategy_id)
    if validation_context is None:
        return None

    if validation_context.order_side is None or validation_context.order_size is None:
        _log.warning(
            'cannot build OrderContext: validation context missing side/size',
            extra={'strategy_id': strategy_id, 'command_id': command_id},
        )
        return None

    trade_id = forced_trade_id if forced_trade_id is not None else validation_context.trade_id

    try:
        return OrderContext(
            command_id=command_id,
            strategy_id=strategy_id,
            trade_id=trade_id,
            side=validation_context.order_side,
            order_size=validation_context.order_size,
            order_notional=validation_context.order_notional,
            estimated_fees=validation_context.estimated_fees,
            is_entry=action.action_type == ActionType.ENTER,
        )
    except ValueError:
        _log.exception(
            'OrderContext rejected by invariants',
            extra={'strategy_id': strategy_id, 'command_id': command_id},
        )
        return None


def _register_wired_kline_sizes(
    wired_sensors: Iterable[Any],
) -> tuple[int, ...]:
    '''Collect kline sizes from wired sensors.

    Called from `_build_nexus_runtime` after `sequencer.start()` has
    trained the manifest's sensors. Each `WiredSensor` carries a live
    `limen_manifest` whose `data_source_config.params['kline_size']`
    declares the bucket width the sensor needs. Pre-PR (PT-FIX-1) the
    launcher tried to read `_limen_manifest` from raw `SensorSpec`
    objects in the manifest YAML; that attribute is not set until the
    Limen `Trainer` runs, so the lookup always returned `None`, the
    poller started empty, and `signal_producer.produce_signal` raised
    `ValueError("market_data is empty for sensor X")` on every tick.

    Returns the sorted tuple of declared kline sizes for the
    launcher's `fallback_price_provider` closure to iterate. Post
    market-data-cache rewire (Praxis #108) the cache is
    symbol-scoped — there is no per-kline_size registration to
    perform, so this function only collects the sizes from wired
    sensor manifests.
    '''

    sizes: set[int] = set()

    for wired in wired_sensors:
        try:
            config = getattr(
                getattr(wired, 'limen_manifest', None),
                'data_source_config',
                None,
            )

            if config is None:
                continue

            params = getattr(config, 'params', None)

            if params is None:
                continue

            raw = params.get('kline_size')

            if raw is None:
                continue

            kline_size = int(raw)

            if kline_size <= 0:
                _log.warning(
                    'skipping wired sensor with non-positive kline_size',
                    extra={
                        'sensor_type': type(wired).__name__,
                        'kline_size': kline_size,
                    },
                )
                continue

            if kline_size % 60 != 0:
                _log.warning(
                    'skipping wired sensor with non-multiple-of-60 kline_size',
                    extra={
                        'sensor_type': type(wired).__name__,
                        'kline_size': kline_size,
                    },
                )
                continue

            sizes.add(kline_size)
        except Exception:  # noqa: BLE001 - per-sensor parse must not abort startup
            _log.warning(
                'skipping wired sensor with invalid kline_size configuration',
                extra={'sensor_type': type(wired).__name__},
                exc_info=True,
            )

    return tuple(sorted(sizes))


def _ensure_strategies_path_importable(strategies_base_path: Path) -> None:
    '''Prepend `strategies_base_path` to `sys.path` so user SFD modules import.

    Limen `Trainer` resolves the SFD class via
    `importlib.import_module(metadata['sfd_module'])`; the module path
    recorded at training time must be importable in the launcher
    process at boot. Foundational SFDs ship inside `vaquum_limen` so
    they always resolve, but user-defined SFDs (e.g. a custom
    `Round3SFD` co-located with strategies) need the strategy
    directory on `sys.path` before `_wire_sensors` runs. This helper
    is idempotent and prepends rather than appends so a user-supplied
    module shadows any installed package of the same name.

    Operators with SFDs outside `STRATEGIES_BASE_PATH` should add the
    extra path to `PYTHONPATH` at deploy time; the launcher does not
    enumerate alternative roots.
    '''

    resolved = str(strategies_base_path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def _last_close_from_poller(
    poller: MarketDataPoller | None,
    kline_sizes: tuple[int, ...],
) -> Decimal | None:
    '''Return the last-known close from the poller, or `None` if absent or stale.

    Iterates `kline_sizes` (smallest first) and returns the close value
    of the last row in the first non-empty, non-stale DataFrame found.
    Returns `None` when the poller is absent, every kline_size is empty
    or stale, or no DataFrame has a `close` column.

    Round-18 MAJOR-005: a stale entry now raises `StaleMarketDataError`
    from `get_market_data`. This helper swallows the exception per
    kline_size and falls through to the next; if every kline_size is
    stale (or empty), the caller (`fallback_price_provider`) returns
    `None`, which the validator's PRICE stage rejects with a clear
    reason. Pre-fix the helper returned the indefinitely-stale cached
    value, sizing ENTERs against ancient prices.
    '''

    if poller is None:
        return None

    for kline_size in kline_sizes:
        try:
            df = poller.get_market_data(kline_size)
        except StaleMarketDataError as exc:
            _log.warning(
                'fallback_price_provider skipping stale kline_size: %s',
                exc,
            )
            continue

        if df.height == 0 or 'close' not in df.columns:
            continue

        last_close = df.tail(1).get_column('close').item()

        if last_close is None:
            continue

        return Decimal(str(last_close))

    return None


def _build_strategy_context(
    state: InstanceState | None,
    manifest: Manifest | None,
    strategy_id: str,
    positions_lock: threading.Lock | None = None,
) -> StrategyContext:
    '''Derive the per-strategy `StrategyContext` from live state + manifest.

    Used by the runtime `context_provider` injected into PredictLoop and
    TimerLoop. Reads the live `InstanceState` (so reservations and
    operational-mode transitions show up between ticks) and the loaded
    `Manifest` (so per-strategy budgets follow the operational
    capital_pct allocation).

    Returns a "stopped" context (positions=(), capital_available=0,
    operational_mode=HALTED) when state or manifest is unavailable —
    safer than ACTIVE since strategies may treat empty positions as
    "no exposure" and act accordingly.

    `positions_lock` (PT-FIX-28 + MAJOR-J) is held only for the
    snapshot of `state.positions.values()`. Mutations come from two
    classes of writer, each of which now honors the same lock:
    (a) the launcher's terminal-cleanup `del state.positions[trade_id]`
    in `process_outcome` and `_ensure_entry_position`'s placeholder
    insert, both wrapped in `with positions_lock`; (b) the
    `OutcomeProcessor`'s `_grow_position` field-assignment block
    (`size`/`entry_price`/`avg_cost_basis`) and `_reduce_position`
    field-assignment + `del` block (post-MAJOR-J fix —
    `OutcomeProcessor` now accepts `positions_lock` via its
    constructor and wraps both mutation regions). Filtering of the
    snapshot by `strategy_id` happens after the lock is released
    (`Position.strategy_id` is immutable post-construction so the
    read-without-lock is safe).

    Args:
        state: Live `InstanceState` from `StartupSequencer.instance_state`.
        manifest: Loaded `Manifest` from `StartupSequencer.manifest`.
        strategy_id: Strategy whose context to build.
        positions_lock: Optional `threading.Lock` shared with the
            OutcomeLoop's mutation site. Tests pass `None` to skip
            locking; production callers always pass the runtime lock.
    '''

    if state is None or manifest is None:
        return StrategyContext(
            positions=(),
            capital_available=_ZERO,
            operational_mode=OperationalMode.HALTED,
        )

    spec = next(
        (s for s in manifest.strategies if s.strategy_id == strategy_id),
        None,
    )

    if spec is None:
        return StrategyContext(
            positions=(),
            capital_available=_ZERO,
            operational_mode=OperationalMode.HALTED,
        )

    strategy_budget = manifest.capital_pool * spec.capital_pct / _HUNDRED
    deployed = state.capital.per_strategy_deployed.get(strategy_id, _ZERO)
    capital_available = max(strategy_budget - deployed, _ZERO)

    if positions_lock is not None:
        with positions_lock:
            positions_snapshot = list(state.positions.values())
    else:
        positions_snapshot = list(state.positions.values())

    positions = tuple(
        pos for pos in positions_snapshot if pos.strategy_id == strategy_id
    )

    sm = state.strategy_modes.get(strategy_id)
    operational_mode = sm.state.mode if sm is not None else state.mode.mode

    return StrategyContext(
        positions=positions,
        capital_available=capital_available,
        operational_mode=operational_mode,
    )


@dataclass(frozen=True)
class InstanceConfig:
    '''Configuration for one Nexus Manager instance.

    Args:
        account_id: Trading account identifier (sourced from manifest).
        manifest_path: Path to strategy manifest YAML.
        strategies_base_path: Base path for strategy .py files.
        state_dir: Directory for WAL and snapshots.
        strategy_state_path: Directory for strategy state blobs.
    '''

    account_id: str
    manifest_path: Path
    strategies_base_path: Path
    state_dir: Path
    strategy_state_path: Path | None = None


@dataclass
class _NexusRuntime:
    '''Wired runtime components for one Nexus Manager instance.

    Built once by `Launcher._build_nexus_runtime` and handed to
    `_run_nexus_instance` for lifecycle orchestration (wait → shutdown).
    A regular (non-frozen) dataclass because the grouped components
    (`InstanceState`, `CapitalController`, `PredictLoop`, `OutcomeLoop`,
    etc.) are themselves mutable; the `_NexusRuntime` container
    carries them by reference.
    '''

    state_store: StateStore
    sequencer: StartupSequencer
    runner: StrategyRunner
    manifest: Manifest
    state: InstanceState
    nexus_config: NexusInstanceConfig
    capital_controller: CapitalController
    pipeline: ValidationPipeline
    praxis_outbound: PraxisOutbound
    praxis_inbound: PraxisInbound
    predict_loop: PredictLoop
    timer_loop: TimerLoop | None
    outcome_loop: OutcomeLoop
    health_loop: HealthLoop
    snapshot_scheduler: SnapshotScheduler
    mtm_loop: MtmLoop
    outcome_processor: OutcomeProcessor
    process_outcome: Callable[[NexusTradeOutcome], None]
    positions_lock: threading.Lock = field(default_factory=threading.Lock)


class Launcher:
    '''Orchestrates Praxis + Nexus + Limen in one process.

    Args:
        trading_config: Praxis trading configuration.
        instances: One InstanceConfig per Nexus Manager.
        event_spine: Pre-built event spine for Praxis. Mutually exclusive
            with `db_path`.
        db_path: Path to the SQLite file backing the event spine. When
            provided, the launcher opens the connection on its own loop
            and owns its lifecycle. Mutually exclusive with `event_spine`.
        venue_adapter: Optional injected venue adapter.
    '''

    def __init__(
        self,
        trading_config: TradingConfig,
        instances: list[InstanceConfig],
        event_spine: EventSpine | None = None,
        db_path: Path | None = None,
        venue_adapter: VenueAdapter | None = None,
        healthz_port: int | None = None,
        market_data_testnet: bool = False,
    ) -> None:
        if (event_spine is None) == (db_path is None):
            msg = 'Launcher requires exactly one of event_spine or db_path'
            raise ValueError(msg)

        self._trading_config = trading_config
        self._instances = list(instances)
        self._event_spine = event_spine
        self._db_path = db_path
        self._db_conn: aiosqlite.Connection | None = None
        self._owns_spine = event_spine is None
        self._venue_adapter = venue_adapter
        self._healthz_port = healthz_port
        self._market_data_testnet = market_data_testnet
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._trading: Trading | None = None
        self._cache: MainCache | None = None
        self._cache_scheduler: CacheScheduler | None = None
        self._poller: MarketDataPoller | None = None
        self._nexus_threads: list[threading.Thread] = []
        self._healthz_runner: web.AppRunner | None = None
        self._outcome_queues: dict[str, queue.Queue[NexusTradeOutcome]] = {}
        self._outcome_translator = OutcomeTranslator()

    def launch(self) -> None:
        '''Start Praxis + Nexus in one process.

        Blocks until SIGINT/SIGTERM. Handles graceful shutdown.
        '''

        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        self._start_event_loop()
        self._start_trading()
        self._start_poller()
        self._start_nexus_instances()
        self._start_healthz()

        _log.info('all nexus instances started', extra={'count': len(self._nexus_threads)})

        self._stop_event.wait()

        _log.info('shutting down')
        self._shutdown()

    def _signal_handler(self, _signum: int, _frame: Any) -> None:
        _log.info('shutdown signal received')
        self._stop_event.set()

    def _start_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name='asyncio-loop',
        )
        self._loop_thread.start()

    def _start_trading(self) -> None:
        if self._loop is None:
            msg = 'event loop not started'
            raise RuntimeError(msg)

        if self._event_spine is None:
            spine_future = asyncio.run_coroutine_threadsafe(
                self._build_event_spine(),
                self._loop,
            )
            self._event_spine = spine_future.result(timeout=30)

        self._trading = Trading(
            config=self._trading_config,
            event_spine=self._event_spine,
            venue_adapter=self._venue_adapter,
            bootstrap_filter_symbols=frozenset({_DEFAULT_SYMBOL}),
        )

        for inst in self._instances:
            account_queue: queue.Queue[NexusTradeOutcome] = queue.Queue()
            self._outcome_queues[inst.account_id] = account_queue

        translator = self._outcome_translator
        outcome_queues = self._outcome_queues

        def _route_translated(praxis_outcome: TradeOutcome) -> None:
            q = outcome_queues.get(praxis_outcome.account_id)
            if q is None:
                _log.warning(
                    'no outcome queue for account, dropping outcome',
                    extra={
                        'account_id': praxis_outcome.account_id,
                        'command_id': praxis_outcome.command_id,
                    },
                )
                return

            for nexus_outcome in translator.translate(praxis_outcome):
                q.put_nowait(nexus_outcome)

        existing_on_trade_outcome = self._trading_config.on_trade_outcome

        if existing_on_trade_outcome is None:
            self._trading.set_on_trade_outcome(_route_translated)
        else:
            user_cb = existing_on_trade_outcome

            async def _composed(outcome: TradeOutcome) -> None:
                _route_translated(outcome)
                await user_cb(outcome)

            self._trading.set_on_trade_outcome(_composed)

        future = asyncio.run_coroutine_threadsafe(self._trading.start(), self._loop)
        future.result(timeout=30)
        _log.info('trading started')

    async def _build_event_spine(self) -> EventSpine:
        if self._db_path is None:
            msg = 'db_path required to build event spine'
            raise RuntimeError(msg)

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_conn = await aiosqlite.connect(str(self._db_path))
        spine = EventSpine(self._db_conn)
        await spine.ensure_schema()

        _log.info('event spine opened', extra={'db_path': str(self._db_path)})
        return spine

    def _append_outcome_acked(self, account_id: str, outcome_id: str) -> None:
        '''Append a durable OutcomeAcked event after Nexus accepted the outcome.

        Round-18 MAJOR-004: marks `outcome_id` as fully consumed by the
        Nexus consumer so the boot replay-from-spine pass does not
        re-deliver it. Runs on the Nexus thread (caller is the
        per-account `process_outcome` closure); dispatches the async
        spine append onto the Praxis loop. Failure is logged but does
        not abort outcome processing — the worst case is that the next
        boot replays the (already-applied) outcome and Nexus's
        idempotent OutcomeProcessor returns success no-op.
        '''

        if self._loop is None or self._trading is None:
            _log.warning(
                'cannot append OutcomeAcked: loop or trading not initialised',
                extra={'outcome_id': outcome_id, 'account_id': account_id},
            )
            return

        event = OutcomeAcked(
            account_id=account_id,
            timestamp=datetime.now(UTC),
            outcome_id=outcome_id,
        )
        epoch_id = self._trading_config.epoch_id
        spine = self._trading.event_spine

        try:
            future = asyncio.run_coroutine_threadsafe(
                spine.append(event, epoch_id), self._loop,
            )
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - ack failure must not abort outcome flow
            _log.exception(
                'OutcomeAcked append failed; boot replay will re-deliver',
                extra={'outcome_id': outcome_id, 'account_id': account_id},
            )

    def _start_poller(self) -> None:
        '''Build the MainCache, fill it at boot, start CacheScheduler, wrap in MarketDataPoller.

        On first-ever boot the on-disk parquet at `MAIN_CACHE_DIR`
        is missing; `bootstrap_if_empty()` triggers a synchronous
        `refresh_from_limen()` to populate it from the HF dataset.
        Then a synchronous `refresh_from_binancial()` fills the
        trailing-day gap that Limen does not cover, so when
        `CacheScheduler.start()` returns and the first sensor tick
        fires, the cache already has fresh data — no 1-minute
        warm-up window where strategies see only Limen bars.
        Restart-with-existing-parquet skips bootstrap and just
        calls `load()` to populate the in-memory mirror.

        The `MarketDataPoller` adapter wraps the cache for
        backward-compat with the existing `market_data_provider`
        callback and the staleness-aware `fallback_price_provider`.
        Lifecycle is owned by `CacheScheduler`, not the adapter.
        '''

        client = Client(None, None, ping=False, testnet=self._market_data_testnet)
        cache_dir = Path(os.environ.get('MAIN_CACHE_DIR', '/var/lib/praxis/maincache'))
        parquet_path = cache_dir / 'btcusdt_1m.parquet'
        state_path = cache_dir / 'main_cache_state.json'

        try:
            self._cache = MainCache(
                client,
                parquet_path=parquet_path,
                main_cache_state_path=state_path,
            )
        except OSError as exc:
            msg = (
                f'failed to initialize MainCache at {cache_dir}: {exc!r}. '
                f'Set the MAIN_CACHE_DIR environment variable to a writable '
                f'host bind mount (default: /var/lib/praxis/maincache).'
            )
            raise RuntimeError(msg) from exc

        self._cache.load()

        try:
            self._cache.bootstrap_if_empty()
        except Exception:  # noqa: BLE001 - resilience: scheduler retries
            _log.exception(
                'cache bootstrap_if_empty failed at boot; '
                'CacheScheduler will retry on the next 05:00 UTC tick',
            )

        try:
            self._cache.refresh_from_binancial()
        except Exception:  # noqa: BLE001 - resilience: scheduler retries
            _log.exception(
                'cache refresh_from_binancial failed at boot; '
                'CacheScheduler will retry on the next 60s tick. '
                'Sensors will see StaleMarketDataError until refresh succeeds',
            )

        self._cache_scheduler = CacheScheduler(self._cache)
        self._cache_scheduler.start()
        self._poller = MarketDataPoller(self._cache)

    def _start_healthz(self) -> None:
        '''Start the /healthz HTTP listener on the launcher's asyncio loop.

        Render polls this endpoint to decide whether to restart the
        container. 200 means Trading is up, the loop thread is alive,
        and every Nexus thread is alive; 503 otherwise.
        '''

        if self._healthz_port is None or self._loop is None:
            return

        future = asyncio.run_coroutine_threadsafe(
            self._build_healthz_runner(self._healthz_port),
            self._loop,
        )
        self._healthz_runner = future.result(timeout=10)
        _log.info('healthz listener started', extra={'port': self._healthz_port})

    def _stop_healthz(self) -> None:
        '''Stop the /healthz listener; subsequent requests will refuse.'''

        if self._healthz_runner is None or self._loop is None:
            return

        future = asyncio.run_coroutine_threadsafe(
            self._healthz_runner.cleanup(),
            self._loop,
        )
        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - best effort during shutdown
            _log.exception('healthz cleanup failed')
        self._healthz_runner = None

    async def _build_healthz_runner(self, port: int) -> web.AppRunner:
        app = web.Application()
        app.router.add_get('/healthz', self._healthz_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host='0.0.0.0', port=port)  # noqa: S104
        await site.start()
        return runner

    async def _healthz_handler(self, _request: web.Request) -> web.Response:
        failures: list[str] = []

        if self._stop_event.is_set():
            failures.append('shutting_down')

        if self._trading is None or not self._trading.started:
            failures.append('trading_not_started')

        if self._loop_thread is None or not self._loop_thread.is_alive():
            failures.append('loop_thread_dead')

        dead_nexus = [
            t.name for t in self._nexus_threads if not t.is_alive()
        ]
        if dead_nexus:
            failures.append(f'nexus_threads_dead:{",".join(dead_nexus)}')

        if failures:
            return web.json_response(
                {'status': 'unhealthy', 'failures': failures},
                status=503,
            )
        return web.json_response({'status': 'ok'})

    def _start_nexus_instances(self) -> None:
        if self._trading is None or self._loop is None:
            msg = 'trading not started'
            raise RuntimeError(msg)

        for inst in self._instances:
            outcome_queue = self._outcome_queues[inst.account_id]

            thread = threading.Thread(
                target=self._run_nexus_instance,
                args=(inst, outcome_queue),
                daemon=True,
                name=f'nexus-{inst.account_id}',
            )
            self._nexus_threads.append(thread)
            thread.start()

    def _shutdown(self) -> None:
        for thread in self._nexus_threads:
            thread.join(timeout=30)

            if thread.is_alive():
                _log.warning(
                    'nexus thread did not finish within timeout',
                    extra={'thread': thread.name},
                )

        if self._cache_scheduler is not None:
            self._cache_scheduler.stop()

        if self._trading is not None and self._loop is not None:
            future = asyncio.run_coroutine_threadsafe(self._trading.stop(), self._loop)
            future.result(timeout=30)

        if self._owns_spine and self._db_conn is not None and self._loop is not None:
            close_future = asyncio.run_coroutine_threadsafe(
                self._db_conn.close(),
                self._loop,
            )
            close_future.result(timeout=10)
            self._db_conn = None

        self._stop_healthz()

        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._loop_thread is not None:
            self._loop_thread.join(timeout=5)

        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()

        self._loop = None
        self._loop_thread = None

        _log.info('shutdown complete')

    def _run_nexus_instance(
        self,
        inst: InstanceConfig,
        outcome_queue: queue.Queue[NexusTradeOutcome],
    ) -> None:
        '''Build, run, and shut down one Nexus Manager instance in its own thread.'''

        if self._trading is None or self._loop is None:
            return

        try:
            runtime = self._build_nexus_runtime(inst, outcome_queue)

            _log.info('nexus instance running', extra={'account_id': inst.account_id})

            self._stop_event.wait()

            runtime.health_loop.stop()
            runtime.mtm_loop.stop()
            runtime.snapshot_scheduler.stop()

            shutdown = ShutdownSequencer(
                runner=runtime.runner,
                manifest=runtime.manifest,
                state_store=runtime.state_store,
                state=runtime.state,
                strategy_state_path=(
                    inst.strategy_state_path
                    or inst.state_dir / 'strategy_state'
                ),
                predict_loop=runtime.predict_loop,
                timer_loop=runtime.timer_loop,
                outcome_loop=runtime.outcome_loop,
                praxis_outbound=runtime.praxis_outbound,
                praxis_inbound=runtime.praxis_inbound,
                account_id=inst.account_id,
                config=runtime.nexus_config,
                outcome_processor=runtime.outcome_processor,
                non_pending_outcome_handler=runtime.process_outcome,
                positions_lock=runtime.positions_lock,
                capital_controller=runtime.capital_controller,
            )
            shutdown.shutdown()

            _log.info('nexus instance stopped', extra={'account_id': inst.account_id})

        except Exception:  # noqa: BLE001 - top-level catch for thread, must not propagate
            _log.exception('nexus instance failed', extra={'account_id': inst.account_id})
            self._stop_event.set()

    def _build_nexus_runtime(
        self,
        inst: InstanceConfig,
        outcome_queue: queue.Queue[NexusTradeOutcome],
    ) -> _NexusRuntime:
        '''Wire all per-account runtime components and start the loops.

        Runs through: `StateStore` / `PraxisOutbound` / `StartupSequencer`
        (state recovery) → per-account `NexusInstanceConfig`,
        `CapitalController`, six-stage `ValidationPipeline`, submitter /
        `build_context` / `context_provider` / `fallback_price_provider`
        closures → `PredictLoop`, `TimerLoop` (when the manifest carries
        timers), and `OutcomeLoop`, all started before returning. The
        caller is responsible for waiting on the shutdown signal and
        then invoking `ShutdownSequencer.shutdown()` on the returned
        runtime.

        Raises:
            RuntimeError: If `sequencer.start()` completed but the
                manifest/state accessors did not populate — indicates
                an inconsistent Nexus upgrade, not a normal shutdown
                path.
        '''

        if self._trading is None or self._loop is None:
            msg = 'Launcher runtime not initialized'
            raise RuntimeError(msg)

        _ensure_strategies_path_importable(inst.strategies_base_path)

        state_store = StateStore(inst.state_dir)

        praxis_outbound = _build_praxis_outbound(self._trading, self._loop)

        sequencer = StartupSequencer(
            state_store=state_store,
            manifest_path=inst.manifest_path,
            strategies_base_path=inst.strategies_base_path,
            strategy_state_path=inst.strategy_state_path,
            praxis_outbound=praxis_outbound,
        )

        runner = sequencer.start()

        manifest = sequencer.manifest
        state = sequencer.instance_state

        if manifest is None or state is None:
            msg = (
                'StartupSequencer.start() did not produce manifest/state for '
                f'account {inst.account_id!r}'
            )
            raise RuntimeError(msg)

        nexus_instance_config = _build_nexus_instance_config(inst, manifest)
        capital_controller = CapitalController(state.capital)
        capital_controller.reconcile_at_boot(positions=state.positions.values())
        pipeline = _build_validation_pipeline(nexus_instance_config, capital_controller)
        positions_lock = threading.Lock()
        command_registry_lock = threading.Lock()
        if not hasattr(state.risk, 'lock'):
            msg = (
                'state.risk has no `lock` slot; FINAL-MAJOR-02 cross-thread '
                'serialization requires Nexus RiskState to expose a transient '
                'lock attribute. Refusing to boot with broken concurrency.'
            )
            raise RuntimeError(msg)
        state.risk.lock = positions_lock
        capital_pct_by_strategy = {
            spec.strategy_id: spec.capital_pct for spec in manifest.strategies
        }
        kline_sizes = _register_wired_kline_sizes(sequencer.wired_sensors)

        def market_data_provider(kline_size: int) -> Any:
            if self._poller is None:
                return pl.DataFrame()
            return self._poller.get_market_data(kline_size)

        def context_provider(strategy_id: str) -> StrategyContext:
            return _build_strategy_context(
                sequencer.instance_state,
                sequencer.manifest,
                strategy_id,
                positions_lock=positions_lock,
            )

        def fallback_price_provider() -> Decimal | None:
            return _last_close_from_poller(self._poller, kline_sizes)

        def build_context(
            action: Action,
            strategy_id: str,
        ) -> ValidationRequestContext | None:
            capital_pct = capital_pct_by_strategy.get(strategy_id)

            if capital_pct is None:
                _log.warning(
                    'unknown strategy_id when building validation context; '
                    'skipping action',
                    extra={
                        'strategy_id': strategy_id,
                        'account_id': inst.account_id,
                    },
                )
                return None

            return _build_validation_context(
                action,
                strategy_id,
                nexus_config=nexus_instance_config,
                capital_controller=capital_controller,
                state=state,
                capital_pct=capital_pct,
                fallback_price_provider=fallback_price_provider,
                venue_adapter=(
                    self._trading.venue_adapter
                    if self._trading is not None
                    else None
                ),
            )

        command_strategy_ids: dict[str, str] = {}
        command_contexts: dict[str, OrderContext] = {}

        def submitter(actions: list[Action], strategy_id: str) -> None:
            results = submit_actions(
                actions,
                strategy_id=strategy_id,
                config=nexus_instance_config,
                praxis_outbound=praxis_outbound,
                validator=pipeline,
                build_context=build_context,
                now=lambda: datetime.now(UTC),
                capital_controller=capital_controller,
                positions_lock=positions_lock,
            )

            for action, outcome in results:
                if (
                    outcome.status != SubmissionStatus.SUBMITTED
                    or outcome.command_id is None
                ):
                    continue

                with command_registry_lock:
                    command_strategy_ids[outcome.command_id] = strategy_id

                    if (
                        outcome.decision is not None
                        and outcome.decision.reservation is not None
                    ):
                        send_result = capital_controller.send_order(
                            outcome.decision.reservation.reservation_id,
                            outcome.command_id,
                        )
                        if not send_result.success:
                            _log.error(
                                'send_order failed; skipping OrderContext '
                                'registration. The venue command was already '
                                'submitted, so subsequent ACK/FILL outcomes '
                                'will be dropped by OutcomeProcessor with '
                                "'no OrderContext for command'. The Nexus "
                                'reservation will be released by the next '
                                'boot reconcile_at_boot pass.',
                                extra={
                                    'command_id': outcome.command_id,
                                    'reason': send_result.reason,
                                },
                            )
                            command_strategy_ids.pop(outcome.command_id, None)
                            continue

                    forced_trade_id: str | None = None
                    if action.action_type == ActionType.ENTER:
                        forced_trade_id = outcome.command_id
                        _ensure_entry_position(
                            state=state,
                            action=action,
                            strategy_id=strategy_id,
                            trade_id=forced_trade_id,
                            fallback_price_provider=fallback_price_provider,
                            positions_lock=positions_lock,
                        )

                    order_context = _build_order_context(
                        action=action,
                        strategy_id=strategy_id,
                        command_id=outcome.command_id,
                        build_context=build_context,
                        forced_trade_id=forced_trade_id,
                    )

                    if order_context is not None:
                        command_contexts[outcome.command_id] = order_context

        def resolve_strategy_id(outcome: Any) -> str | None:
            with command_registry_lock:
                return command_strategy_ids.get(outcome.command_id)

        outcome_processor = OutcomeProcessor(
            capital_controller=capital_controller,
            instance_state=state,
            state_store=state_store,
            positions_lock=positions_lock,
        )

        def process_outcome(outcome: NexusTradeOutcome) -> None:
            with command_registry_lock:
                order_context = command_contexts.get(outcome.command_id)

            if order_context is None:
                _log.warning(
                    'no OrderContext for command; skipping processor',
                    extra={'command_id': outcome.command_id},
                )
                if outcome.outcome_type.is_terminal:
                    with command_registry_lock:
                        command_contexts.pop(outcome.command_id, None)
                        command_strategy_ids.pop(outcome.command_id, None)
                    recover_result = capital_controller.recover_orphaned_order(
                        outcome.command_id,
                        outcome.outcome_type.value,
                    )
                    if not recover_result.success:
                        _log.warning(
                            'recover_orphaned_order rejected the orphan release',
                            extra={
                                'command_id': outcome.command_id,
                                'outcome_type': outcome.outcome_type.value,
                                'reason': recover_result.reason,
                            },
                        )
                return

            result = outcome_processor.process(outcome, order_context)
            if not result.success:
                _log.warning(
                    'OutcomeProcessor reported failure',
                    extra={
                        'command_id': outcome.command_id,
                        'outcome_type': result.outcome_type.value,
                        'error': result.error_reason,
                    },
                )

            if outcome.outcome_type.is_terminal:
                with command_registry_lock:
                    command_contexts.pop(outcome.command_id, None)
                    command_strategy_ids.pop(outcome.command_id, None)
                if (
                    order_context.is_entry
                    and order_context.trade_id is not None
                ):
                    with positions_lock:
                        pos = state.positions.get(order_context.trade_id)
                        if pos is not None and pos.size == _ZERO:
                            del state.positions[order_context.trade_id]

            mutation_persisted = True
            if result.success and (result.position_updated or result.capital_updated):
                try:
                    state_store.append_mutation(state)
                except Exception:  # noqa: BLE001 - persistence failure must not abort outcome flow
                    mutation_persisted = False
                    _log.exception(
                        'append_mutation failed; mid-run state durability '
                        'lost for this outcome — OutcomeAcked withheld so '
                        'replay-from-spine will re-deliver and recovery '
                        'rolls back to the last clean checkpoint',
                        extra={'command_id': outcome.command_id},
                    )

            if result.success and mutation_persisted:
                self._append_outcome_acked(inst.account_id, outcome.outcome_id)

        sequencer.drain_pending_startup_actions(submitter)

        predict_loop = PredictLoop(
            runner=runner,
            wired_sensors=sequencer.wired_sensors,
            market_data_provider=market_data_provider,
            context_provider=context_provider,
            action_submit=submitter,
        )
        predict_loop.start()

        timer_loop: TimerLoop | None = None

        if sequencer.timer_specs:
            timer_loop = TimerLoop(
                runner=runner,
                strategy_timers=sequencer.timer_specs,
                context_provider=context_provider,
                action_submit=submitter,
            )
            timer_loop.start()

        praxis_inbound = PraxisInbound(outcome_queue=outcome_queue)

        outcome_loop = OutcomeLoop(
            runner=runner,
            praxis_inbound=praxis_inbound,
            state=state,
            context_provider=context_provider,
            resolve_strategy_id=resolve_strategy_id,
            action_submit=submitter,
            process_outcome=process_outcome,
        )
        outcome_loop.start()

        health_loop = _build_health_loop(
            trading=self._trading,
            state=state,
            account_id=inst.account_id,
            state_store=state_store,
        )
        health_loop.start()

        snapshot_interval = _positive_float_env(
            'NEXUS_SNAPSHOT_INTERVAL_SECONDS',
            _DEFAULT_SNAPSHOT_INTERVAL_SECONDS,
        )
        snapshot_scheduler = SnapshotScheduler(
            state_store=state_store,
            state=state,
            interval_seconds=snapshot_interval,
            positions_lock=positions_lock,
            capital_lock_cm=capital_controller.lock_cm,
        )
        snapshot_scheduler.start()

        mtm_interval = _positive_float_env(
            'NEXUS_MTM_INTERVAL_SECONDS',
            _DEFAULT_MTM_INTERVAL_SECONDS,
        )

        def mark_price_provider(symbol: str) -> Decimal | None:
            if symbol != _DEFAULT_SYMBOL:
                return None

            return _last_close_from_poller(self._poller, kline_sizes)

        mtm_loop = MtmLoop(
            state=state,
            mark_price_provider=mark_price_provider,
            interval_seconds=mtm_interval,
            positions_lock=positions_lock,
        )
        mtm_loop.start()

        return _NexusRuntime(
            state_store=state_store,
            sequencer=sequencer,
            runner=runner,
            manifest=manifest,
            state=state,
            nexus_config=nexus_instance_config,
            capital_controller=capital_controller,
            pipeline=pipeline,
            praxis_outbound=praxis_outbound,
            praxis_inbound=praxis_inbound,
            predict_loop=predict_loop,
            timer_loop=timer_loop,
            outcome_loop=outcome_loop,
            health_loop=health_loop,
            snapshot_scheduler=snapshot_scheduler,
            mtm_loop=mtm_loop,
            outcome_processor=outcome_processor,
            process_outcome=process_outcome,
            positions_lock=positions_lock,
        )

def _check_required_env(env: dict[str, str]) -> None:
    '''Raise if any required env var is missing or empty.'''

    missing = [name for name in _REQUIRED_ENV_VARS if not env.get(name)]
    if missing:
        msg = f'missing required env vars: {", ".join(missing)}'
        raise RuntimeError(msg)


def _resolve_trade_mode(env: dict[str, str]) -> tuple[str, str, str, bool]:
    '''Map `TRADE_MODE` to the venue REST/WS-stream/WS-API URLs and the testnet flag.

    Operators set `TRADE_MODE=paper` or `TRADE_MODE=live`; all three URLs
    and the market-data poller's testnet routing are derived from the
    in-code constants in `binance_urls`. There is no operator path
    that can submit orders to mainnet while the rest of the system
    thinks it is on testnet (MAJOR-001).

    `BINSIM_URL` is an optional paper-mode override pointing at an
    in-process binsim instance (`http://host:port`). When set under
    `TRADE_MODE=paper`, all three venue URLs are derived from it
    (REST stays http(s)://, WS endpoints become ws(s)://) and the
    market-data poller is routed to Binance Spot mainnet
    (`testnet=False`). Binsim is a fully internal venue with its own
    mainnet-quality depth feed (binsim PR #112 spec, "Order book — live
    source"); pairing it with sparse testnet aggTrades for sensor
    feature reconstruction is the asymmetry the binsim project was built
    to remove. MAJOR-001's order-routing invariant (orders submitted to
    mainnet only when the system as a whole is in live mode) is
    preserved — binsim orders never reach a real venue, so the
    market-data → mainnet routing does not create the asymmetric
    configuration MAJOR-001 protects against. Mixing `BINSIM_URL` with
    `TRADE_MODE=live` is a hard error: it would silently divert mainnet
    flow at the URL layer.
    '''

    raw = env['TRADE_MODE'].strip().lower()
    binsim_url = env.get('BINSIM_URL', '').strip()

    if raw == _TRADE_MODE_PAPER:
        if binsim_url:
            rest, ws, ws_api = _derive_binsim_urls(binsim_url)
            return rest, ws, ws_api, False

        return TESTNET_REST_URL, TESTNET_WS_URL, TESTNET_WS_API_URL, True

    if raw == _TRADE_MODE_LIVE:
        if binsim_url:
            msg = 'BINSIM_URL must not be set when TRADE_MODE=live'
            raise RuntimeError(msg)

        return MAINNET_REST_URL, MAINNET_WS_URL, MAINNET_WS_API_URL, False

    msg = (
        f'TRADE_MODE must be one of {list(_TRADE_MODES)!r}; got {env["TRADE_MODE"]!r}'
    )
    raise RuntimeError(msg)


def _derive_binsim_urls(binsim_url: str) -> tuple[str, str, str]:
    '''Split a single `BINSIM_URL` into the REST/WS/WS-API triple.

    `BINSIM_URL` is `http://host:port` (or `https://...` for a TLS-
    terminated deployment). The REST URL is used as the base, and
    both WS URLs are derived by replacing the scheme:
    `http://` → `ws://`, `https://` → `wss://`. The WS-API path is
    hard-coded to `/ws-api/v3` to match Binance's path-scoped WS-API
    endpoint (which the binsim server replicates).
    '''

    parsed = urlparse(binsim_url)

    if parsed.scheme not in ('http', 'https'):
        msg = f'BINSIM_URL must use http or https scheme, got {parsed.scheme!r}'
        raise RuntimeError(msg)

    # `netloc` is truthy for hostless URLs like `http://:8081` (netloc
    # is `:8081`), so we have to check `hostname` explicitly to reject
    # those — otherwise the derived URLs would be syntactically valid
    # but unroutable.
    if not parsed.hostname:
        msg = f'BINSIM_URL must include a hostname, got {binsim_url!r}'
        raise RuntimeError(msg)

    ws_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
    rest_url = f'{parsed.scheme}://{parsed.netloc}'
    ws_url = f'{ws_scheme}://{parsed.netloc}'
    ws_api_url = f'{ws_scheme}://{parsed.netloc}/ws-api/v3'

    return rest_url, ws_url, ws_api_url


_ACCOUNT_ID_SAFE_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


def _require_safe_account_id(account_id: str, manifest_path: Path) -> None:
    '''Reject account_ids that would escape the state directory as path segments.

    `account_id` from the manifest is used to form
    `STATE_BASE / <account_id> / <epoch_id>` and
    `STRATEGY_STATE_BASE / <account_id> / <epoch_id>`. A manifest containing path
    separators, `..`, or a leading `.` could escape the intended directory.
    Restrict to `[A-Za-z0-9][A-Za-z0-9._-]*` to match typical account-id
    conventions and stay a single safe filesystem component.
    '''

    if not _ACCOUNT_ID_SAFE_RE.fullmatch(account_id):
        msg = (
            f'account_id {account_id!r} (manifest {manifest_path}) is not a safe '
            f'filesystem component — must match [A-Za-z0-9][A-Za-z0-9._-]*'
        )
        raise RuntimeError(msg)


def _account_id_to_env_suffix(account_id: str) -> str:
    '''Normalize an account_id into a valid env-var suffix.

    Replaces non-alphanumeric chars with `_` and uppercases. e.g.
    `acct-001` -> `ACCT_001`.
    '''

    return ''.join(c if c.isalnum() else '_' for c in account_id).upper()


def _enumerate_manifests(manifests_dir: Path) -> list[Path]:
    '''Return globally-sorted list of manifest YAML paths in `manifests_dir`.'''

    if not manifests_dir.is_dir():
        msg = f'MANIFESTS_DIR not a directory: {manifests_dir}'
        raise RuntimeError(msg)

    paths = sorted(list(manifests_dir.glob('*.yaml')) + list(manifests_dir.glob('*.yml')))
    if not paths:
        msg = f'no manifest files (*.yaml/*.yml) found in {manifests_dir}'
        raise RuntimeError(msg)

    return paths


def main() -> None:
    '''Env-driven entrypoint for `python -m praxis.launcher`.

    Reads runtime configuration from the process environment, enumerates
    per-account strategy manifests under `MANIFESTS_DIR`, and starts one
    Trading service plus one Nexus Manager instance per manifest.
    Blocks until SIGINT or SIGTERM.

    Per-account Binance credentials are sourced from env vars
    `BINANCE_API_KEY_<ACCOUNT_ID>` / `BINANCE_API_SECRET_<ACCOUNT_ID>`,
    where `<ACCOUNT_ID>` is the manifest's `account_id` normalized
    (non-alphanumeric -> `_`, uppercased).
    '''

    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    log_format = os.environ.get('LOG_FORMAT', 'json').lower()

    if log_format == 'json':
        configure_logging(log_level=log_level)
    else:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
        )

    env = dict(os.environ)
    _check_required_env(env)

    venue_rest_url, venue_ws_url, venue_ws_api_url, market_data_testnet = _resolve_trade_mode(env)

    manifests_dir = Path(env['MANIFESTS_DIR'])
    state_base = Path(env['STATE_BASE'])
    epoch_id = int(env['EPOCH_ID'])
    strategies_base_path = Path(env['STRATEGIES_BASE_PATH'])
    strategy_state_base_raw = env.get('STRATEGY_STATE_BASE')
    strategy_state_base = Path(strategy_state_base_raw) if strategy_state_base_raw else None

    manifest_paths = _enumerate_manifests(manifests_dir)

    account_credentials: dict[str, tuple[str, str]] = {}
    instances: list[InstanceConfig] = []
    seen_account_ids: dict[str, Path] = {}
    seen_suffixes: dict[str, str] = {}

    for manifest_path in manifest_paths:
        manifest = load_manifest(manifest_path)
        account_id = manifest.account_id
        _require_safe_account_id(account_id, manifest_path)
        suffix = _account_id_to_env_suffix(account_id)

        if account_id in seen_account_ids:
            msg = (
                f'duplicate account_id {account_id!r} across manifests: '
                f'{seen_account_ids[account_id]} and {manifest_path}'
            )
            raise RuntimeError(msg)

        if suffix in seen_suffixes and seen_suffixes[suffix] != account_id:
            msg = (
                f'env-var suffix collision: account_ids '
                f'{seen_suffixes[suffix]!r} and {account_id!r} both normalize to '
                f'{suffix!r}, causing ambiguous BINANCE_API_KEY_{suffix} lookup'
            )
            raise RuntimeError(msg)

        seen_account_ids[account_id] = manifest_path
        seen_suffixes[suffix] = account_id

        api_key = env.get(f'BINANCE_API_KEY_{suffix}')
        api_secret = env.get(f'BINANCE_API_SECRET_{suffix}')

        if not api_key or not api_secret:
            msg = (
                f'missing BINANCE_API_KEY_{suffix} or BINANCE_API_SECRET_{suffix} '
                f'for account {account_id!r} (manifest {manifest_path})'
            )
            raise RuntimeError(msg)

        account_credentials[account_id] = (api_key, api_secret)

        state_dir = state_base / account_id / str(epoch_id)
        strategy_state_path = (
            strategy_state_base / account_id / str(epoch_id)
            if strategy_state_base is not None
            else None
        )

        instances.append(
            InstanceConfig(
                account_id=account_id,
                manifest_path=manifest_path,
                strategies_base_path=strategies_base_path,
                state_dir=state_dir,
                strategy_state_path=strategy_state_path,
            ),
        )

    trading_config = TradingConfig(
        epoch_id=epoch_id,
        venue_rest_url=venue_rest_url,
        venue_ws_url=venue_ws_url,
        venue_ws_api_url=venue_ws_api_url,
        account_credentials=account_credentials,
        shutdown_timeout=float(env.get('SHUTDOWN_TIMEOUT', _DEFAULT_SHUTDOWN_TIMEOUT)),
    )

    port_raw = env.get('PORT') or env.get('HEALTHZ_PORT')
    healthz_port = int(port_raw) if port_raw else _DEFAULT_HEALTHZ_PORT

    bind_context(epoch_id=trading_config.epoch_id)

    launcher = Launcher(
        trading_config=trading_config,
        instances=instances,
        db_path=state_base / 'event_spine.sqlite',
        healthz_port=healthz_port,
        market_data_testnet=market_data_testnet,
    )

    _log.info(
        'launching praxis',
        extra={
            'accounts': sorted(account_credentials.keys()),
            'state_base': str(state_base),
        },
    )
    launcher.launch()


if __name__ == '__main__':
    try:
        main()
    except Exception:  # noqa: BLE001 - top-level entrypoint, log and exit non-zero
        _log.exception('launcher failed')
        sys.exit(1)
