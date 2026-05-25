'''Tests for epoch-scoped InstanceState path in launcher `main()` (issue #120).'''

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from praxis.launcher import main


def _write_manifest(path: Path, account_id: str) -> None:
    exp_dir = path.parent / 'exp_experiment'
    exp_dir.mkdir(exist_ok=True)
    (path.parent / 'strat.py').write_text('# stub\n')
    path.write_text(
        f'account_id: {account_id}\n'
        f'allocated_capital: 10000\n'
        f'capital_pool: 10000\n'
        f'strategies:\n'
        f'  - id: s\n'
        f'    file: strat.py\n'
        f'    sensors:\n'
        f'      - experiment: {exp_dir}\n'
        f'        permutation_ids: [1]\n'
        f'        interval_seconds: 60\n'
        f'    capital_pct: 100\n'
    )


def test_state_dir_is_epoch_scoped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    '''`state_dir` and `strategy_state_path` fold `EPOCH_ID` as a path component.'''

    manifests_dir = tmp_path / 'manifests'
    manifests_dir.mkdir()
    _write_manifest(manifests_dir / 'a.yaml', account_id='acct-epoch')

    state_base = tmp_path / 'state'
    strategy_state_base = tmp_path / 'sstate'

    captured = MagicMock()
    monkeypatch.setattr('praxis.launcher.Launcher', captured)
    monkeypatch.setattr('os.environ', {
        'EPOCH_ID': '7',
        'TRADE_MODE': 'paper',
        'MANIFESTS_DIR': str(manifests_dir),
        'STRATEGIES_BASE_PATH': str(manifests_dir),
        'STATE_BASE': str(state_base),
        'STRATEGY_STATE_BASE': str(strategy_state_base),
        'BINANCE_API_KEY_ACCT_EPOCH': 'k',
        'BINANCE_API_SECRET_ACCT_EPOCH': 's',
    })

    main()

    instances = captured.call_args.kwargs['instances']

    assert instances[0].state_dir == state_base / 'acct-epoch' / '7'
    assert instances[0].strategy_state_path == strategy_state_base / 'acct-epoch' / '7'
