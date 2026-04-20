'''Tests for launcher `main()` uniqueness guards across manifests.

Ensures that duplicate `account_id`s or colliding env-var suffixes
across manifests in `MANIFESTS_DIR` are caught with a clear
`RuntimeError` rather than silently overwriting credentials or
registering duplicate outcome queues.
'''

from __future__ import annotations

from pathlib import Path

import pytest

from praxis.launcher import _enumerate_manifests, main


def _write_manifest(
    path: Path,
    account_id: str,
    allocated_capital: int = 10000,
    capital_pool: int = 10000,
) -> None:
    exp_dir = path.parent / f'{account_id}_experiment'
    exp_dir.mkdir(exist_ok=True)
    (path.parent / 'strat.py').write_text('# stub\n')
    path.write_text(
        f'account_id: {account_id}\n'
        f'allocated_capital: {allocated_capital}\n'
        f'capital_pool: {capital_pool}\n'
        f'strategies:\n'
        f'  - id: s\n'
        f'    file: strat.py\n'
        f'    sensors:\n'
        f'      - experiment: {exp_dir}\n'
        f'        permutation_ids: [1]\n'
        f'        interval_seconds: 60\n'
        f'    capital_pct: 100\n'
    )


class TestEnumerateManifests:

    def test_globally_sorted_across_yaml_and_yml(self, tmp_path: Path) -> None:
        '''Globbed *.yaml and *.yml paths return in one global sort.'''

        manifests_dir = tmp_path / 'manifests'
        manifests_dir.mkdir()
        (manifests_dir / 'b.yml').write_text('x')
        (manifests_dir / 'a.yaml').write_text('x')
        (manifests_dir / 'c.yaml').write_text('x')

        paths = _enumerate_manifests(manifests_dir)

        assert [p.name for p in paths] == ['a.yaml', 'b.yml', 'c.yaml']


class TestMainUniquenessGuards:

    def _env(
        self,
        *,
        manifests_dir: Path,
        state_base: Path,
        strategies_base_path: Path,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        env = {
            'EPOCH_ID': '1',
            'VENUE_REST_URL': 'https://example.invalid',
            'VENUE_WS_URL': 'wss://example.invalid',
            'MANIFESTS_DIR': str(manifests_dir),
            'STRATEGIES_BASE_PATH': str(strategies_base_path),
            'STATE_BASE': str(state_base),
        }
        if extra:
            env.update(extra)
        return env

    def test_duplicate_account_id_across_manifests_rejected(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        '''Two manifests declaring the same account_id fail fast.'''

        manifests_dir = tmp_path / 'manifests'
        manifests_dir.mkdir()
        _write_manifest(manifests_dir / 'a.yaml', account_id='acct-001')
        _write_manifest(manifests_dir / 'b.yaml', account_id='acct-001')

        monkeypatch.setattr('os.environ', self._env(
            manifests_dir=manifests_dir,
            state_base=tmp_path / 'state',
            strategies_base_path=manifests_dir,
            extra={
                'BINANCE_API_KEY_ACCT_001': 'k',
                'BINANCE_API_SECRET_ACCT_001': 's',
            },
        ))

        with pytest.raises(RuntimeError, match='duplicate account_id'):
            main()

    def test_env_suffix_collision_rejected(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        '''Two account_ids normalizing to the same env-var suffix fail fast.'''

        manifests_dir = tmp_path / 'manifests'
        manifests_dir.mkdir()
        _write_manifest(manifests_dir / 'a.yaml', account_id='acct-001')
        _write_manifest(manifests_dir / 'b.yaml', account_id='acct_001')

        monkeypatch.setattr('os.environ', self._env(
            manifests_dir=manifests_dir,
            state_base=tmp_path / 'state',
            strategies_base_path=manifests_dir,
            extra={
                'BINANCE_API_KEY_ACCT_001': 'k',
                'BINANCE_API_SECRET_ACCT_001': 's',
            },
        ))

        with pytest.raises(RuntimeError, match='env-var suffix collision'):
            main()
