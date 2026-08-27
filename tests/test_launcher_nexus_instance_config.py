'''Tests for `_build_nexus_instance_config` (PT.1.4.1).'''

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nexus.core.stp_mode import STPMode

from praxis.launcher import (
    InstanceConfig,
    _build_live_limit_profile,
    _build_nexus_instance_config,
)


def _stub_strategy_spec(
    strategy_id: str,
    capital_pct: Decimal,
    max_price_deviation_bps: Decimal | None = None,
) -> MagicMock:
    spec = MagicMock()
    spec.strategy_id = strategy_id
    spec.capital_pct = capital_pct
    spec.max_price_deviation_bps = max_price_deviation_bps
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

        cfg = _build_nexus_instance_config(
            _praxis_instance('acct-001'), manifest, _build_live_limit_profile(live=False),
        )

        assert cfg.account_id == 'acct-001'

    def test_price_limits_default_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv('PRAXIS_MAX_SPREAD_BPS', raising=False)
        monkeypatch.delenv('PRAXIS_BOOK_STALENESS_SECONDS', raising=False)
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert cfg.max_spread_bps is None
        assert cfg.book_staleness_max_seconds is None

    def test_price_limits_read_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('PRAXIS_MAX_SPREAD_BPS', '25')
        monkeypatch.setenv('PRAXIS_BOOK_STALENESS_SECONDS', '5')
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert cfg.max_spread_bps == Decimal('25')
        assert cfg.book_staleness_max_seconds == 5

    def test_book_staleness_at_or_below_poll_interval_rejected(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv('PRAXIS_BOOK_STALENESS_SECONDS', '2')
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        with pytest.raises(ValueError, match='must exceed the book poll interval'):
            _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

    def test_book_staleness_above_poll_interval_accepted(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv('PRAXIS_BOOK_STALENESS_SECONDS', '3')
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert cfg.book_staleness_max_seconds == 3

    def test_venue_defaults_to_binance_spot(self) -> None:
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert cfg.venue == 'binance_spot'

    def test_stp_mode_defaults_to_cancel_taker(self) -> None:
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert cfg.stp_mode == STPMode.CANCEL_TAKER

    def test_duplicate_window_default(self) -> None:
        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert cfg.duplicate_window_ms == 1000

    def test_no_stage3_thresholds_set(self) -> None:
        '''MMVP defaults leave Stage-3 price/spread/staleness thresholds unset.'''

        manifest = _stub_manifest((_stub_strategy_spec('s', Decimal('100')),))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

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

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert dict(cfg.capital_pct) == {
            'strat_a': Decimal('60'),
            'strat_b': Decimal('40'),
        }

    def test_capital_pct_empty_when_no_strategies(self) -> None:
        '''Empty capital_pct is allowed; unknown strategy_id rejection is intake-stage concern.'''

        manifest = _stub_manifest(())

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert dict(cfg.capital_pct) == {}

    def test_price_deviation_map_mirrors_manifest_caps(self) -> None:
        '''Per-strategy deviation caps mirror manifest specs and arm origo_mid.'''

        manifest = _stub_manifest((
            _stub_strategy_spec('strat_a', Decimal('60'), Decimal('50')),
            _stub_strategy_spec('strat_b', Decimal('40'), Decimal('120')),
        ))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert dict(cfg.price_deviation_max_bps_by_strategy) == {
            'strat_a': Decimal('50'),
            'strat_b': Decimal('120'),
        }
        assert cfg.reference_price_source == 'origo_mid'

    def test_price_deviation_map_skips_strategies_without_cap(self) -> None:
        '''A strategy without a declared cap is absent from the map.'''

        manifest = _stub_manifest((
            _stub_strategy_spec('strat_a', Decimal('60'), Decimal('50')),
            _stub_strategy_spec('strat_b', Decimal('40')),
        ))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert dict(cfg.price_deviation_max_bps_by_strategy) == {
            'strat_a': Decimal('50'),
        }
        assert cfg.reference_price_source == 'origo_mid'

    def test_price_deviation_map_empty_leaves_source_unset(self) -> None:
        '''No declared caps leaves the map empty and the source unset.'''

        manifest = _stub_manifest((
            _stub_strategy_spec('strat_a', Decimal('60')),
            _stub_strategy_spec('strat_b', Decimal('40')),
        ))

        cfg = _build_nexus_instance_config(
            _praxis_instance(), manifest, _build_live_limit_profile(live=False),
        )

        assert dict(cfg.price_deviation_max_bps_by_strategy) == {}
        assert cfg.reference_price_source is None
