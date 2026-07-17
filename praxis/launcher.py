'''Process launcher for Praxis + Nexus.

Single entry point that starts the Trading service and one Nexus
Manager thread per account. Predictions are read from Conduit and
prices from the control-plane Arrow volume via `ArrowPriceStore`.
'''

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import math
import os
import queue
import re
import signal
import sys
import threading
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiosqlite
from aiohttp import ClientSession, ClientTimeout, web

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.enums import OperationalMode, OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.domain.position import Position
from nexus.core.health_evaluator import HealthEvaluator, HealthThresholds
from nexus.core.health_loop import HealthLoop
from nexus.core.mode_controller import ModeController
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
from nexus.infrastructure.praxis_connector.process_result import ProcessResult
from nexus.infrastructure.snapshot_scheduler import SnapshotScheduler
from nexus.infrastructure.praxis_connector.trade_command import (
    TradeCommand as NexusTradeCommand,
)
from nexus.infrastructure.praxis_connector.trade_outcome import (
    TradeOutcome as NexusTradeOutcome,
)
from nexus.infrastructure.state_store import StateSnapshotLocks, StateStore
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
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide as _PraxisOrderSide,
    OrderType,
    STPMode as _PraxisSTPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.events import (
    Event,
    MarkSampled,
    OperatorHaltRequested,
    OperatorResumeRequested,
    OutcomeAcked,
    OutcomeDeliveryContextRecorded,
    OutcomeReplayAbandoned,
    TradeOutcomeProduced,
)
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.infrastructure.binance_urls import (
    MAINNET_REST_URL,
    MAINNET_WS_API_URL,
    MAINNET_WS_URL,
    TESTNET_REST_URL,
    TESTNET_WS_API_URL,
    TESTNET_WS_URL,
)
from praxis.arrow_price_store import ArrowPriceStore
from praxis.paper.mark_sampler import MarkSampler
from praxis.paper.paper_report import build_paper_report
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.observability import bind_context, configure_logging
from praxis.outcome_translator import OutcomeTranslator
from praxis.infrastructure.alert_sink import AlertSink
from praxis.infrastructure.book_cache import BookCache, book_mid_price, build_price_snapshot
from praxis.infrastructure.book_poller import BookPoller
from praxis.infrastructure.secret_store import (
    Credentials,
    FileSecretStore,
    KeyringSecretStore,
    MappingSecretStore,
    SecretBackendError,
    SecretNotFoundError,
    SecretStore,
)
from praxis.infrastructure.venue_adapter import OrderBookSnapshot, VenueAdapter
from praxis.trading import Trading
from praxis.trading_config import TradingConfig

__all__ = ['InstanceConfig', 'Launcher', 'main']

_log = logging.getLogger(__name__)

_PERMISSION_QUERY_TIMEOUT = 15.0

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
_SECRETS_FILE_ENV = 'PRAXIS_SECRETS_FILE'
_DEFAULT_SHUTDOWN_TIMEOUT = '30'
_DEFAULT_HEALTHZ_PORT = 8080
_DEFAULT_DUPLICATE_WINDOW_MS = 1000
_DEFAULT_VENUE = 'binance_spot'
_DEFAULT_FEE_RATE = Decimal('0.001')
_DEFAULT_SYMBOL = 'BTCUSDT'
_LOOPBACK_HOSTS = frozenset({'127.0.0.1', '::1'})
_OPS_CLOSE_TIMEOUT_SECONDS = 60
_DEFAULT_BOOK_POLL_INTERVAL_SECONDS = 2.0
_BOOK_POLL_DEPTH_LEVELS = 5
_ALERT_WEBHOOK_TIMEOUT_SECONDS = 5


def _utc_now() -> datetime:
    '''Return the current UTC time.'''

    return datetime.now(UTC)
_DEFAULT_HEALTH_INTERVAL_SECONDS = 5.0
_DEFAULT_SNAPSHOT_INTERVAL_SECONDS = 300.0
_DEFAULT_MTM_INTERVAL_SECONDS = 30.0
_DEFAULT_MARK_SAMPLE_INTERVAL_SECONDS = 60.0
_DEFAULT_UNKNOWN_SUBMISSION_WARN_SECONDS = 60.0
_DEFAULT_UNKNOWN_SUBMISSION_SCAN_SECONDS = 15.0
_UNKNOWN_SUBMISSION_LOG_ID_LIMIT = 10


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


