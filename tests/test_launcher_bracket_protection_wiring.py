'''Tests that launcher `main()` sources per-account bracket protection
failure response from each manifest into the TradingConfig.'''

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nexus.core.domain.bracket_protection_failure_response import (
    BracketProtectionFailureResponse,
)

from praxis.launcher import main


def _write_manifest(path: Path, account_id: str, extra: str = '') -> None:
    (path.parent / 'strat.py').write_text('# stub\n')
    path.write_text(
        f'account_id: {account_id}\n'
        f'allocated_capital: 10000\n'
        f'capital_pool: 10000\n'
        f'{extra}'
        f'strategies:\n'
        f'  - id: s\n'
        f'    file: strat.py\n'
        f'    signal:\n'
        f'      series: time_15m\n'
        f'      interval_seconds: 900\n'
        f'    capital_pct: 100\n'
    )


def test_main_sources_per_account_protection_response_from_manifests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    '''Each manifest's `bracket_protection_failure_response` reaches TradingConfig.'''

    manifests_dir = tmp_path / 'manifests'
    manifests_dir.mkdir()
    _write_manifest(
        manifests_dir / 'a.yaml',
        account_id='acct-reduce',
        extra='bracket_protection_failure_response: REDUCE_ONLY\n',
    )
    _write_manifest(manifests_dir / 'b.yaml', account_id='acct-flatten')

    captured = MagicMock()
    monkeypatch.setattr('praxis.launcher.Launcher', captured)
    monkeypatch.setattr('os.environ', {
        'EPOCH_ID': '1',
        'TRADE_MODE': 'paper',
        'MANIFESTS_DIR': str(manifests_dir),
        'STRATEGIES_BASE_PATH': str(manifests_dir),
        'STATE_BASE': str(tmp_path / 'state'),
        'BINANCE_API_KEY_ACCT_REDUCE': 'k',
        'BINANCE_API_SECRET_ACCT_REDUCE': 's',
        'BINANCE_API_KEY_ACCT_FLATTEN': 'k',
        'BINANCE_API_SECRET_ACCT_FLATTEN': 's',
    })

    main()

    trading_config = captured.call_args.kwargs['trading_config']

    assert (
        trading_config.response_for('acct-reduce')
        is BracketProtectionFailureResponse.REDUCE_ONLY
    )
    assert (
        trading_config.response_for('acct-flatten')
        is BracketProtectionFailureResponse.FLATTEN_THEN_HALT
    )
    assert (
        trading_config.response_for('acct-absent')
        is BracketProtectionFailureResponse.FLATTEN_THEN_HALT
    )
