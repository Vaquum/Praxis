'''Tests for the live mandatory-limit profile (WP-Praxis-0010 live cutover).

On `TRADE_MODE=live` every deployment limit cap must be set and each manifest
must arm the account loss breakers; the boot fails closed otherwise. On paper
the caps stay optional.
'''

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nexus.core.domain.risk_breaker_thresholds import RiskBreakerThresholds

from praxis.launcher import (
    _LIVE_LIMIT_ENV_VARS,
    Launcher,
    _build_live_limit_profile,
    _require_live_risk_controls,
)

_LIVE_ENV = {
    'PRAXIS_MAX_ORDER_NOTIONAL': '1000',
    'PRAXIS_MAX_POSITION': '5000',
    'PRAXIS_MAX_ORDER_RATE': '3',
    'PRAXIS_MAX_SPREAD_BPS': '25',
    'PRAXIS_BOOK_STALENESS_SECONDS': '5',
    'PRAXIS_MAX_SLIPPAGE_BPS': '30',
}


def _set_live_env(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> None:
    for name in _LIVE_LIMIT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    for name, value in {**_LIVE_ENV, **overrides}.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def _manifest(controls: RiskBreakerThresholds) -> MagicMock:
    manifest = MagicMock()
    manifest.account_id = 'acct-001'
    manifest.risk_controls = controls

    return manifest


class TestLiveLimitProfile:

    def test_live_full_profile_resolves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_live_env(monkeypatch)

        profile = _build_live_limit_profile(live=True)

        assert profile.max_order_notional == Decimal('1000')
        assert profile.max_position == Decimal('5000')
        assert profile.max_order_rate == 3
        assert profile.max_spread_bps == Decimal('25')
        assert profile.book_staleness_seconds == 5
        assert profile.max_slippage_bps == Decimal('30')

    def test_live_missing_caps_reports_all(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_live_env(
            monkeypatch,
            PRAXIS_MAX_POSITION=None,
            PRAXIS_MAX_SLIPPAGE_BPS=None,
        )

        with pytest.raises(RuntimeError) as exc:
            _build_live_limit_profile(live=True)

        message = str(exc.value)
        assert 'PRAXIS_MAX_POSITION' in message
        assert 'PRAXIS_MAX_SLIPPAGE_BPS' in message
        assert 'PRAXIS_MAX_ORDER_NOTIONAL' not in message

    def test_live_single_missing_cap_rejected(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_live_env(monkeypatch, PRAXIS_MAX_ORDER_RATE=None)

        with pytest.raises(RuntimeError, match='PRAXIS_MAX_ORDER_RATE'):
            _build_live_limit_profile(live=True)

    def test_live_invalid_cap_rejected(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_live_env(monkeypatch, PRAXIS_MAX_ORDER_NOTIONAL='-1')

        with pytest.raises(ValueError, match='PRAXIS_MAX_ORDER_NOTIONAL'):
            _build_live_limit_profile(live=True)

    def test_paper_caps_are_optional(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in _LIVE_LIMIT_ENV_VARS:
            monkeypatch.delenv(name, raising=False)

        profile = _build_live_limit_profile(live=False)

        assert profile.max_order_notional is None
        assert profile.max_position is None
        assert profile.max_order_rate is None
        assert profile.max_spread_bps is None
        assert profile.book_staleness_seconds is None
        assert profile.max_slippage_bps is None


class TestRequireLiveRiskControls:

    def test_full_controls_accepted(self) -> None:
        controls = RiskBreakerThresholds(
            max_daily_loss=Decimal('100'),
            max_drawdown=Decimal('500'),
            max_drawdown_pct=Decimal('0.2'),
        )

        _require_live_risk_controls(_manifest(controls))

    def test_daily_loss_and_one_drawdown_accepted(self) -> None:
        controls = RiskBreakerThresholds(
            max_daily_loss=Decimal('100'),
            max_drawdown=None,
            max_drawdown_pct=Decimal('0.2'),
        )

        _require_live_risk_controls(_manifest(controls))

    def test_missing_daily_loss_rejected(self) -> None:
        controls = RiskBreakerThresholds(
            max_daily_loss=None,
            max_drawdown=Decimal('500'),
            max_drawdown_pct=None,
        )

        with pytest.raises(RuntimeError, match='max_daily_loss'):
            _require_live_risk_controls(_manifest(controls))

    def test_missing_both_drawdowns_rejected(self) -> None:
        controls = RiskBreakerThresholds(
            max_daily_loss=Decimal('100'),
            max_drawdown=None,
            max_drawdown_pct=None,
        )

        with pytest.raises(RuntimeError, match='max_drawdown'):
            _require_live_risk_controls(_manifest(controls))


class TestLauncherProfileInvariant:

    def test_enforce_permissions_without_profile_rejected(
        self, tmp_path: Path,
    ) -> None:
        with pytest.raises(ValueError, match='mandatory caps'):
            Launcher(
                trading_config=MagicMock(),
                instances=[],
                db_path=tmp_path / 'spine.sqlite',
                enforce_api_permissions=True,
            )

    def test_enforce_permissions_with_all_none_profile_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for name in _LIVE_LIMIT_ENV_VARS:
            monkeypatch.delenv(name, raising=False)

        with pytest.raises(ValueError, match='mandatory caps'):
            Launcher(
                trading_config=MagicMock(),
                instances=[],
                db_path=tmp_path / 'spine.sqlite',
                enforce_api_permissions=True,
                limit_profile=_build_live_limit_profile(live=False),
            )

    def test_paper_launcher_without_profile_allowed(
        self, tmp_path: Path,
    ) -> None:
        launcher = Launcher(
            trading_config=MagicMock(),
            instances=[],
            db_path=tmp_path / 'spine.sqlite',
            enforce_api_permissions=False,
        )

        assert launcher._limit_profile.max_order_notional is None