def _mark_sample_interval_seconds() -> int:
    '''Return the paper-metrics mark sampling cadence, in whole seconds.'''

    value = _positive_float_env(
        'PRAXIS_MARK_SAMPLE_INTERVAL_SECONDS', _DEFAULT_MARK_SAMPLE_INTERVAL_SECONDS,
    )

    if value != int(value):
        msg = (
            f'env var PRAXIS_MARK_SAMPLE_INTERVAL_SECONDS={value!r} must be a whole '
            'number of seconds'
        )
        raise RuntimeError(msg)

    return int(value)


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

    book_staleness_max_seconds = _env_positive_int('PRAXIS_BOOK_STALENESS_SECONDS')

    if (
        book_staleness_max_seconds is not None
        and book_staleness_max_seconds <= _DEFAULT_BOOK_POLL_INTERVAL_SECONDS
    ):
        msg = (
            f'PRAXIS_BOOK_STALENESS_SECONDS ({book_staleness_max_seconds}) must '
            f'exceed the book poll interval ({_DEFAULT_BOOK_POLL_INTERVAL_SECONDS}s): '
            f'at or below it the cached book is frequently older than the limit '
            f'between polls, so the price stage rejects orders with PRICE_BOOK_STALE '
            f'often enough to stall trading.'
        )
        raise ValueError(msg)

    return NexusInstanceConfig(
        account_id=praxis_inst.account_id,
        venue=_DEFAULT_VENUE,
        duplicate_window_ms=_DEFAULT_DUPLICATE_WINDOW_MS,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct=capital_pct,
        max_spread_bps=_env_positive_decimal('PRAXIS_MAX_SPREAD_BPS'),
        book_staleness_max_seconds=book_staleness_max_seconds,
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
        command_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        return await trading.submit_command(
            side=translate_order_side(side),
            order_type=translate_order_type(order_type),
            execution_mode=translate_execution_mode(execution_mode),
            maker_preference=translate_maker_preference(maker_preference),
            stp_mode=translate_stp_mode(stp_mode),
            execution_params=build_single_shot_params(execution_params),
            command_id=command_id,
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
    mode_controller: ModeController | None = None,
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
        mode_controller=mode_controller,
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


def _default_platform_snapshot(
    _context: ValidationRequestContext,
) -> PlatformLimitsStageSnapshot:
    '''Return an empty `PlatformLimitsStageSnapshot` (MMVP-lenient default).'''

    return PlatformLimitsStageSnapshot()


def _projected_position(
    positions: dict[str, Position],
    context: ValidationRequestContext,
    mid_price_provider: Callable[[str], Decimal | None],
) -> Decimal:
    '''Return the account's projected base position for the context's order.

    Sums current open positions in the order's symbol (long positive, short
    negative) and applies the pending order's signed base size, so the
    platform-limits stage gates the position the order would leave, not the
    position before it. Floored at zero.

    A quote-native order carries `order_notional` but no `order_size`, so
    its base delta is estimated as `order_notional / mid`, where `mid` is
    the cached top-of-book mid. When no mid is available the delta is zero
    (the cap degrades to gating the current position), and `order_size`
    stays `None` so the estimate never leaks onto the delivered order.
    '''

    current = sum(
        (position.size if position.side is OrderSide.BUY else -position.size
         for position in positions.values() if position.symbol == context.symbol),
        _ZERO,
    )

    if context.order_size is not None:
        delta = context.order_size

    elif context.order_notional is not None:
        mid = mid_price_provider(context.symbol)
        delta = context.order_notional / mid if mid is not None and mid > _ZERO else _ZERO

    else:
        delta = _ZERO

    if context.order_side is OrderSide.SELL:
        delta = -delta

    projected = current + delta

    return projected if projected > _ZERO else _ZERO


def _build_platform_snapshot_provider(
    positions: dict[str, Position],
    positions_lock: threading.Lock,
    mid_price_provider: Callable[[str], Decimal | None],
) -> Callable[[ValidationRequestContext], PlatformLimitsStageSnapshot]:
    '''Return a provider that projects the account position for each order.

    Args:
        positions: The account's live open positions keyed by trade_id.
        positions_lock: Guards `positions` against concurrent OutcomeLoop
            deletes; the provider runs at validation time on the strategy
            thread, outside the validator's lock, so it snapshots under this
            lock to avoid a `dictionary changed size during iteration` race.
        mid_price_provider: Maps a symbol to its cached top-of-book mid,
            used to project a quote-native order's base delta.
    '''

    def provider(context: ValidationRequestContext) -> PlatformLimitsStageSnapshot:
        with positions_lock:
            snapshot = dict(positions)

        return PlatformLimitsStageSnapshot(
            projected_position=_projected_position(snapshot, context, mid_price_provider),
        )

    return provider


def _make_book_fetch(
    venue_adapter: VenueAdapter, symbol: str,
) -> Callable[[], Awaitable[OrderBookSnapshot]]:
    '''Bind a zero-arg top-of-book fetch for one symbol.

    Binding the symbol in this factory keeps each poller's `fetch` a
    zero-arg callable (as `BookPoller` expects) and avoids the loop-variable
    late-binding that an inline closure over the loop `account` would hit.
    '''

    def fetch() -> Awaitable[OrderBookSnapshot]:
        return venue_adapter.query_order_book(symbol, limit=_BOOK_POLL_DEPTH_LEVELS)

    return fetch


def _default_price_snapshot(_context: ValidationRequestContext) -> PriceCheckSnapshot | None:
    '''Return `None`; MMVP `PriceStageLimits` are all unset.'''

    return None


def _env_positive_decimal(name: str) -> Decimal | None:
    '''Return a positive finite `Decimal` from environment variable `name`.

    Args:
        name: Environment variable holding the threshold.

    Returns:
        The parsed `Decimal`, or `None` when the variable is unset or empty.

    Raises:
        ValueError: The variable is set but is not a positive finite decimal.
    '''

    raw = os.environ.get(name)

    if not raw:
        return None

    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        msg = f'{name} must be a decimal, got {raw!r}'
        raise ValueError(msg) from exc

    if not value.is_finite() or value <= _ZERO:
        msg = f'{name} must be a positive finite decimal, got {raw!r}'
        raise ValueError(msg)

    return value


def _env_positive_int(name: str) -> int | None:
    '''Return a positive integer from environment variable `name`.

    Args:
        name: Environment variable holding the value.

    Returns:
        The parsed integer, or `None` when the variable is unset or empty.

    Raises:
        ValueError: The variable is set but is not a positive integer.
    '''

    raw = os.environ.get(name)

    if not raw:
        return None

    try:
        value = int(raw)
    except ValueError as exc:
        msg = f'{name} must be an integer, got {raw!r}'
        raise ValueError(msg) from exc

    if value <= 0:
        msg = f'{name} must be a positive integer, got {raw!r}'
        raise ValueError(msg)

    return value


async def _post_alert_webhook(url: str, payload: dict[str, Any]) -> None:
    '''POST an alert payload to the configured webhook, raising on non-2xx.'''

    async with ClientSession() as session, session.post(
        url, json=payload, timeout=ClientTimeout(total=_ALERT_WEBHOOK_TIMEOUT_SECONDS),
    ) as response:
        response.raise_for_status()


def _build_validation_pipeline(
    nexus_config: NexusInstanceConfig,
    capital_controller: CapitalController,
    *,
    health_snapshot_provider: Callable[[], HealthStageSnapshot] = (
        _default_health_snapshot
    ),
    platform_snapshot_provider: Callable[[ValidationRequestContext], PlatformLimitsStageSnapshot] = (
        _default_platform_snapshot
    ),
    price_snapshot_provider: Callable[[ValidationRequestContext], PriceCheckSnapshot | None] = (
        _default_price_snapshot
    ),
    platform_limits: PlatformLimitsStageLimits | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> ValidationPipeline:
    '''Build a six-stage `ValidationPipeline` for one account.

    Each stage closure captures stage-specific configuration that is
    derived once from `nexus_config`; mutable runtime state (health
    snapshot, platform-limits snapshot, price-check snapshot) is read on
    every call via the supplied providers.

    MMVP defaults are deliberately lenient: `RiskStageLimits` and
    `HealthStagePolicy` are constructed with all thresholds unset so each
    stage allows every action, and `PriceStageLimits` is derived from
    `nexus_config` and inherits the same all-unset posture from
    `_build_nexus_instance_config`. `PlatformLimitsStageLimits` is supplied
    by the caller (empty by default), so operator-configured platform caps
    such as `max_order_notional` are enforced when set. Operator-supplied
    limits are dialed in pre-live by passing configured limits and richer
    snapshot providers.

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
        platform_snapshot_provider: Callable returning the platform-limits
            snapshot for a request context, used to project the order's
            resulting position. Defaults to an empty snapshot.
        price_snapshot_provider: Callable returning the current
            price-check snapshot. Defaults to `None`.
        platform_limits: Operator-configured platform caps for the
            platform-limits stage. Defaults to an empty (all-unset) limit set.
        clock: Source of UTC time for the duplicate-order and order-rate
            intake hooks; a replay run injects its cursor so these gate
            on simulated time rather than wall time.

    Returns:
        Six-stage `ValidationPipeline` ready for use by `submit_actions`.
    '''

    intake_hooks = build_default_intake_hooks(nexus_config, now_fn=clock)
    risk_limits = RiskStageLimits()
    price_limits = build_price_stage_limits_from_config(nexus_config)
    platform_limits = platform_limits if platform_limits is not None else PlatformLimitsStageLimits()
    health_policy = HealthStagePolicy()

    def intake(context: ValidationRequestContext) -> ValidationDecision:
        return validate_intake_stage(context, hooks=intake_hooks)

    def risk(context: ValidationRequestContext) -> ValidationDecision:
        return validate_risk_stage(context, risk_limits)

    def price(context: ValidationRequestContext) -> ValidationDecision:
        return validate_price_stage(
            context,
            price_limits,
            price_snapshot_provider(context),
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
            platform_snapshot_provider(context),
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
    outcome_processor: OutcomeProcessor | None = None,
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
            (the latest closed-bar close from `ArrowPriceStore`) or
            `None` when no market data is available yet.
        fee_rate: Effective taker fee rate for fee estimation.
        enter_symbol: Symbol used for `ENTER` actions when the action
            itself does not carry one.
        venue_adapter: Optional venue adapter; when supplied, `ENTER`
            and `EXIT` paths route the action's qty through
            `quantize_for_command(...)` for `LOT_SIZE` / `minNotional`
            gating.
        outcome_processor: Optional `OutcomeProcessor` reference. When
            supplied, the `EXIT` rejection branch routes a full-close
            EXIT (one whose `action.size == position.size -
            position.pending_exit`) that the venue's quantizer rejects
            as sub-lot through `OutcomeProcessor.close_as_dust(...)`
            before returning `None`. Without it, the rejection branch
            keeps the legacy behavior — log + drop the action — and
            the position lingers in `state.positions`. Tests not
            exercising the dust-close path may pass `None`.

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
        outcome_processor=outcome_processor,
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
    order_side = action.direction or OrderSide.BUY

    if action.quote_qty is not None:
        order_notional = action.quote_qty
        estimated_fees = order_notional * fee_rate

        return ValidationRequestContext(
            strategy_id=strategy_id,
            action=ValidationAction.ENTER,
            symbol=enter_symbol,
            order_side=order_side,
            order_size=None,
            command_id=command_id,
            trade_id=None,
            order_notional=order_notional,
            estimated_fees=estimated_fees,
            strategy_budget=strategy_budget,
            state=state,
            config=nexus_config,
        )

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
    outcome_processor: OutcomeProcessor | None = None,
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
    command_id = action.command_id or f'cmd-{uuid.uuid4().hex}'
    remaining = position.size - position.pending_exit
    intended_full_close = action.size == remaining

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
            log_rejection = _log.info if intended_full_close else _log.warning
            log_rejection(
                'EXIT action rejected by venue filters at intake; skipping',
                extra={
                    'strategy_id': strategy_id,
                    'trade_id': trade_id,
                    'command_id': command_id,
                    'symbol': position.symbol,
                    'entry_price': str(position.entry_price),
                    'requested_size': str(action.size),
                    'reason': quantization.rejection_reason,
                    'intended_full_close': intended_full_close,
                },
            )

            if (
                intended_full_close
                and outcome_processor is not None
                and position.pending_exit == _ZERO
            ):
                # The `pending_exit == _ZERO` gate defers the dust-close
                # while a prior EXIT order is still in flight: the in-flight
                # fill will reduce `position.size` when it lands, and the
                # strategy's next tick re-evaluates against the true
                # residue. Dusting here with an in-flight EXIT would move
                # the not-yet-sold quantity into `account_dust`.
                #
                # `dust_close_id` is keyed on `trade_id` (not `command_id`)
                # so the dedup is deterministic even when `action.command_id`
                # is `None` and the launcher generates a fresh per-call
                # UUID via `f'cmd-{uuid.uuid4().hex}'`. A position can only
                # become dust once per epoch — `trade_id` is the natural
                # key for that invariant. The first successful call removes
                # the trade from `state.positions`; subsequent calls hit
                # the `trade_id not in state.positions` guard at the top
                # of this function and return `None` before reaching this
                # branch. The Nexus-side `_processed_dust_close_ids` set
                # backstops any cross-call dedup if the position lingers
                # (e.g. concurrent EXIT actions racing past the guard).
                outcome_processor.close_as_dust(
                    trade_id=trade_id,
                    reason=quantization.rejection_reason,
                    dust_close_id=f'dust-{trade_id}',
                )

            return None

        assert quantization.snapped_qty is not None
        order_size = quantization.snapped_qty

    order_notional = position.entry_price * order_size
    estimated_fees = order_notional * fee_rate
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
        intended_full_close=intended_full_close,
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

    For qty-native ENTER, the action would already have been rejected
    by `_build_enter_context`'s no-price guard, so a `None` reference
    price here means a deeper bug — logged and skipped.

    For quote-native ENTER, no reference price is required to size or
    validate the action (`quote_qty` is the spend cap), so the
    placeholder uses `Decimal('1')` as an arbitrary positive sentinel
    when neither `action.reference_price` nor the fallback is
    available. The sentinel is discarded on first fill because
    `_grow_position`'s `(old_size * old_entry_price + ...) / new_size`
    term zeroes out when `old_size == 0`.

    Idempotent via `dict.setdefault` — repeated calls are no-ops.
    '''

    ref_price = action.reference_price
    if ref_price is None:
        ref_price = fallback_price_provider()

    if ref_price is None:

        if action.quote_qty is None:
            _log.warning(
                'cannot pre-populate entry Position: no reference price',
                extra={'strategy_id': strategy_id, 'trade_id': trade_id},
            )
            return

        ref_price = Decimal('1')

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

    if validation_context.order_side is None:
        _log.warning(
            'cannot build OrderContext: validation context missing side',
            extra={'strategy_id': strategy_id, 'command_id': command_id},
        )
        return None

    is_entry = action.action_type == ActionType.ENTER

    if validation_context.order_size is None and not is_entry:
        _log.warning(
            'cannot build OrderContext: EXIT validation context missing size',
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
            is_entry=is_entry,
            intended_full_close=validation_context.intended_full_close,
        )
    except ValueError:
        _log.exception(
            'OrderContext rejected by invariants',
            extra={'strategy_id': strategy_id, 'command_id': command_id},
        )
        return None


def _order_context_from_recorded(event: OutcomeDeliveryContextRecorded) -> OrderContext:
    '''Rebuild the Nexus delivery `OrderContext` from its spine record.

    Inverse of `_append_outcome_delivery_context`'s encode; used by boot
    replay (TD-052) to recover the routing context for an unacked
    `TradeOutcomeProduced` after a restart.

    Args:
        event (OutcomeDeliveryContextRecorded): Persisted context record.

    Returns:
        OrderContext: Reconstructed delivery context.
    '''

    return OrderContext(
        command_id=event.command_id,
        strategy_id=event.strategy_id,
        trade_id=event.trade_id,
        side=OrderSide(event.side.value),
        order_size=event.order_size,
        order_notional=event.order_notional,
        estimated_fees=event.estimated_fees,
        is_entry=event.is_entry,
        intended_full_close=event.intended_full_close,
    )


def _trade_outcome_from_produced(event: TradeOutcomeProduced) -> TradeOutcome:
    '''Rebuild the Praxis `TradeOutcome` from a `TradeOutcomeProduced` record.

    Reconstructs only the fields `OutcomeTranslator.translate` consumes
    (status, `filled_qty`, `cumulative_notional`, `target_qty`,
    `created_at`, `reason`) so boot replay (TD-052) re-derives the same
    deterministic Nexus outcomes. `avg_fill_price` is the recorded VWAP
    (`cumulative_notional / filled_qty`) or None with no fills, and the
    single-shot slice counts are 1 — none of which the translator reads.

    Args:
        event (TradeOutcomeProduced): Persisted outcome record.

    Returns:
        TradeOutcome: Reconstructed Praxis outcome.
    '''

    avg_fill_price = (
        event.cumulative_notional / event.filled_qty
        if event.filled_qty > _ZERO
        else None
    )

    return TradeOutcome(
        command_id=event.command_id,
        trade_id=event.trade_id,
        account_id=event.account_id,
        status=event.status,
        target_qty=event.target_qty,
        filled_qty=event.filled_qty,
        avg_fill_price=avg_fill_price,
        slices_completed=1,
        slices_total=1,
        reason=event.reason,
        created_at=event.timestamp,
        cumulative_notional=event.cumulative_notional,
    )


def _plan_outcome_replay(
    seq_events: list[tuple[int, Event]],
    account_id: str,
    fee_rate: Decimal,
) -> list[tuple[NexusTradeOutcome, OrderContext]]:
    '''Compute the unacked Nexus outcomes to re-deliver at boot (TD-052).

    Pure planning over the spine events for one account: groups the
    recorded delivery contexts, the `TradeOutcomeProduced` events (kept
    in append order per command), and the ids already settled
    (`OutcomeAcked`, or `OutcomeReplayAbandoned` for a leg a prior boot
    could not apply). For each produced command it rebuilds the `OrderContext` and the
    Praxis `TradeOutcome` from their durable records, re-runs a fresh
    `OutcomeTranslator` to derive the deterministic Nexus `outcome_id`s,
    and returns every `(outcome, context)` pair whose id is not yet settled. A produced command with no recorded delivery context
    is skipped (logged) — it cannot be routed and is left for operator
    review. Nexus#86's durable dedup makes re-delivery of an already-
    applied (but un-acked) leg a no-op.

    Args:
        seq_events: `(seq, Event)` pairs from `EventSpine.read`.
        account_id: Account whose outcomes to plan.
        fee_rate: Translator fee rate; must match the live translator so
            replayed fill outcomes carry the same `actual_fees`.

    Returns:
        Ordered `(NexusTradeOutcome, OrderContext)` pairs to re-deliver.
    '''

    contexts_by_cmd: dict[str, OutcomeDeliveryContextRecorded] = {}
    settled_ids: set[str] = set()

    for _seq, event in seq_events:
        if event.account_id != account_id:
            continue
        if isinstance(event, OutcomeDeliveryContextRecorded):
            contexts_by_cmd[event.command_id] = event
        elif isinstance(event, (OutcomeAcked, OutcomeReplayAbandoned)):
            settled_ids.add(event.outcome_id)

    # Second pass walks `TradeOutcomeProduced` in original spine order — NOT
    # grouped per command — so an interleaved sequence (`A partial`, `B
    # filled`, `A filled`) re-delivers in the same order it was produced.
    # `OutcomeProcessor` mutates shared capital / position / risk state, so
    # cross-command order can matter. A lazily-created per-command translator
    # preserves each command's cumulative deltas and partial indexes.
    translators: dict[str, OutcomeTranslator] = {}
    contexts: dict[str, OrderContext] = {}
    skipped_no_context: set[str] = set()
    plan: list[tuple[NexusTradeOutcome, OrderContext]] = []

    for _seq, event in seq_events:
        if event.account_id != account_id or not isinstance(event, TradeOutcomeProduced):
            continue

        command_id = event.command_id
        context_event = contexts_by_cmd.get(command_id)
        if context_event is None:
            if command_id not in skipped_no_context:
                skipped_no_context.add(command_id)
                _log.warning(
                    'boot replay: produced outcome with no delivery context; '
                    'leaving unacked for operator review',
                    extra={'command_id': command_id, 'account_id': account_id},
                )
            continue

        order_context = contexts.setdefault(
            command_id, _order_context_from_recorded(context_event),
        )
        translator = translators.setdefault(
            command_id, OutcomeTranslator(fee_rate=fee_rate),
        )

        praxis_outcome = _trade_outcome_from_produced(event)
        for nexus_outcome in translator.translate(praxis_outcome):
            if nexus_outcome.outcome_id in settled_ids:
                continue
            plan.append((nexus_outcome, order_context))

    return plan


def _apply_replay_plan(
    plan: list[tuple[NexusTradeOutcome, OrderContext]],
    process_fn: Callable[[NexusTradeOutcome, OrderContext], ProcessResult],
    abandon_fn: Callable[[str, str], None],
) -> None:
    '''Apply a boot-replay plan; no leg can wedge boot, and only deterministic failures are abandoned.

    Each leg is routed through `process_fn`. The two failure modes are
    treated differently on purpose:

    - A leg that returns `ProcessResult(success=False)` is a deterministic,
      non-retryable failure (e.g. capital `order not found` because
      `reconcile_at_boot` cleared the order). It is recorded via
      `abandon_fn` (`OutcomeReplayAbandoned`) so the planner skips it on
      later boots — it would never succeed (TD-099).
    - A leg that RAISES is caught and skipped for THIS boot only, with NO
      abandon marker, because the exception may be transient (e.g. a WAL
      append failing mid-`_handle_fill` after capital/position already
      mutated). Durably abandoning it would permanently hide an outcome
      that should retry once the transient failure clears, and leave
      capital/position/risk inconsistent. It is re-planned next boot; a
      genuinely permanent raise simply re-logs and re-skips each boot
      without wedging startup.

    Catching the raise is what keeps one un-applyable leg from propagating
    out of startup and wedging the instance into a boot loop.

    Args:
        plan: `(outcome, context)` pairs from `_plan_outcome_replay`.
        process_fn: Routes one leg, returning its `ProcessResult`.
        abandon_fn: Records `(outcome_id, reason)` as abandoned.
    '''

    for nexus_outcome, order_context in plan:
        try:
            result = process_fn(nexus_outcome, order_context)
        except Exception:  # noqa: BLE001 - skip this boot (may be transient); never wedge startup
            _log.exception(
                'boot replay leg raised; skipping this boot, will retry next boot',
                extra={'outcome_id': nexus_outcome.outcome_id},
            )
            continue

        if not result.success:
            abandon_fn(
                nexus_outcome.outcome_id,
                result.error_reason or 'replay process failed',
            )


@dataclass(frozen=True)
class _UnknownSubmission:
    '''Telemetry record for a command whose handoff outcome is unknown.

    Created by `_PreRegisteredSubmission.mark_unknown` when a
    `send_command` timeout leaves a pre-registered command in limbo: it
    may still execute, so the registration is retained and a late
    outcome resolves against it, but the launcher's periodic scan warns
    about ones that linger. Cleared when any outcome for the command is
    successfully processed (an ACK proves it reached the venue
    lifecycle), and defensively on terminal cleanup in `process_outcome`
    (including the no-`OrderContext` branch).

    Args:
        command_id: The deterministic command identity.
        strategy_id: Owning strategy.
        created_at: Wall-clock UTC instant the command became unknown.
        action_type: ENTER / EXIT / etc., for the operator log.
        symbol: Trading symbol.
        side: Order side.
        order_notional: Requested notional (quote units).
        error: The timeout/cause string.
    '''

    command_id: str
    strategy_id: str
    created_at: datetime
    action_type: str
    symbol: str
    side: str
    order_notional: Decimal | None
    error: str


@dataclass
class _PreRegisteredSubmission:
    '''Lifecycle handle for a command registered before outbound handoff.

    Returned by the launcher's `pre_register` to `submit_actions`, which
    drives it as the `send_command` handoff resolves. Registering the
    strategy mapping, `OrderContext`, capital order, and position effect
    BEFORE handoff lets a fast venue's ACK/FILL resolve against state
    that already exists, closing the registration-gap race at its root.

    The handle records exactly what it inserted so `rollback` is precise
    and idempotent. `mark_unknown` retains everything (the command may
    still execute; a late outcome must resolve against it) and records
    the command in `unknown_submissions` for the launcher's reconciler.

    Args:
        command_id: The deterministic command identity.
        strategy_id: Owning strategy.
        command_strategy_ids: Registry the strategy mapping was inserted
            into.
        command_contexts: Registry the `OrderContext` was inserted into
            (only when `context_registered`).
        unknown_submissions: Registry that retains the command when the
            handoff outcome is unknown.
        capital_controller: For releasing the capital order on rollback.
        lock: `command_registry_lock` guarding the registries.
        reservation_consumed: Whether `send_order` consumed the
            reservation into a capital order (so rollback releases the
            order, not the reservation).
        context_registered: Whether an `OrderContext` was inserted.
        action_type: `ENTER` or `EXIT`, recorded into the unknown record.
        symbol: Command symbol, recorded into the unknown record.
        side: `BUY` or `SELL`, recorded into the unknown record.
        order_notional: Requested notional, recorded into the unknown
            record.
        now: Wall-clock UTC provider stamping the unknown record.
        rollback_position: Optional callable undoing the position effect
            (ENTER placeholder removal or EXIT `pending_exit` decrement).
    '''

    command_id: str
    strategy_id: str
    command_strategy_ids: dict[str, str]
    command_contexts: dict[str, OrderContext]
    unknown_submissions: dict[str, _UnknownSubmission]
    capital_controller: CapitalController
    lock: threading.Lock
    reservation_consumed: bool
    context_registered: bool
    action_type: str
    symbol: str
    side: str
    order_notional: Decimal | None
    now: Callable[[], datetime]
    rollback_position: Callable[[], None] | None = None

    def mark_submitted(self, _command_id: str) -> None:
        '''Confirm acceptance; registration already stands, nothing to do.'''

    def mark_unknown(self, error: BaseException) -> None:
        '''Retain the registration and record the command as unknown.'''

        record = _UnknownSubmission(
            command_id=self.command_id,
            strategy_id=self.strategy_id,
            created_at=self.now(),
            action_type=self.action_type,
            symbol=self.symbol,
            side=self.side,
            order_notional=self.order_notional,
            error=str(error),
        )

        with self.lock:
            self.unknown_submissions[self.command_id] = record

    def rollback(self, error: BaseException) -> None:
        '''Undo every registration effect; idempotent.

        Args:
            error: The failure that triggered the rollback (logged).
        '''

        if self.rollback_position is not None:
            self.rollback_position()

        if self.reservation_consumed:
            recover_result = self.capital_controller.recover_orphaned_order(
                self.command_id,
                'submit_failed',
            )
            if not recover_result.success:
                _log.warning(
                    'recover_orphaned_order rejected during pre-register '
                    'rollback',
                    extra={
                        'command_id': self.command_id,
                        'reason': recover_result.reason,
                    },
                )

        with self.lock:
            self.command_strategy_ids.pop(self.command_id, None)
            if self.context_registered:
                self.command_contexts.pop(self.command_id, None)
            self.unknown_submissions.pop(self.command_id, None)

        _log.warning(
            'pre-registered submission rolled back',
            extra={'command_id': self.command_id, 'reason': str(error)},
        )


@dataclass
class _PreRegisterWiring:
    '''Per-account references a pre_register callback closes over.

    Grouped so the registration logic can live in the module-level
    `_make_pre_register` factory — testable in isolation — rather than
    as an opaque closure inside `_build_nexus_runtime`.

    Args:
        pending_registrations: command_id -> (action, strategy_id, ctx),
            populated by the submitter's recording build_context so the
            callback can recover per-action metadata from `cmd` alone.
        command_strategy_ids: strategy-id registry to insert into.
        command_contexts: OrderContext registry to insert into.
        unknown_submissions: registry retaining unknown-outcome commands.
        command_registry_lock: lock guarding the three registries.
        capital_controller: for `send_order` and rollback recovery.
        state: live InstanceState for position effects.
        positions_lock: guards position / pending_exit writes.
        fallback_price_provider: ENTER placeholder pricing.
        now: wall-clock UTC provider for unknown-submission timestamps.
        append_delivery_context: durably records the `OrderContext` on the
            spine (`OutcomeDeliveryContextRecorded`) before the command is
            handed to `send_command`, so boot replay (TD-052) can rebuild
            the context after a restart. Raises on append failure so the
            submission is aborted rather than left un-replayable.
    '''

    pending_registrations: dict[str, tuple[Action, str, ValidationRequestContext]]
    command_strategy_ids: dict[str, str]
    command_contexts: dict[str, OrderContext]
    unknown_submissions: dict[str, _UnknownSubmission]
    command_registry_lock: threading.Lock
    capital_controller: CapitalController
    state: InstanceState
    positions_lock: threading.Lock
    fallback_price_provider: Callable[[], Decimal | None]
    now: Callable[[], datetime]
    append_delivery_context: Callable[[str, OrderContext], None]


def _make_pre_register(
    wiring: _PreRegisterWiring,
) -> Callable[[NexusTradeCommand, ValidationDecision], _PreRegisteredSubmission]:
    '''Build the pre-registration callback for `submit_actions`.

    The returned callable registers a command's strategy mapping,
    capital order, position effect, and `OrderContext` BEFORE the
    `send_command` handoff, keyed on the deterministic `cmd.command_id`,
    and returns a `_PreRegisteredSubmission` handle driving confirm /
    unknown / rollback.

    Args:
        wiring: The per-account references to operate on.

    Returns:
        A `pre_register(cmd, decision)` callable.
    '''

    def pre_register(
        cmd: NexusTradeCommand,
        decision: ValidationDecision,
    ) -> _PreRegisteredSubmission:
        action, strategy_id, ctx = wiring.pending_registrations[cmd.command_id]

        reservation_consumed = False

        with wiring.command_registry_lock:
            wiring.command_strategy_ids[cmd.command_id] = strategy_id

            if decision.reservation is not None:
                send_result = wiring.capital_controller.send_order(
                    decision.reservation.reservation_id,
                    cmd.command_id,
                )
                if not send_result.success:
                    wiring.command_strategy_ids.pop(cmd.command_id, None)
                    msg = (
                        f'send_order failed for {cmd.command_id}: '
                        f'{send_result.reason}'
                    )
                    raise RuntimeError(msg)
                reservation_consumed = True

        rollback_position: Callable[[], None] | None = None
        forced_trade_id: str | None = None

        # Once `send_order` consumed the reservation into a capital order,
        # every step below must be exception-safe: if one raises,
        # `submit_actions`' catch calls `_release_granted_reservation`,
        # which is a no-op for an already-consumed reservation — leaking
        # the capital order and the `command_strategy_ids` entry until
        # boot reconcile. Mirror `rollback` here (undo the position
        # effect, recover the orphaned order, pop the registries) before
        # re-raising so the cleanup contract does not depend on these
        # helpers staying raise-free.
        try:
            if action.action_type == ActionType.ENTER:
                forced_trade_id = cmd.command_id
                _ensure_entry_position(
                    state=wiring.state,
                    action=action,
                    strategy_id=strategy_id,
                    trade_id=forced_trade_id,
                    fallback_price_provider=wiring.fallback_price_provider,
                    positions_lock=wiring.positions_lock,
                )

                def rollback_position() -> None:
                    with wiring.positions_lock:
                        position = wiring.state.positions.get(cmd.command_id)
                        if position is not None and position.size == _ZERO:
                            del wiring.state.positions[cmd.command_id]

            elif (
                action.action_type == ActionType.EXIT
                and action.trade_id is not None
                and ctx.order_size is not None
            ):
                exit_trade_id = action.trade_id
                exit_size = ctx.order_size

                with wiring.positions_lock:
                    position = wiring.state.positions.get(exit_trade_id)
                    if position is not None:
                        position.pending_exit += exit_size

                def rollback_position() -> None:
                    with wiring.positions_lock:
                        position = wiring.state.positions.get(exit_trade_id)
                        if position is not None:
                            position.pending_exit -= exit_size

            # Build the OrderContext from the validator's already-captured
            # `ctx`, NOT by re-running `build_context`: this code has just
            # mutated `position.pending_exit`, and a re-run would recompute
            # `intended_full_close` (= `action.size == size - pending_exit`)
            # against the inflated value, flipping a true full-close to
            # not-full-close and breaking the dust-close path. `ctx` was
            # computed by the validator before the mutation.
            order_context = _build_order_context(
                action=action,
                strategy_id=strategy_id,
                command_id=cmd.command_id,
                build_context=lambda _action, _strategy_id: ctx,
                forced_trade_id=forced_trade_id,
            )

            context_registered = order_context is not None

            if order_context is not None:
                wiring.append_delivery_context(cmd.account_id, order_context)
                with wiring.command_registry_lock:
                    wiring.command_contexts[cmd.command_id] = order_context
        except BaseException:
            # BaseException, not Exception: a CancelledError after
            # `send_order` must still run the capital-recovery cleanup, or
            # the consumed reservation leaks. The cleanup re-raises, so
            # KeyboardInterrupt / SystemExit are not swallowed.
            if rollback_position is not None:
                rollback_position()
            if reservation_consumed:
                wiring.capital_controller.recover_orphaned_order(
                    cmd.command_id,
                    'submit_failed',
                )
            with wiring.command_registry_lock:
                wiring.command_strategy_ids.pop(cmd.command_id, None)
                wiring.command_contexts.pop(cmd.command_id, None)
            raise

        return _PreRegisteredSubmission(
            command_id=cmd.command_id,
            strategy_id=strategy_id,
            command_strategy_ids=wiring.command_strategy_ids,
            command_contexts=wiring.command_contexts,
            unknown_submissions=wiring.unknown_submissions,
            capital_controller=wiring.capital_controller,
            lock=wiring.command_registry_lock,
            reservation_consumed=reservation_consumed,
            context_registered=context_registered,
            action_type=action.action_type.value,
            symbol=cmd.symbol,
            side=cmd.side.value,
            order_notional=cmd.notional,
            now=wiring.now,
            rollback_position=rollback_position,
        )

    return pre_register


class _UnknownSubmissionMonitor:
    '''Periodically warn about commands stuck in SUBMISSION_UNKNOWN.

    A command lands in `unknown_submissions` when its `send_command`
    handoff timed out: the command may still be executing at the venue,
    so the registration is retained and a late outcome will clear it
    (`process_outcome` pops on the first successfully-processed outcome,
    including ACK). This monitor surfaces the ones that never clear —
    telemetry only, no venue query and no forced release.

    Mirrors `SnapshotScheduler`'s `threading.Timer` cadence because the
    `unknown_submissions` registry is guarded by `command_registry_lock`
    (a `threading.Lock`) and written from the `OutcomeLoop` worker
    thread.

    Args:
        unknown_submissions: The launcher's unknown-submission registry.
        lock: `command_registry_lock` guarding the registry.
        now: Wall-clock UTC provider for age computation.
        warn_seconds: Age above which a command is reported.
        scan_seconds: Seconds between scans. Must be positive.
    '''

    def __init__(
        self,
        unknown_submissions: dict[str, _UnknownSubmission],
        lock: threading.Lock,
        now: Callable[[], datetime],
        warn_seconds: float,
        scan_seconds: float,
    ) -> None:
        self._unknown_submissions = unknown_submissions
        self._lock = lock
        self._now = now
        self._warn_seconds = warn_seconds
        self._scan_seconds = scan_seconds
        self._timer: threading.Timer | None = None
        self._running = False
        self._state_lock = threading.Lock()

    @property
    def running(self) -> bool:
        '''Whether the scan loop is currently scheduling ticks.'''

        return self._running

    def start(self) -> None:
        '''Start the periodic scan loop.'''

        with self._state_lock:
            if self._running:
                return

            self._running = True
            self._schedule_locked()

    def stop(self) -> None:
        '''Stop the loop and cancel any pending scan.'''

        with self._state_lock:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def scan_once(self) -> None:
        '''Run one scan without scheduling another tick.'''

        now = self._now()

        with self._lock:
            aged = [
                record
                for record in self._unknown_submissions.values()
                if (now - record.created_at).total_seconds() >= self._warn_seconds
            ]

        if not aged:
            return

        max_age = max((now - record.created_at).total_seconds() for record in aged)
        command_ids = [record.command_id for record in aged][
            :_UNKNOWN_SUBMISSION_LOG_ID_LIMIT
        ]

        _log.warning(
            'submissions stuck in SUBMISSION_UNKNOWN',
            extra={
                'count': len(aged),
                'max_age_seconds': max_age,
                'command_ids': command_ids,
            },
        )

    def _schedule_locked(self) -> None:
        if not self._running:
            return

        self._timer = threading.Timer(self._scan_seconds, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        with self._state_lock:
            if not self._running:
                return

        try:
            self.scan_once()
        except Exception:  # noqa: BLE001 - a scan failure must not abort the loop
            _log.exception('unknown-submission scan failed; next tick will retry')

        with self._state_lock:
            self._schedule_locked()


def _resolve_mark_price_series(manifest: Manifest) -> tuple[str, int]:
    '''Resolve the OHLCV series + interval used for fallback / MTM pricing.

    The `fallback_price_provider` (ENTER reference pricing) and the
    `mark_price_provider` (mark-to-market) read closed-bar closes from
    the control-plane Arrow volume via `ArrowPriceStore.latest_close`,
    which needs a `(series, interval_seconds)` pair. Each manifest
    strategy declares its own `signal.series` / `signal.interval_seconds`;
    this resolves the single pair the launcher prices against.

    Resolution order:

    - `PRAXIS_MARK_PRICE_SERIES` set and present among the manifest
      series: use it with the matching `interval_seconds`.
    - `PRAXIS_MARK_PRICE_SERIES` set but absent from the manifest:
      require `PRAXIS_MARK_PRICE_INTERVAL_SECONDS` (positive int) and
      use that interval; raise if the var is missing or invalid.
    - `PRAXIS_MARK_PRICE_SERIES` unset and the manifest declares exactly
      one distinct series: use it.
    - `PRAXIS_MARK_PRICE_SERIES` unset and the manifest declares several
      distinct series: raise — the operator must disambiguate via
      `PRAXIS_MARK_PRICE_SERIES`.
    - No manifest series at all: raise.

    Args:
        manifest: Loaded strategy manifest.

    Returns:
        The `(series, interval_seconds)` pair to price against.

    Raises:
        RuntimeError: When the series cannot be resolved unambiguously
            or a required env var is missing or invalid.
    '''

    series_intervals: dict[str, int] = {}
    for spec in manifest.strategies:
        existing = series_intervals.get(spec.signal.series)

        if existing is not None and existing != spec.signal.interval_seconds:
            msg = (
                f'manifest declares series {spec.signal.series!r} with conflicting '
                f'interval_seconds ({existing} vs {spec.signal.interval_seconds}); '
                'cannot resolve a single mark-price interval'
            )
            raise RuntimeError(msg)

        series_intervals[spec.signal.series] = spec.signal.interval_seconds

    env_series = os.environ.get('PRAXIS_MARK_PRICE_SERIES')

    if env_series:
        if env_series in series_intervals:
            return env_series, series_intervals[env_series]

        raw_interval = os.environ.get('PRAXIS_MARK_PRICE_INTERVAL_SECONDS')
        if not raw_interval:
            msg = (
                f'PRAXIS_MARK_PRICE_SERIES={env_series!r} is not declared by any '
                'manifest strategy; set PRAXIS_MARK_PRICE_INTERVAL_SECONDS to '
                'its bar width in seconds'
            )
            raise RuntimeError(msg)

        try:
            interval = int(raw_interval)
        except ValueError as exc:
            msg = (
                f'PRAXIS_MARK_PRICE_INTERVAL_SECONDS={raw_interval!r} is not a '
                'valid integer'
            )
            raise RuntimeError(msg) from exc

        if interval <= 0:
            msg = (
                f'PRAXIS_MARK_PRICE_INTERVAL_SECONDS={raw_interval!r} must be a '
                'positive integer'
            )
            raise RuntimeError(msg)

        return env_series, interval

    if len(series_intervals) == 1:
        series, interval = next(iter(series_intervals.items()))
        return series, interval

    if len(series_intervals) > 1:
        msg = (
            'manifest declares multiple signal series '
            f'{sorted(series_intervals)!r}; set PRAXIS_MARK_PRICE_SERIES to '
            'select the one to price fallback / mark-to-market against'
        )
        raise RuntimeError(msg)

    msg = (
        'manifest declares no signal series; cannot resolve a mark-price '
        'series for fallback / mark-to-market pricing'
    )
    raise RuntimeError(msg)


def _ensure_strategies_path_importable(strategies_base_path: Path) -> None:
    '''Prepend `strategies_base_path` to `sys.path` so strategy modules import.

    Nexus's `StartupSequencer` imports each strategy implementation named
    by the manifest's `file:` field at boot; the strategy module (and any
    helper modules co-located with it) must be importable in the launcher
    process. This helper is idempotent and prepends rather than appends so
    a user-supplied module shadows any installed package of the same name.

    Operators with strategy modules outside `STRATEGIES_BASE_PATH` should
    add the extra path to `PYTHONPATH` at deploy time; the launcher does
    not enumerate alternative roots.
    '''

    resolved = str(strategies_base_path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


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


def _build_state_snapshot_locks(
    state: InstanceState,
    positions_lock: threading.Lock,
    capital_controller: CapitalController,
) -> StateSnapshotLocks:
    '''Build the `StateStore` snapshot-lock bundle, asserting lock identity.

    `serialize_state` iterates `state.positions`, `state.risk.per_strategy`,
    and `state.capital.per_strategy_deployed`. `StateStore` acquires the
    bundle's `positions_lock` + `capital_lock` around that serialization, so
    `positions_lock` only covers `state.risk.per_strategy` when it IS
    `state.risk.lock` (the same object). This is the composition point that
    holds all three objects, so the identity is enforced here — once the
    Nexus-side construction guards moved out of `ShutdownSequencer` /
    `SnapshotScheduler`, this is the single place that can catch a miswire.

    Args:
        state: The recovered instance state (its `risk.lock` must already
            be wired to `positions_lock`).
        positions_lock: The shared lock guarding `state.positions`.
        capital_controller: Source of the capital lock via `lock_cm`.

    Returns:
        A `StateSnapshotLocks` bundle for `StateStore.attach_snapshot_locks`.

    Raises:
        RuntimeError: If `state.risk.lock is not positions_lock`.
    '''

    if state.risk.lock is not positions_lock:
        msg = (
            'StateStore snapshot-lock bundle requires `state.risk.lock` to be '
            'the same object as `positions_lock` so the bundle covers '
            '`state.risk.per_strategy` serialization; got '
            f'state.risk.lock={state.risk.lock!r}, positions_lock={positions_lock!r}'
        )
        raise RuntimeError(msg)

    return StateSnapshotLocks(
        positions_lock=positions_lock,
        capital_lock=capital_controller.lock_cm(),
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


@dataclass(frozen=True)
class _PaperAccount:
    '''Per-account inputs for paper-trading metrics.

    Args:
        account_id: Trading account identifier.
        symbol: Symbol the marks and metrics apply to.
        capital_pool: Starting quote capital.
        mark_series: OHLCV series the mark price is read from.
        mark_interval: Mark series interval in seconds.
    '''

    account_id: str
    symbol: str
    capital_pool: Decimal
    mark_series: str
    mark_interval: int


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
    mode_controller: ModeController
    snapshot_scheduler: SnapshotScheduler
    mtm_loop: MtmLoop
    unknown_submission_monitor: _UnknownSubmissionMonitor
    outcome_processor: OutcomeProcessor
    process_outcome: Callable[[NexusTradeOutcome], None]
    positions_lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class _AccountOutcomeWiring:
    '''Per-account references for synchronous outcome accounting.

    Registered by `Launcher._build_nexus_runtime` once the account's
    `OutcomeProcessor` exists, and consumed by `_route_translated` (wired
    in `Launcher._start_trading`) to apply Nexus position/capital mutation
    synchronously at the Praxis outcome boundary. Without this, accounting
    is deferred behind the `OutcomeLoop` queue, which serializes it with
    strategy callbacks and action submission on a single worker — under
    load, FILLED outcomes lag behind strategy ticks and strategies act on
    stale `state.positions`.

    A regular (non-frozen) dataclass, matching `_NexusRuntime`: the
    grouped members (`command_contexts`, `unpersisted_commands`, the
    lock) are themselves mutable and mutated through this container,
    which carries them by reference.

    Args:
        outcome_processor: The account's Nexus outcome processor.
        command_contexts: Registry of in-flight `OrderContext`s by
            command_id, shared with the submitter and `process_outcome`.
        command_registry_lock: Lock guarding `command_contexts`,
            `command_strategy_ids`, and `unpersisted_commands`.
        unpersisted_commands: Command ids whose in-memory mutation has
            not yet been durably persisted, each mapped to the
            generation stamped at its most recent marking. The
            synchronous path runs on the Trading event loop, so it
            never calls `append_mutation` (a WAL write + fsync would
            block the loop that also serves the trading websocket and
            `/healthz`); it stamps the command id here instead, bumping
            `pending_generation` on every marking. The async
            `process_outcome` — running on the `OutcomeLoop` worker
            thread — checks membership on the dedup-hit redelivery,
            performs the `append_mutation` there, and withholds
            `OutcomeAcked` until it succeeds, preserving the
            withhold-ack-on-persist-failure contract that boot replay
            depends on. After a successful `append_mutation`, an id is
            discarded only when its generation still equals the one
            captured in the pre-append snapshot: a command re-marked
            after the snapshot (its new mutation blocked on
            `positions_lock` until the serialize finished, so it is NOT
            in the persisted bytes) carries a newer generation and
            survives the discard. A plain id set could not make that
            distinction — the re-mark would be an idempotent no-op and
            the discard would drop the unpersisted mutation.
        pending_generation: Monotonic counter feeding the generation
            stamps. Guarded by `command_registry_lock`.
        account_id: The owning account, for skip telemetry.
        command_strategy_ids: Registry of command_id to strategy_id,
            shared with the submitter and the `OutcomeLoop`'s
            `resolve_strategy_id`, and guarded by
            `command_registry_lock` like the other registries. Read
            here only for skip telemetry — whether a missing
            `OrderContext` coincides with a missing strategy mapping
            distinguishes the pre-registration race from a genuinely
            unknown command.
    '''

    outcome_processor: OutcomeProcessor
    command_contexts: dict[str, OrderContext]
    command_registry_lock: threading.Lock
    account_id: str
    command_strategy_ids: dict[str, str]
    unpersisted_commands: dict[str, int] = field(default_factory=dict)
    pending_generation: int = 0


class Launcher:
    '''Orchestrates Praxis + Nexus in one process.

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
        clock: Callable[[], datetime] = _utc_now,
        conduit_dir: Path | None = None,
        arrow_dir: Path | None = None,
        enforce_api_permissions: bool = False,
    ) -> None:
        if (event_spine is None) == (db_path is None):
            msg = 'Launcher requires exactly one of event_spine or db_path'
            raise ValueError(msg)

        self._enforce_api_permissions = enforce_api_permissions
        self._trading_config = trading_config
        self._instances = list(instances)
        self._event_spine = event_spine
        self._db_path = db_path
        self._db_conn: aiosqlite.Connection | None = None
        self._owns_spine = event_spine is None
        self._venue_adapter = venue_adapter
        self._healthz_port = healthz_port
        self._clock = clock
        self._conduit_dir = conduit_dir
        self._arrow_dir = arrow_dir
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._trading: Trading | None = None
        self._nexus_threads: list[threading.Thread] = []
        self._healthz_runner: web.AppRunner | None = None
        self._paper_accounts: dict[str, _PaperAccount] | None = None
        self._mark_samplers: list[MarkSampler] = []
        self._book_cache = BookCache()
        self._book_pollers: list[BookPoller] = []
        self._alert_sink = AlertSink(
            webhook_url=os.environ.get('PRAXIS_ALERT_WEBHOOK_URL'),
            post=_post_alert_webhook,
        )
        self._outcome_queues: dict[str, queue.Queue[NexusTradeOutcome]] = {}
        self._outcome_translator = OutcomeTranslator(fee_rate=_DEFAULT_FEE_RATE)
        self._account_outcome_wiring: dict[str, _AccountOutcomeWiring] = {}
        self._account_outcome_wiring_lock = threading.Lock()
        self._nexus_runtimes: dict[str, _NexusRuntime] = {}
        self._nexus_runtimes_lock = threading.Lock()

    def launch(self) -> None:
        '''Start Praxis + Nexus in one process.

        Blocks until SIGINT/SIGTERM. Handles graceful shutdown.
        '''

        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        self._start_event_loop()
        self._start_trading()
        self._assert_api_permissions()
        self._start_nexus_instances()
        self._start_healthz()
        self._start_mark_samplers()
        self._start_book_pollers()

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

    @staticmethod
    def _apply_sync_accounting(
        wiring: _AccountOutcomeWiring,
        nexus_outcome: NexusTradeOutcome,
    ) -> None:
        '''Apply Nexus position/capital mutation at the Praxis outcome boundary.

        Runs synchronously on the Trading outcome callback before the
        outcome is enqueued for the async `OutcomeLoop`, so the
        in-memory `state.positions` mutation never lags behind strategy
        ticks. The `OutcomeLoop`'s single worker serializes accounting
        with strategy callbacks and action submission; under load,
        FILLED outcomes queued there were not dequeued before the
        strategy's next tick read stale `state.positions` and dusted
        full positions via `close_as_dust`.

        Only the in-memory mutation happens here — this callback runs
        on the Trading event loop, which also serves the trading
        websocket and `/healthz`, so the WAL `append_mutation` (a
        write + fsync under the store's lock, shared with the
        `SnapshotScheduler`) must not run on it. Mutated command ids
        are recorded in `wiring.unpersisted_commands`; the async
        `process_outcome` — on the `OutcomeLoop` worker thread —
        performs the persist on the dedup-hit redelivery and withholds
        `OutcomeAcked` until it succeeds. The stale-positions race is
        closed by the synchronous state mutation, not by synchronous
        persistence.

        Outcomes whose `OrderContext` is not yet registered are skipped
        with a warning (the pre-registration race telemetry); the async
        path's unresolved-retry covers them once the submitter completes
        registration. Failures are logged and never propagate — the
        strategy-callback delivery must not be blocked by accounting
        errors.

        Args:
            wiring: Per-account outcome accounting references.
            nexus_outcome: Translated Nexus outcome to process.
        '''

        with wiring.command_registry_lock:
            order_context = wiring.command_contexts.get(nexus_outcome.command_id)
            has_strategy_mapping = (
                nexus_outcome.command_id in wiring.command_strategy_ids
            )

        if order_context is None:
            _log.warning(
                'sync accounting skipped: no OrderContext for command '
                'at outcome time; deferred to the async path '
                '(pre-registration race when has_strategy_mapping is '
                'also false and registration lands shortly after)',
                extra={
                    'account_id': wiring.account_id,
                    'command_id': nexus_outcome.command_id,
                    'outcome_id': nexus_outcome.outcome_id,
                    'outcome_type': nexus_outcome.outcome_type.value,
                    'has_strategy_mapping': has_strategy_mapping,
                },
            )
            return

        try:
            result = wiring.outcome_processor.process(nexus_outcome, order_context)
        except Exception:  # noqa: BLE001 - accounting must not break outcome delivery
            _log.exception(
                'sync outcome process raised at route boundary',
                extra={'command_id': nexus_outcome.command_id},
            )
            return

        if not result.success:
            _log.warning(
                'sync OutcomeProcessor reported failure at route boundary',
                extra={
                    'command_id': nexus_outcome.command_id,
                    'outcome_id': nexus_outcome.outcome_id,
                    'reason': result.error_reason,
                },
            )
            return

        if result.position_updated or result.capital_updated:
            with wiring.command_registry_lock:
                wiring.pending_generation += 1
                wiring.unpersisted_commands[nexus_outcome.command_id] = (
                    wiring.pending_generation
                )

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
            clock=self._clock,
            max_slippage_bps=_env_positive_decimal('PRAXIS_MAX_SLIPPAGE_BPS'),
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

            with self._account_outcome_wiring_lock:
                wiring = self._account_outcome_wiring.get(praxis_outcome.account_id)

            for nexus_outcome in translator.translate(praxis_outcome):
                if wiring is not None:
                    self._apply_sync_accounting(wiring, nexus_outcome)

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

    def _assert_api_permissions(self) -> None:
        '''
        Assert every account's API key is trade-only before order capability.

        Runs only in live mode (`enforce_api_permissions`). The SAPI
        permission endpoint is not served by the spot testnet, so paper
        and testnet skip it. On any failure the trading stack is stopped
        and the exception propagates, aborting startup before Nexus
        instances (and thus order submission) start.

        NOTE: The outer `future.result` timeout bounds the case where the
        trading event loop is wedged and the inner per-query timeout in
        `_verify_api_permissions` never gets a chance to fire; it is a
        startup backstop, not a per-query deadline.
        '''

        if not self._enforce_api_permissions:
            return

        if self._loop is None or self._trading is None:
            msg = 'trading not started'
            raise RuntimeError(msg)

        future = asyncio.run_coroutine_threadsafe(
            self._verify_api_permissions(), self._loop,
        )
        outer_timeout = _PERMISSION_QUERY_TIMEOUT * (len(self._instances) + 2)
        try:
            future.result(timeout=outer_timeout)
        except TimeoutError:
            future.cancel()
            msg = 'api key permission assertion timed out; aborting startup'
            _log.error(msg)
            raise RuntimeError(msg) from None

    async def _verify_api_permissions(self) -> None:
        '''
        Query and validate each account's API-key permissions, fail-closed.

        Reject a key that can withdraw (`enable_withdrawals is not
        False`) or cannot trade spot (`enable_spot_and_margin_trading is
        not True`); a missing or mistyped flag already raised in the
        adapter parse. On any failure stop the trading stack and re-raise.
        Log account identity and safe status only — never keys,
        signatures, or the raw authenticated response.
        '''

        assert self._trading is not None
        adapter = self._trading.venue_adapter
        try:
            for inst in self._instances:
                perms = await asyncio.wait_for(
                    adapter.query_api_permissions(inst.account_id),
                    _PERMISSION_QUERY_TIMEOUT,
                )
                if perms.enable_withdrawals is not False:
                    msg = (
                        f'account {inst.account_id!r} API key has withdrawals '
                        f'enabled; refusing to start (trade-only required)'
                    )
                    raise RuntimeError(msg)
                if perms.enable_spot_and_margin_trading is not True:
                    msg = (
                        f'account {inst.account_id!r} API key cannot trade '
                        f'spot; refusing to start'
                    )
                    raise RuntimeError(msg)
                _log.info(
                    'api key permissions verified (trade-only)',
                    extra={'account_id': inst.account_id},
                )
        except Exception:
            await self._trading.stop()
            _log.error('api key permission assertion failed; aborting startup')
            raise

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
            timestamp=self._clock(),
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

    def _append_outcome_replay_abandoned(
        self, account_id: str, outcome_id: str, reason: str,
    ) -> None:
        '''Durably mark a boot-replayed outcome that could not be applied.

        TD-052: a replayed leg that fails irrecoverably (e.g. an entry
        fill whose capital order was cleared by `reconcile_at_boot`, so
        `order_fill` returns `order not found`) would otherwise be
        re-planned and re-fail on every boot. Recording an
        `OutcomeReplayAbandoned` makes the boot-replay planner skip it on
        later boots; the underlying venue/Nexus divergence is owned by the
        boot capital reconcile (TD-097/TD-098). Best-effort, like
        `_append_outcome_acked`: a failed append just means the next boot
        re-attempts the (still-failing) leg.
        '''

        if self._loop is None or self._trading is None:
            _log.warning(
                'cannot append OutcomeReplayAbandoned: loop or trading not initialised',
                extra={'outcome_id': outcome_id, 'account_id': account_id},
            )
            return

        event = OutcomeReplayAbandoned(
            account_id=account_id,
            timestamp=self._clock(),
            outcome_id=outcome_id,
            reason=reason,
        )
        epoch_id = self._trading_config.epoch_id
        spine = self._trading.event_spine

        try:
            future = asyncio.run_coroutine_threadsafe(
                spine.append(event, epoch_id), self._loop,
            )
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - abandon-mark failure must not abort boot
            _log.exception(
                'OutcomeReplayAbandoned append failed; leg will be re-attempted next boot',
                extra={'outcome_id': outcome_id, 'account_id': account_id},
            )

    def _append_outcome_delivery_context(
        self, account_id: str, ctx: OrderContext,
    ) -> None:
        '''Durably record a command's Nexus delivery `OrderContext` on the spine.

        Appended at submit time on the Nexus submitter thread, before the
        command is handed to `send_command`, so boot replay (TD-052) can
        rebuild the `OrderContext` for an unacked outcome after a restart —
        the in-memory `command_contexts` map does not survive one. Unlike
        `_append_outcome_acked`, this RAISES on append failure so the caller
        aborts the submission (unwinding capital / registry state) rather
        than submitting a command whose outcome could never be replayed.
        '''

        if self._loop is None or self._trading is None:
            msg = (
                'cannot append OutcomeDeliveryContextRecorded: '
                'loop or trading not initialised'
            )
            raise RuntimeError(msg)

        event = OutcomeDeliveryContextRecorded(
            account_id=account_id,
            timestamp=self._clock(),
            command_id=ctx.command_id,
            side=_PraxisOrderSide(ctx.side.value),
            is_entry=ctx.is_entry,
            order_notional=ctx.order_notional,
            estimated_fees=ctx.estimated_fees,
            strategy_id=ctx.strategy_id,
            trade_id=ctx.trade_id,
            order_size=ctx.order_size,
            intended_full_close=ctx.intended_full_close,
        )
        epoch_id = self._trading_config.epoch_id
        spine = self._trading.event_spine

        future = asyncio.run_coroutine_threadsafe(
            spine.append(event, epoch_id), self._loop,
        )
        future.result(timeout=10)

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
        app.router.add_get('/metrics', self._metrics_handler)
        app.router.add_post('/ops/halt', self._ops_halt_handler)
        app.router.add_post('/ops/resume', self._ops_resume_handler)
        app.router.add_post('/ops/cancel-all', self._ops_cancel_all_handler)
        app.router.add_post('/ops/close-all', self._ops_close_all_handler)
        app.router.add_get('/ops/status', self._ops_status_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host='0.0.0.0', port=port)  # noqa: S104
        await site.start()
        return runner

    def _paper_account_map(self) -> dict[str, _PaperAccount]:
        '''Return per-account paper-metrics inputs, loaded once from manifests.'''

        if self._paper_accounts is not None:
            return self._paper_accounts

        accounts: dict[str, _PaperAccount] = {}

        for inst in self._instances:
            manifest = load_manifest(inst.manifest_path)
            mark_series, mark_interval = _resolve_mark_price_series(manifest)
            accounts[inst.account_id] = _PaperAccount(
                account_id=inst.account_id,
                symbol=_DEFAULT_SYMBOL,
                capital_pool=manifest.capital_pool,
                mark_series=mark_series,
                mark_interval=mark_interval,
            )

        self._paper_accounts = accounts

        return accounts

    async def _metrics_handler(self, request: web.Request) -> web.Response:
        '''Serve paper-trading metrics for one account from its spine events.

        Restricted to loopback callers, since it exposes PnL and fills; the
        `/healthz` route on the same listener stays open. The `account_id`
        query parameter selects the account; it defaults to the sole
        configured account when exactly one exists.
        '''

        if request.remote not in _LOOPBACK_HOSTS:
            return web.json_response({'error': 'forbidden'}, status=403)

        if self._event_spine is None:
            return web.json_response({'error': 'spine_not_initialised'}, status=503)

        accounts = self._paper_account_map()
        account_id = request.query.get('account_id')

        if account_id is None and len(accounts) == 1:
            account_id = next(iter(accounts))

        account = accounts.get(account_id) if account_id is not None else None

        if account is None:
            return web.json_response(
                {'error': 'unknown_account', 'known': sorted(accounts)}, status=404,
            )

        epoch_id = self._trading_config.epoch_id

        try:
            records = await self._event_spine.read(epoch_id)
            events = [
                event for _seq, event in records if event.account_id == account.account_id
            ]
            report = build_paper_report(
                account.capital_pool, _mark_sample_interval_seconds(), events,
            )
        except Exception:  # noqa: BLE001 - a malformed spine must not crash the handler
            _log.exception('metrics endpoint failed to build the paper report')
            return web.json_response({'error': 'metrics_unavailable'}, status=500)

        return web.json_response({'account_id': account.account_id, **report})

    def _build_mode_halt_alert(self, account_id: str) -> Callable[[str], None]:
        '''Return an on-halt callback that alerts when the account is halted.

        The callback fires on the ModeController's thread, not the event
        loop, so it schedules `AlertSink.notify` (log + webhook) onto the
        loop when one is available and falls back to the synchronous
        log-only `alert` otherwise, keeping webhook delivery best-effort
        without double-logging.
        '''

        def on_halt(source: str) -> None:
            loop = self._loop

            if loop is not None and not loop.is_closed():

                try:
                    asyncio.run_coroutine_threadsafe(
                        self._alert_sink.notify(
                            'mode_halted', severity='critical',
                            account_id=account_id, source=source,
                        ),
                        loop,
                    )
                    return
                except RuntimeError:
                    pass

            self._alert_sink.alert(
                'mode_halted', severity='critical', account_id=account_id, source=source,
            )

        return on_halt

    def _ops_auth_error(self, request: web.Request) -> web.Response | None:
        '''Return an error response when an `/ops` caller is not authorised.

        Every `/ops` route — including read-only `status` — is loopback-only
        and requires a bearer token matching `PRAXIS_OPS_TOKEN`; the routes
        stay disabled while the variable is unset.
        '''

        if request.remote not in _LOOPBACK_HOSTS:
            return web.json_response({'error': 'forbidden'}, status=403)

        token = os.environ.get('PRAXIS_OPS_TOKEN')

        if not token:
            return web.json_response({'error': 'ops_not_configured'}, status=503)

        expected = f'Bearer {token}'

        if not hmac.compare_digest(request.headers.get('Authorization', ''), expected):
            return web.json_response({'error': 'unauthorized'}, status=401)

        return None

    def _resolve_ops_runtime(
        self, request: web.Request,
    ) -> tuple[_NexusRuntime | None, web.Response | None]:
        '''Resolve the request's runtime, or an error response.

        The `account_id` query parameter selects the account; it defaults
        to the sole running account when exactly one exists. When it is
        omitted and more than one account is running the request is
        ambiguous — a 400 `account_id_required` rather than a misleading
        404 `unknown_account`.
        '''

        with self._nexus_runtimes_lock:
            runtimes = dict(self._nexus_runtimes)

        account_id = request.query.get('account_id')

        if account_id is None:

            if len(runtimes) == 1:
                return next(iter(runtimes.values())), None

            if len(runtimes) > 1:
                return None, web.json_response(
                    {'error': 'account_id_required', 'known': sorted(runtimes)}, status=400,
                )

            return None, web.json_response({'error': 'unknown_account'}, status=404)

        runtime = runtimes.get(account_id)

        if runtime is None:
            return None, web.json_response({'error': 'unknown_account'}, status=404)

        return runtime, None

    async def _ops_reason(self, request: web.Request, default: str) -> str:
        raw = await request.text()

        if not raw:
            return default

        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            return default

        reason = body.get('reason') if isinstance(body, dict) else None

        return reason if isinstance(reason, str) and reason.strip() else default

    @staticmethod
    def _ops_status_body(runtime: _NexusRuntime) -> dict[str, Any]:
        holds = runtime.state.mode_holds

        return {
            'account_id': runtime.nexus_config.account_id,
            'mode': runtime.state.mode.mode.value,
            'trigger': runtime.state.mode.trigger,
            'holds': {
                'manual': holds.manual_hold.active,
                'risk_daily_loss': holds.risk_daily_loss.active,
                'risk_drawdown': holds.risk_drawdown.active,
            },
        }

    async def _ops_status_handler(self, request: web.Request) -> web.Response:
        auth = self._ops_auth_error(request)

        if auth is not None:
            return auth

        runtime, error = self._resolve_ops_runtime(request)

        if error is not None:
            return error

        assert runtime is not None

        return web.json_response(self._ops_status_body(runtime))

    async def _ops_halt_handler(self, request: web.Request) -> web.Response:
        return await self._apply_ops_action(request, halt=True)

    async def _ops_resume_handler(self, request: web.Request) -> web.Response:
        return await self._apply_ops_action(request, halt=False)

    async def _apply_ops_action(self, request: web.Request, *, halt: bool) -> web.Response:
        auth = self._ops_auth_error(request)

        if auth is not None:
            return auth

        runtime, error = self._resolve_ops_runtime(request)

        if error is not None:
            return error

        assert runtime is not None

        account_id = runtime.nexus_config.account_id
        reason = await self._ops_reason(
            request, 'operator halt' if halt else 'operator resume',
        )

        if halt:
            runtime.mode_controller.set_manual_halt(reason)
            event: Event = OperatorHaltRequested(
                account_id=account_id, timestamp=self._clock(), reason=reason,
            )

        else:
            runtime.mode_controller.clear_manual_halt()
            event = OperatorResumeRequested(
                account_id=account_id, timestamp=self._clock(), reason=reason,
            )

        try:
            runtime.state_store.append_mutation(runtime.state)
        except Exception:  # noqa: BLE001 - a halt that is not durable must fail loudly
            _log.exception('ops action failed to persist')
            return web.json_response({'error': 'persist_failed'}, status=500)

        if self._event_spine is not None:
            try:
                await self._event_spine.append(
                    event, epoch_id=self._trading_config.epoch_id,
                )
            except Exception:  # noqa: BLE001 - the audit trail is best-effort
                _log.exception('ops audit event append failed')

        await self._alert_sink.notify(
            'operator_halt' if halt else 'operator_resume',
            severity='warning', account_id=account_id, reason=reason,
        )

        return web.json_response(self._ops_status_body(runtime))

    async def _ops_cancel_all_handler(self, request: web.Request) -> web.Response:
        auth = self._ops_auth_error(request)

        if auth is not None:
            return auth

        runtime, error = self._resolve_ops_runtime(request)

        if error is not None:
            return error

        assert runtime is not None

        account_id = runtime.nexus_config.account_id

        try:
            canceled = self._cancel_all_orders(account_id)
        except Exception:  # noqa: BLE001 - operator endpoint returns a structured error
            _log.exception('ops cancel-all failed', extra={'account_id': account_id})
            return web.json_response({'error': 'cancel_all_failed'}, status=500)

        await self._alert_sink.notify(
            'operator_cancel_all', severity='warning',
            account_id=account_id, canceled=len(canceled),
        )

        return web.json_response({'account_id': account_id, 'canceled': canceled})

    async def _ops_close_all_handler(self, request: web.Request) -> web.Response:
        auth = self._ops_auth_error(request)

        if auth is not None:
            return auth

        runtime, error = self._resolve_ops_runtime(request)

        if error is not None:
            return error

        assert runtime is not None

        account_id = runtime.nexus_config.account_id

        try:
            canceled = self._cancel_all_orders(account_id)
            closed = await self._close_all_positions(account_id)
        except Exception:  # noqa: BLE001 - operator endpoint returns a structured error
            _log.exception('ops close-all failed', extra={'account_id': account_id})
            return web.json_response({'error': 'close_all_failed'}, status=500)

        await self._alert_sink.notify(
            'operator_close_all', severity='warning',
            account_id=account_id, canceled=len(canceled), closed=len(closed),
        )

        return web.json_response(
            {'account_id': account_id, 'canceled': canceled, 'closed': closed},
        )

    def _cancel_all_orders(self, account_id: str) -> list[str]:
        '''Abort every working command for an account; returns the aborted ids.'''

        if self._trading is None:
            return []

        command_ids = {
            order.command_id
            for order in self._trading.execution_manager.get_open_orders(account_id).values()
        }
        canceled: list[str] = []

        for command_id in sorted(command_ids):

            try:
                self._trading.submit_abort(TradeAbort(
                    command_id=command_id, account_id=account_id,
                    reason='operator cancel-all', created_at=self._clock(),
                ))
            except Exception:  # noqa: BLE001 - one failed abort must not stop the rest
                _log.warning('cancel-all skipped a command', extra={'command_id': command_id})
            else:
                canceled.append(command_id)

        return canceled

    async def _close_all_positions(self, account_id: str) -> list[dict[str, str]]:
        '''Submit a market exit for every open position; returns per-trade results.'''

        if self._trading is None:
            return []

        closed: list[dict[str, str]] = []

        for (trade_id, _acct), position in self._trading.pull_positions(account_id).items():
            net = position.qty

            if net <= _ZERO:
                continue

            exit_side = (
                _PraxisOrderSide.SELL
                if position.side is _PraxisOrderSide.BUY
                else _PraxisOrderSide.BUY
            )

            try:
                command_id = await self._trading.submit_command(
                    trade_id=trade_id, account_id=account_id, symbol=position.symbol,
                    side=exit_side, qty=net, quote_qty=None,
                    order_type=OrderType.MARKET, execution_mode=ExecutionMode.SINGLE_SHOT,
                    execution_params=SingleShotParams(),
                    timeout=_OPS_CLOSE_TIMEOUT_SECONDS, reference_price=None,
                    maker_preference=MakerPreference.NO_PREFERENCE, stp_mode=_PraxisSTPMode.NONE,
                    created_at=self._clock(),
                )
            except Exception:  # noqa: BLE001 - one failed exit must not stop the rest
                _log.exception('close-all failed to submit an exit', extra={'trade_id': trade_id})
                closed.append({'trade_id': trade_id, 'error': 'submit_failed'})
            else:
                closed.append({'trade_id': trade_id, 'command_id': command_id, 'qty': str(net)})

        return closed

    def _start_mark_samplers(self) -> None:
        '''Start one paper-metrics mark sampler per account on the launcher loop.

        Best-effort: a build or start failure is logged and leaves trading
        unaffected, since the mark series is auxiliary telemetry.
        '''

        if self._loop is None or self._event_spine is None:
            return

        future = asyncio.run_coroutine_threadsafe(self._build_mark_samplers(), self._loop)

        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - metrics sampling must never abort trading
            future.cancel()
            _log.exception(
                'mark sampler startup failed; any started samplers were stopped and the build can retry',
            )
        else:
            _log.info('mark samplers started', extra={'count': len(self._mark_samplers)})

    async def _build_mark_samplers(self) -> None:
        spine = self._event_spine

        if spine is None or self._mark_samplers:
            return

        arrow_dir = self._arrow_dir or Path(os.environ.get('PRAXIS_ARROW_DIR', '/opt/arrow'))
        arrow_price_store = ArrowPriceStore(arrow_dir, clock=self._clock)
        interval = _mark_sample_interval_seconds()
        epoch_id = self._trading_config.epoch_id

        async def append(event: MarkSampled) -> None:
            await spine.append(event, epoch_id)

        samplers: list[MarkSampler] = []

        try:
            for account in self._paper_account_map().values():

                def mark_price_provider(bound: _PaperAccount = account) -> Decimal | None:
                    return arrow_price_store.latest_close(bound.mark_series, bound.mark_interval)

                sampler = MarkSampler(
                    account_id=account.account_id,
                    symbol=account.symbol,
                    mark_price_provider=mark_price_provider,
                    append=append,
                    clock=self._clock,
                    interval_seconds=interval,
                )
                samplers.append(sampler)
                sampler.start()

        except Exception:
            for sampler in samplers:
                await sampler.stop()

            raise

        self._mark_samplers = samplers

    def _stop_mark_samplers(self) -> None:
        '''Stop every mark sampler; best-effort during shutdown.'''

        if self._loop is None or not self._mark_samplers:
            return

        samplers = self._mark_samplers

        async def _stop_all() -> None:
            for sampler in samplers:
                await sampler.stop()

        future = asyncio.run_coroutine_threadsafe(_stop_all(), self._loop)

        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - best effort during shutdown
            future.cancel()
            _log.exception('mark sampler shutdown failed; keeping references for retry')
        else:
            self._mark_samplers = []

    def _build_price_snapshot_provider(
        self,
    ) -> Callable[[ValidationRequestContext], PriceCheckSnapshot | None]:
        '''Return a provider reading the cached book for the order's symbol.'''

        def provider(context: ValidationRequestContext) -> PriceCheckSnapshot | None:
            return build_price_snapshot(self._book_cache, context.symbol, self._clock())

        return provider

    def _start_book_pollers(self) -> None:
        '''Start one order-book poller per unique symbol on the launcher loop.

        Best-effort: a start failure is logged and leaves trading unaffected,
        since an absent book only makes a configured price limit reject.
        '''

        if self._loop is None or self._venue_adapter is None:
            return

        future = asyncio.run_coroutine_threadsafe(self._build_book_pollers(), self._loop)

        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - book polling must never abort trading
            future.cancel()
            _log.exception('book poller startup failed; the build can retry')
        else:
            _log.info('book pollers started', extra={'count': len(self._book_pollers)})

    async def _build_book_pollers(self) -> None:
        venue_adapter = self._venue_adapter

        if venue_adapter is None or self._book_pollers:
            return

        pollers: list[BookPoller] = []
        symbols = {account.symbol for account in self._paper_account_map().values()}

        try:
            for symbol in sorted(symbols):
                poller = BookPoller(
                    symbol=symbol,
                    fetch=_make_book_fetch(venue_adapter, symbol),
                    cache=self._book_cache,
                    clock=self._clock, interval_seconds=_DEFAULT_BOOK_POLL_INTERVAL_SECONDS,
                )
                pollers.append(poller)
                poller.start()

        except Exception:
            for poller in pollers:
                await poller.stop()

            raise

        self._book_pollers = pollers

    def _stop_book_pollers(self) -> None:
        '''Stop every book poller; best-effort during shutdown.'''

        if self._loop is None or not self._book_pollers:
            return

        pollers = self._book_pollers

        async def _stop_all() -> None:
            for poller in pollers:
                await poller.stop()

        future = asyncio.run_coroutine_threadsafe(_stop_all(), self._loop)

        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - best effort during shutdown
            future.cancel()
            _log.exception('book poller shutdown failed; keeping references for retry')
        else:
            self._book_pollers = []

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
        self._stop_mark_samplers()
        self._stop_book_pollers()

        for thread in self._nexus_threads:
            thread.join(timeout=30)

            if thread.is_alive():
                _log.warning(
                    'nexus thread did not finish within timeout',
                    extra={'thread_name': thread.name},
                )

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
            with self._nexus_runtimes_lock:
                self._nexus_runtimes[inst.account_id] = runtime
            self._start_nexus_loops(runtime)

            _log.info('nexus instance running', extra={'account_id': inst.account_id})

            self._stop_event.wait()

            with self._nexus_runtimes_lock:
                self._nexus_runtimes.pop(inst.account_id, None)

            runtime.health_loop.stop()
            runtime.mtm_loop.stop()
            runtime.snapshot_scheduler.stop()
            runtime.unknown_submission_monitor.stop()

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
                mode_controller=runtime.mode_controller,
            )
            shutdown.shutdown()

            _log.info('nexus instance stopped', extra={'account_id': inst.account_id})

        except Exception:  # noqa: BLE001 - top-level catch for thread, must not propagate
            _log.exception('nexus instance failed', extra={'account_id': inst.account_id})

            with self._nexus_runtimes_lock:
                self._nexus_runtimes.pop(inst.account_id, None)

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
        timers), and `OutcomeLoop`. The loops are built but NOT started;
        the caller starts them via `_start_nexus_loops` (the live path)
        or drives them directly (a replay run). The caller is also
        responsible for waiting on the shutdown signal and then invoking
        `ShutdownSequencer.shutdown()` on the returned runtime.

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
        capital_controller = CapitalController(state.capital, clock=self._clock)
        capital_controller.reconcile_at_boot(positions=state.positions.values())
        positions_lock = threading.Lock()
        pipeline = _build_validation_pipeline(
            nexus_instance_config, capital_controller,
            platform_snapshot_provider=_build_platform_snapshot_provider(
                state.positions, positions_lock,
                lambda symbol: book_mid_price(self._book_cache, symbol),
            ),
            platform_limits=PlatformLimitsStageLimits(
                max_order_notional=_env_positive_decimal('PRAXIS_MAX_ORDER_NOTIONAL'),
                max_position=_env_positive_decimal('PRAXIS_MAX_POSITION'),
            ),
            price_snapshot_provider=self._build_price_snapshot_provider(),
            clock=self._clock,
        )
        command_registry_lock = threading.Lock()
        if not hasattr(state.risk, 'lock'):
            msg = (
                'state.risk has no `lock` slot; FINAL-MAJOR-02 cross-thread '
                'serialization requires Nexus RiskState to expose a transient '
                'lock attribute. Refusing to boot with broken concurrency.'
            )
            raise RuntimeError(msg)
        state.risk.lock = positions_lock
        mode_controller = ModeController(
            state, positions_lock, clock=self._clock,
            risk_thresholds=manifest.risk_controls,
            on_halt=self._build_mode_halt_alert(inst.account_id),
        )
        mode_controller.reconcile()
        state_store.attach_snapshot_locks(
            _build_state_snapshot_locks(state, positions_lock, capital_controller),
        )
        capital_pct_by_strategy = {
            spec.strategy_id: spec.capital_pct for spec in manifest.strategies
        }
        conduit_dir = self._conduit_dir or Path(
            os.environ.get('PRAXIS_CONDUIT_DIR', '/opt/conduit'),
        )
        arrow_dir = self._arrow_dir or Path(
            os.environ.get('PRAXIS_ARROW_DIR', '/opt/arrow'),
        )
        arrow_price_store = ArrowPriceStore(arrow_dir, clock=self._clock)
        mark_series, mark_interval = _resolve_mark_price_series(manifest)

        # Pre-bind `outcome_processor` so the `build_context` closure below
        # captures the name safely. The real `OutcomeProcessor(...)` is
        # constructed further down in this scope and reassigns this binding
        # in place; the closure resolves names at call time, so it picks up
        # the live instance once construction has run. Without this
        # pre-bind, a future refactor that invokes `build_context` before
        # the construction line would raise `UnboundLocalError`.
        outcome_processor: OutcomeProcessor | None = None

        def context_provider(strategy_id: str) -> StrategyContext:
            return _build_strategy_context(
                sequencer.instance_state,
                sequencer.manifest,
                strategy_id,
                positions_lock=positions_lock,
            )

        def fallback_price_provider() -> Decimal | None:
            return arrow_price_store.latest_close(mark_series, mark_interval)

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
                outcome_processor=outcome_processor,
            )

        command_strategy_ids: dict[str, str] = {}
        command_contexts: dict[str, OrderContext] = {}
        unknown_submissions: dict[str, _UnknownSubmission] = {}

        def submitter(actions: list[Action], strategy_id: str) -> None:
            # `pending_registrations` is per-call, not shared: `submitter`
            # is the `action_submit` callback for PredictLoop / TimerLoop /
            # OutcomeLoop (separate threads, no shared submission lock), so a
            # module-scoped dict would race — a concurrent call clearing it
            # between this call's `recording_build_context` populate and
            # `pre_register`'s lookup. The shared registries
            # (`command_strategy_ids` / `command_contexts` /
            # `unknown_submissions`) stay shared and are guarded by
            # `command_registry_lock`.
            pending_registrations: dict[
                str, tuple[Action, str, ValidationRequestContext]
            ] = {}

            def recording_build_context(
                action: Action,
                inner_strategy_id: str,
            ) -> ValidationRequestContext | None:
                ctx = build_context(action, inner_strategy_id)

                if ctx is not None and ctx.command_id is not None:
                    pending_registrations[ctx.command_id] = (
                        action,
                        inner_strategy_id,
                        ctx,
                    )

                return ctx

            pre_register = (
                _make_pre_register(
                    _PreRegisterWiring(
                        pending_registrations=pending_registrations,
                        command_strategy_ids=command_strategy_ids,
                        command_contexts=command_contexts,
                        unknown_submissions=unknown_submissions,
                        command_registry_lock=command_registry_lock,
                        capital_controller=capital_controller,
                        state=state,
                        positions_lock=positions_lock,
                        fallback_price_provider=fallback_price_provider,
                        now=self._clock,
                        append_delivery_context=self._append_outcome_delivery_context,
                    ),
                )
                if praxis_outbound.supports_command_id
                else None
            )

            results = submit_actions(
                actions,
                strategy_id=strategy_id,
                config=nexus_instance_config,
                praxis_outbound=praxis_outbound,
                validator=pipeline,
                build_context=recording_build_context,
                now=self._clock,
                capital_controller=capital_controller,
                positions_lock=positions_lock,
                pre_register=pre_register,
            )

            if praxis_outbound.supports_command_id:
                return

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

        wiring = _AccountOutcomeWiring(
            outcome_processor=outcome_processor,
            command_contexts=command_contexts,
            command_registry_lock=command_registry_lock,
            account_id=inst.account_id,
            command_strategy_ids=command_strategy_ids,
        )
        with self._account_outcome_wiring_lock:
            self._account_outcome_wiring[inst.account_id] = wiring

        def _process_nexus_outcome(
            outcome: NexusTradeOutcome,
            order_context: OrderContext,
            *,
            source: str,
        ) -> ProcessResult:
            result = outcome_processor.process(outcome, order_context)
            if not result.success:
                _log.warning(
                    'OutcomeProcessor reported failure',
                    extra={
                        'command_id': outcome.command_id,
                        'outcome_type': result.outcome_type.value,
                        'error': result.error_reason,
                        'source': source,
                    },
                )
            else:
                with command_registry_lock:
                    unknown_submissions.pop(outcome.command_id, None)

            if outcome.outcome_type.is_terminal:
                with command_registry_lock:
                    command_contexts.pop(outcome.command_id, None)
                    command_strategy_ids.pop(outcome.command_id, None)
                    unknown_submissions.pop(outcome.command_id, None)
                if (
                    order_context.is_entry
                    and order_context.trade_id is not None
                ):
                    with positions_lock:
                        pos = state.positions.get(order_context.trade_id)
                        if pos is not None and pos.size == _ZERO:
                            del state.positions[order_context.trade_id]

            with command_registry_lock:
                sync_persist_pending = outcome.command_id in wiring.unpersisted_commands

            mutation_persisted = True
            if result.success and (
                result.position_updated
                or result.capital_updated
                or sync_persist_pending
            ):
                # `sync_persist_pending` covers the dedup seam between the
                # synchronous route-boundary path and this consumer:
                # `_apply_sync_accounting` mutates in-memory state but
                # never persists (the WAL fsync must stay off the Trading
                # event loop), so the dedup-hit redelivery here reports no
                # mutation flags — without the pending check the persist
                # below would be skipped and the ack would fire for a
                # mutation that was never durably persisted, which boot
                # replay would then skip.
                #
                # The snapshot is captured before the append begins: any
                # id present at capture had its in-memory mutation applied
                # before the capture (same-thread ordering in
                # `_apply_sync_accounting`), so the serialize below
                # includes it. Generations are captured with the ids so
                # the post-persist discard can tell a re-marked command
                # apart from a stale entry.
                with command_registry_lock:
                    pending_persist_snapshot = dict(wiring.unpersisted_commands)

                try:
                    # `state_store` acquires `positions_lock` + the capital
                    # lock itself (its `StateSnapshotLocks` bundle) around the
                    # serialize, keeping it mutually exclusive with
                    # `_apply_sync_accounting`'s in-memory mutations on the
                    # trading thread — `state.positions` / `state.account_dust`
                    # are dict-iterated during encoding and a concurrent insert
                    # would tear the snapshot. Wrapping here too would
                    # re-acquire the non-reentrant `positions_lock` and
                    # self-deadlock.
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
                else:
                    # Discard an id only when its generation still equals
                    # the snapshotted one. A command re-marked after the
                    # snapshot carries a newer generation: its fresh
                    # mutation blocked on `positions_lock` until the
                    # serialize finished, so it is NOT in the persisted
                    # bytes and must stay pending. Equality (not mere
                    # membership) is what protects the same-command
                    # remutation window — a plain id discard would treat
                    # the idempotent re-mark as already persisted.
                    with command_registry_lock:
                        for cmd_id, generation in pending_persist_snapshot.items():
                            if wiring.unpersisted_commands.get(cmd_id) == generation:
                                del wiring.unpersisted_commands[cmd_id]

            if result.success and mutation_persisted:
                self._append_outcome_acked(inst.account_id, outcome.outcome_id)

            return result

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
                        unknown_submissions.pop(outcome.command_id, None)
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

            _process_nexus_outcome(outcome, order_context, source='live')

        def _replay_unacked_outcomes() -> None:
            '''Re-deliver TradeOutcomeProduced events with no matching OutcomeAcked.

            TD-052 boot replay: a process kill between a
            `TradeOutcomeProduced` spine append and the Nexus callback
            leaves the outcome durably recorded but never applied. This
            reads the spine, re-derives the deterministic Nexus
            `outcome_id`s for each produced outcome (fresh translator per
            command, append order), subtracts the `OutcomeAcked` ids
            already recorded, and re-routes the missing legs through the
            same `_process_nexus_outcome` path. Nexus#86's durable dedup
            makes a leg that was actually applied (but un-acked) a no-op,
            so this is an at-least-once delivery retry, not a second
            mutation.
            '''

            if self._loop is None or self._trading is None:
                _log.warning('cannot run boot replay: loop or trading not initialised')
                return

            epoch_id = self._trading_config.epoch_id
            spine = self._trading.event_spine
            future = asyncio.run_coroutine_threadsafe(spine.read(epoch_id), self._loop)
            seq_events = future.result(timeout=30)

            plan = _plan_outcome_replay(seq_events, inst.account_id, _DEFAULT_FEE_RATE)

            def _abandon(outcome_id: str, reason: str) -> None:
                self._append_outcome_replay_abandoned(
                    inst.account_id, outcome_id, reason,
                )

            _apply_replay_plan(
                plan,
                lambda outcome, ctx: _process_nexus_outcome(
                    outcome, ctx, source='boot_replay',
                ),
                _abandon,
            )

            if plan:
                _log.info(
                    'boot replay re-delivered unacked outcomes',
                    extra={'account_id': inst.account_id, 'replayed': len(plan)},
                )

        _replay_unacked_outcomes()

        sequencer.drain_pending_startup_actions(submitter)

        predict_loop = PredictLoop(
            runner=runner,
            signal_bindings=sequencer.signal_bindings,
            context_provider=context_provider,
            action_submit=submitter,
            conduit_dir=conduit_dir,
            arrow_dir=arrow_dir,
            clock=self._clock,
        )

        timer_loop: TimerLoop | None = None

        if sequencer.timer_specs:
            timer_loop = TimerLoop(
                runner=runner,
                strategy_timers=sequencer.timer_specs,
                context_provider=context_provider,
                action_submit=submitter,
            )

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

        health_loop = _build_health_loop(
            trading=self._trading,
            state=state,
            account_id=inst.account_id,
            state_store=state_store,
            mode_controller=mode_controller,
        )

        snapshot_interval = _positive_float_env(
            'NEXUS_SNAPSHOT_INTERVAL_SECONDS',
            _DEFAULT_SNAPSHOT_INTERVAL_SECONDS,
        )
        snapshot_scheduler = SnapshotScheduler(
            state_store=state_store,
            state=state,
            interval_seconds=snapshot_interval,
        )

        mtm_interval = _positive_float_env(
            'NEXUS_MTM_INTERVAL_SECONDS',
            _DEFAULT_MTM_INTERVAL_SECONDS,
        )

        def mark_price_provider(symbol: str) -> Decimal | None:
            if symbol != _DEFAULT_SYMBOL:
                return None

            return arrow_price_store.latest_close(mark_series, mark_interval)

        mtm_loop = MtmLoop(
            state=state,
            mark_price_provider=mark_price_provider,
            interval_seconds=mtm_interval,
            positions_lock=positions_lock,
        )

        unknown_warn_seconds = _positive_float_env(
            'NEXUS_UNKNOWN_SUBMISSION_WARN_SECONDS',
            _DEFAULT_UNKNOWN_SUBMISSION_WARN_SECONDS,
        )
        unknown_scan_seconds = _positive_float_env(
            'NEXUS_UNKNOWN_SUBMISSION_SCAN_SECONDS',
            _DEFAULT_UNKNOWN_SUBMISSION_SCAN_SECONDS,
        )
        unknown_submission_monitor = _UnknownSubmissionMonitor(
            unknown_submissions=unknown_submissions,
            lock=command_registry_lock,
            now=self._clock,
            warn_seconds=unknown_warn_seconds,
            scan_seconds=unknown_scan_seconds,
        )

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
            mode_controller=mode_controller,
            snapshot_scheduler=snapshot_scheduler,
            mtm_loop=mtm_loop,
            unknown_submission_monitor=unknown_submission_monitor,
            outcome_processor=outcome_processor,
            process_outcome=process_outcome,
            positions_lock=positions_lock,
        )

    def _start_nexus_loops(self, runtime: _NexusRuntime) -> None:
        '''Start the realtime loops of a built runtime (the live path).

        A replay run skips this and drives `runtime.predict_loop`
        synchronously via `tick_once` instead.
        '''

        runtime.predict_loop.start()

        if runtime.timer_loop is not None:
            runtime.timer_loop.start()

        runtime.outcome_loop.start()
        runtime.health_loop.start()
        runtime.snapshot_scheduler.start()
        runtime.mtm_loop.start()
        runtime.unknown_submission_monitor.start()


