'''Tests for `_build_nexus_instance_config` (PT.1.4.1).'''

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from nexus.core.stp_mode import STPMode

from praxis.launcher import (
    InstanceConfig,
    _build_nexus_instance_config,
)


def _stub_strategy_spec(strategy_id: str, capital_pct: Decimal) -> MagicMock:
    spec = MagicMock()
    spec.strategy_id = strategy_id
    spec.capital_pct = capital_pct
    return spec


def _stub_manifest(strategies: tuple[MagicMock, ...]) -> MagicMock:
    m = MagicMock()
    m.account_id = 'acct-test'
    m.allocated_capital = Decimal('100000')
    m.capital_pool = Decimal('10000')
    m.strategies = strategies
    return m


def _praxis_instance(account_id: str = 'acct-test') -> InstanceConfig:
    return InstanceConfig(
        account_id=account_id,
        manifest_path=Path('/placeholder/manifest.yaml'),
        strategies_base_path=Path('/placeholder/strategies'),
        state_dir=Path('/placeholder/state'),
    )


class TestBuildNexusInstanceConfig:

    def test_account_id_propagated_from_praxis_inst(self) -> None:
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(_praxis_instance('acct-001'), manifest)

        assert cfg.account_id == 'acct-001'

    def test_venue_defaults_to_binance_spot(self) -> None:
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(_praxis_instance(), manifest)

        assert cfg.venue == 'binance_spot'

    def test_stp_mode_defaults_to_cancel_taker(self) -> None:
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(_praxis_instance(), manifest)

        assert cfg.stp_mode == STPMode.CANCEL_TAKER

    def test_duplicate_window_default(self) -> None:
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(_praxis_instance(), manifest)

        assert cfg.duplicate_window_ms == 1000

    def test_no_stage3_thresholds_set(self) -> None:
        '''MMVP defaults leave Stage-3 price/spread/staleness thresholds unset.'''

        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(_praxis_instance(), manifest)

        assert cfg.max_order_rate is None
        assert cfg.book_staleness_max_seconds is None
        assert cfg.max_spread_bps is None
        assert cfg.price_deviation_max_bps is None
        assert cfg.reference_price_source is None

    def test_capital_pct_mirrors_manifest(self) -> None:
        '''Per-strategy capital_pct mapping mirrors manifest spec percentages.'''

        manifest = _stub_manifest((
            _stub_strategy_spec('strat_a', Decimal('60')),
            _stub_strategy_spec('strat_b', Decimal('40')),
        ))

        cfg = _build_nexus_instance_config(_praxis_instance(), manifest)

        assert dict(cfg.capital_pct) == {
            'strat_a': Decimal('60'),
            'strat_b': Decimal('40'),
        }

    def test_capital_pct_empty_when_no_strategies(self) -> None:
        manifest = _stub_manifest(())

        # Nexus InstanceConfig requires at least one validation pass; an
        # empty capital_pct map is valid (intake stage handles unknown
        # strategy_id rejection elsewhere).
        cfg = _build_nexus_instance_config(_praxis_instance(), manifest)

        assert dict(cfg.capital_pct) == {}
