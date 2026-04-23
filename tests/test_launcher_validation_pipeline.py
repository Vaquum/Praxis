'''Tests for `_build_validation_pipeline` (PT.1.4.2).'''

from __future__ import annotations

from decimal import Decimal

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.enums import OrderSide
from nexus.core.domain.instance_state import InstanceState
from nexus.core.stp_mode import STPMode
from nexus.core.validator import (
    HealthStageSnapshot,
    PriceCheckSnapshot,
    PriceStageLimits,
    ValidationAction,
    ValidationDecision,
    ValidationPipeline,
    ValidationRequestContext,
    ValidationStage,
)
from nexus.instance_config import InstanceConfig as NexusInstanceConfig

from praxis.launcher import _build_validation_pipeline


def _nexus_config(
    *,
    duplicate_window_ms: int = 1000,
    book_staleness_max_seconds: int | None = None,
    max_spread_bps: Decimal | None = None,
) -> NexusInstanceConfig:
    return NexusInstanceConfig(
        account_id='acct-test',
        venue='binance_spot',
        duplicate_window_ms=duplicate_window_ms,
        stp_mode=STPMode.CANCEL_TAKER,
        capital_pct={'strat_a': Decimal('100')},
        book_staleness_max_seconds=book_staleness_max_seconds,
        max_spread_bps=max_spread_bps,
    )


def _instance_state() -> InstanceState:
    return InstanceState(capital=CapitalState(capital_pool=Decimal('10000')))


def _capital_controller() -> CapitalController:
    return CapitalController(CapitalState(capital_pool=Decimal('10000')))


def _enter_context(
    *,
    config: NexusInstanceConfig,
    state: InstanceState,
    command_id: str = 'cmd_1',
    order_notional: Decimal = Decimal('100'),
    strategy_budget: Decimal = Decimal('1000'),
) -> ValidationRequestContext:
    return ValidationRequestContext(
        strategy_id='strat_a',
        action=ValidationAction.ENTER,
        symbol='BTCUSDT',
        order_side=OrderSide.BUY,
        order_size=Decimal('0.001'),
        command_id=command_id,
        order_notional=order_notional,
        estimated_fees=Decimal('0.1'),
        strategy_budget=strategy_budget,
        state=state,
        config=config,
    )


class TestBuildValidationPipeline:

    def test_returns_validation_pipeline_with_all_six_stages(self) -> None:
        pipeline = _build_validation_pipeline(_nexus_config(), _capital_controller())

        assert isinstance(pipeline, ValidationPipeline)
        assert set(pipeline.stage_order) == set(ValidationStage)

    def test_enter_allow_path_with_mmvp_defaults(self) -> None:
        '''ENTER passes all six MMVP-lenient stages and returns allowed.'''

        config = _nexus_config()
        state = _instance_state()
        pipeline = _build_validation_pipeline(config, _capital_controller())

        decision = pipeline.validate(
            _enter_context(config=config, state=state),
        )

        assert decision.allowed
        assert decision.reservation is not None

    def test_capital_stage_denies_when_pool_insufficient_for_reservation(self) -> None:
        '''Capital stage denies when reservation notional exceeds the pool.

        Strategy budget is large enough to pass intake; the deny comes
        from `CapitalController.check_and_reserve` refusing because the
        account capital pool cannot cover the requested notional.
        '''

        config = _nexus_config()
        state = _instance_state()
        controller = CapitalController(CapitalState(capital_pool=Decimal('10')))
        pipeline = _build_validation_pipeline(config, controller)

        decision = pipeline.validate(
            _enter_context(
                config=config,
                state=state,
                order_notional=Decimal('1000000'),
                strategy_budget=Decimal('1000000'),
            ),
        )

        assert not decision.allowed
        assert decision.failed_stage == ValidationStage.CAPITAL

    def test_intake_stage_denies_duplicate_command_id(self) -> None:
        '''Duplicate-order intake hook short-circuits second submission.'''

        config = _nexus_config()
        state = _instance_state()
        pipeline = _build_validation_pipeline(config, _capital_controller())

        first = pipeline.validate(_enter_context(config=config, state=state))
        second = pipeline.validate(_enter_context(config=config, state=state))

        assert first.allowed
        assert not second.allowed
        assert second.failed_stage == ValidationStage.INTAKE
        assert second.reason_code == 'INTAKE_DUPLICATE_ORDER_WINDOW'

    def test_price_stage_uses_provider_when_limits_configured(self) -> None:
        '''Price snapshot provider is consulted on every validate call.'''

        config = _nexus_config(
            book_staleness_max_seconds=5,
            max_spread_bps=Decimal('25'),
        )
        state = _instance_state()

        snapshots: list[PriceCheckSnapshot] = []

        def provider() -> PriceCheckSnapshot:
            snapshot = PriceCheckSnapshot(
                now_ms=1_700_000_000_000,
                book_timestamp_ms=1_700_000_000_000,
                spread_bps=Decimal('5'),
            )
            snapshots.append(snapshot)
            return snapshot

        pipeline = _build_validation_pipeline(
            config,
            _capital_controller(),
            price_snapshot_provider=provider,
        )

        decision = pipeline.validate(_enter_context(config=config, state=state))

        assert decision.allowed
        assert len(snapshots) == 1

    def test_price_stage_denies_when_spread_exceeds_limit(self) -> None:
        config = _nexus_config(max_spread_bps=Decimal('10'))
        state = _instance_state()

        def provider() -> PriceCheckSnapshot:
            return PriceCheckSnapshot(spread_bps=Decimal('25'))

        pipeline = _build_validation_pipeline(
            config,
            _capital_controller(),
            price_snapshot_provider=provider,
        )

        decision = pipeline.validate(_enter_context(config=config, state=state))

        assert not decision.allowed
        assert decision.failed_stage == ValidationStage.PRICE

    def test_default_price_stage_passes_when_limits_unset(self) -> None:
        '''MMVP `PriceStageLimits` defaults skip price checks entirely.'''

        config = _nexus_config()
        price_limits = PriceStageLimits()

        assert price_limits.max_staleness_ms is None
        assert price_limits.max_spread_bps is None
        assert price_limits.max_deviation_bps is None

        pipeline = _build_validation_pipeline(config, _capital_controller())

        decision = pipeline.validate(
            _enter_context(config=config, state=_instance_state()),
        )

        assert decision.allowed

    def test_health_provider_invoked_per_validate_call(self) -> None:
        '''Health snapshot provider is called once per pipeline validation.'''

        calls = {'n': 0}

        def provider() -> HealthStageSnapshot:
            calls['n'] += 1
            return HealthStageSnapshot(
                latency_ms=Decimal(0),
                consecutive_failures=Decimal(0),
                failure_rate=Decimal(0),
                rate_limit_headroom=Decimal(1),
                clock_drift_ms=Decimal(0),
            )

        config = _nexus_config()
        pipeline = _build_validation_pipeline(
            config,
            _capital_controller(),
            health_snapshot_provider=provider,
        )

        pipeline.validate(_enter_context(config=config, state=_instance_state()))
        pipeline.validate(
            _enter_context(
                config=config,
                state=_instance_state(),
                command_id='cmd_2',
            ),
        )

        assert calls['n'] == 2


def test_decision_type_returned_is_validation_decision() -> None:
    '''Pipeline returns a ValidationDecision (sanity check).'''

    config = _nexus_config()
    pipeline = _build_validation_pipeline(config, _capital_controller())

    result = pipeline.validate(
        _enter_context(config=config, state=_instance_state()),
    )

    assert isinstance(result, ValidationDecision)