def _check_required_env(env: dict[str, str]) -> None:
    '''Raise if any required env var is missing or empty.'''

    missing = [name for name in _REQUIRED_ENV_VARS if not env.get(name)]
    if missing:
        msg = f'missing required env vars: {", ".join(missing)}'
        raise RuntimeError(msg)


def _resolve_trade_mode(env: dict[str, str]) -> tuple[str, str, str]:
    '''Map `TRADE_MODE` to the venue REST / WS-stream / WS-API URLs.

    Operators set `TRADE_MODE=paper` or `TRADE_MODE=live`; all three URLs
    are derived from the in-code constants in `binance_urls`. There is no
    operator path that can submit orders to mainnet while the rest of the
    system thinks it is on testnet (MAJOR-001).

    `BINSIM_URL` is an optional paper-mode override pointing at an
    in-process binsim instance (`http://host:port`). When set under
    `TRADE_MODE=paper`, all three venue URLs are derived from it (REST
    stays http(s)://, WS endpoints become ws(s)://). Binsim is a fully
    internal venue, so its orders never reach a real venue and
    MAJOR-001's order-routing invariant (orders submitted to mainnet
    only when the system as a whole is in live mode) is preserved.
    Mixing `BINSIM_URL` with `TRADE_MODE=live` is a hard error: it would
    silently divert mainnet flow at the URL layer.
    '''

    raw = env['TRADE_MODE'].strip().lower()
    binsim_url = env.get('BINSIM_URL', '').strip()

    if raw == _TRADE_MODE_PAPER:
        if binsim_url:
            return _derive_binsim_urls(binsim_url)

        return TESTNET_REST_URL, TESTNET_WS_URL, TESTNET_WS_API_URL

    if raw == _TRADE_MODE_LIVE:
        if binsim_url:
            msg = 'BINSIM_URL must not be set when TRADE_MODE=live'
            raise RuntimeError(msg)

        return MAINNET_REST_URL, MAINNET_WS_URL, MAINNET_WS_API_URL

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

    venue_rest_url, venue_ws_url, venue_ws_api_url = _resolve_trade_mode(env)
    trade_mode = env['TRADE_MODE'].strip().lower()

    manifests_dir = Path(env['MANIFESTS_DIR'])
    state_base = Path(env['STATE_BASE'])
    epoch_id = int(env['EPOCH_ID'])
    strategies_base_path = Path(env['STRATEGIES_BASE_PATH'])
    strategy_state_base_raw = env.get('STRATEGY_STATE_BASE')
    strategy_state_base = Path(strategy_state_base_raw) if strategy_state_base_raw else None

    manifest_paths = _enumerate_manifests(manifests_dir)

    paper_credentials: dict[str, Credentials] = {}
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

        if trade_mode == _TRADE_MODE_PAPER:
            api_key = env.get(f'BINANCE_API_KEY_{suffix}')
            api_secret = env.get(f'BINANCE_API_SECRET_{suffix}')

            if not api_key or not api_secret:
                msg = (
                    f'missing BINANCE_API_KEY_{suffix} or BINANCE_API_SECRET_{suffix} '
                    f'for account {account_id!r} (manifest {manifest_path})'
                )
                raise RuntimeError(msg)

            paper_credentials[account_id] = Credentials(
                api_key=api_key,
                api_secret=api_secret,
            )

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

    if trade_mode == _TRADE_MODE_LIVE:
        secrets_file = env.get(_SECRETS_FILE_ENV, '').strip()
        if secrets_file:
            secret_store: SecretStore = FileSecretStore(Path(secrets_file))
        else:
            secret_store = KeyringSecretStore()
    else:
        secret_store = MappingSecretStore(paper_credentials)

    account_credentials: dict[str, Credentials] = {}
    for inst in instances:
        try:
            account_credentials[inst.account_id] = secret_store.get(inst.account_id)
        except (SecretNotFoundError, SecretBackendError) as exc:
            msg = f'failed to resolve credentials for account {inst.account_id!r}'
            raise RuntimeError(msg) from exc

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
        enforce_api_permissions=trade_mode == _TRADE_MODE_LIVE,
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
