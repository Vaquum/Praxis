'''Integration tests for launcher `main()` on the live cutover path.

Exercise the mandatory live interlocks end to end through `main()` with the
`Launcher` mocked: the live-arm token, the mandatory limit-cap profile, and
the per-manifest account loss breakers all gate before the launcher is
constructed. The happy path threads the resolved caps into the launcher.
'''

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from praxis.launcher import (
    _LIVE_ARM_ENV,
    _LIVE_ARM_TOKEN,
    main,
)

_ACCOUNT = 'acct-live'
_SUFFIX = 'ACCT_LIVE'


def _write_manifest(path: Path, *, risk_controls: str) -> None:
    (path.parent / 'strat.py').write_text('# stub\n')
    path.write_text(
        f'account_id: {_ACCOUNT}\n'
        f'allocated_capital: 10000\n'
        f'capital_pool: 10000\n'
        f'{risk_controls}'
        f'strategies:\n'
        f'  - id: s\n'
        f'    file: strat.py\n'
        f'    signal:\n'
        f'      series: time_15m\n'
        f'      interval_seconds: 900\n'
        f'    capital_pct: 100\n'
    )


_FULL_RISK_CONTROLS = (
    'risk_controls:\n'
    '  max_daily_loss: 500\n'
    '  max_drawdown: 1000\n'
)

_LIVE_CAPS = {
    'PRAXIS_MAX_ORDER_NOTIONAL': '1000',
    'PRAXIS_MAX_POSITION': '5000',
    'PRAXIS_MAX_ORDER_RATE': '3',
    'PRAXIS_MAX_SPREAD_BPS': '25',
    'PRAXIS_BOOK_STALENESS_SECONDS': '5',
    'PRAXIS_MAX_SLIPPAGE_BPS': '30',
}


def _live_env(
    tmp_path: Path, manifests_dir: Path, *, caps: dict[str, str] | None = None,
) -> dict[str, str]:
    secrets_file = tmp_path / 'secrets.json'
    secrets_file.write_text(json.dumps(
        {_ACCOUNT: {'api_key': 'k', 'api_secret': 's'}},
    ))

    env = {
        'EPOCH_ID': '1',
        'TRADE_MODE': 'live',
        _LIVE_ARM_ENV: _LIVE_ARM_TOKEN,
        'MANIFESTS_DIR': str(manifests_dir),
        'STRATEGIES_BASE_PATH': str(manifests_dir),
        'STATE_BASE': str(tmp_path / 'state'),
        'PRAXIS_SECRETS_FILE': str(secrets_file),
    }
    env.update(caps if caps is not None else _LIVE_CAPS)

    return env


def test_live_full_profile_and_breakers_constructs_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifests_dir = tmp_path / 'manifests'
    manifests_dir.mkdir()
    _write_manifest(manifests_dir / 'a.yaml', risk_controls=_FULL_RISK_CONTROLS)

    captured = MagicMock()
    monkeypatch.setattr('praxis.launcher.Launcher', captured)
    monkeypatch.setattr('os.environ', _live_env(tmp_path, manifests_dir))

    main()

    profile = captured.call_args.kwargs['limit_profile']
    assert profile.max_order_notional == Decimal('1000')
    assert profile.max_position == Decimal('5000')
    assert profile.max_order_rate == 3
    assert profile.max_spread_bps == Decimal('25')
    assert profile.book_staleness_seconds == 5
    assert profile.max_slippage_bps == Decimal('30')
    assert captured.call_args.kwargs['enforce_api_permissions'] is True


def test_live_missing_cap_fails_before_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifests_dir = tmp_path / 'manifests'
    manifests_dir.mkdir()
    _write_manifest(manifests_dir / 'a.yaml', risk_controls=_FULL_RISK_CONTROLS)

    partial_caps = dict(_LIVE_CAPS)
    del partial_caps['PRAXIS_MAX_SLIPPAGE_BPS']

    captured = MagicMock()
    monkeypatch.setattr('praxis.launcher.Launcher', captured)
    monkeypatch.setattr(
        'os.environ', _live_env(tmp_path, manifests_dir, caps=partial_caps),
    )

    with pytest.raises(RuntimeError, match='PRAXIS_MAX_SLIPPAGE_BPS'):
        main()

    captured.assert_not_called()


def test_live_missing_risk_controls_fails_before_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifests_dir = tmp_path / 'manifests'
    manifests_dir.mkdir()
    _write_manifest(manifests_dir / 'a.yaml', risk_controls='')

    captured = MagicMock()
    monkeypatch.setattr('praxis.launcher.Launcher', captured)
    monkeypatch.setattr('os.environ', _live_env(tmp_path, manifests_dir))

    with pytest.raises(RuntimeError, match='max_daily_loss'):
        main()

    captured.assert_not_called()


def test_live_missing_arm_fails_before_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifests_dir = tmp_path / 'manifests'
    manifests_dir.mkdir()
    _write_manifest(manifests_dir / 'a.yaml', risk_controls=_FULL_RISK_CONTROLS)

    env = _live_env(tmp_path, manifests_dir)
    del env[_LIVE_ARM_ENV]

    captured = MagicMock()
    monkeypatch.setattr('praxis.launcher.Launcher', captured)
    monkeypatch.setattr('os.environ', env)

    with pytest.raises(RuntimeError, match=_LIVE_ARM_ENV):
        main()

    captured.assert_not_called()
