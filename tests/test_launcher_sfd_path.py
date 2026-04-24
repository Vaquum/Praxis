'''Tests for PT-FIX-19: launcher prepends strategies_base_path to sys.path.

Pre-fix: Limen `Trainer.__init__` calls
`importlib.import_module(metadata['sfd_module'])` to reload the SFD
class recorded at training time. If the user's SFD lived alongside
their strategy file (under `STRATEGIES_BASE_PATH`) but that path was
not on `sys.path`, `Trainer` raised `ModuleNotFoundError` at boot
and `_wire_sensors` re-raised as `StartupError` → the Nexus instance
never came up.

Post-fix: `_ensure_strategies_path_importable(strategies_base_path)`
runs at the top of `Launcher._build_nexus_runtime`, prepending the
resolved path to `sys.path` (idempotent — only if not already
present). Foundational SFDs continue to import unaffected; user SFDs
co-located with strategies become importable.
'''

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from praxis.launcher import _ensure_strategies_path_importable


@pytest.fixture(autouse=True)
def _restore_sys_path() -> None:
    snapshot = list(sys.path)
    try:
        yield
    finally:
        sys.path[:] = snapshot


def test_prepends_resolved_strategies_path(tmp_path: Path) -> None:

    target = tmp_path / 'strategies'
    target.mkdir()

    _ensure_strategies_path_importable(target)

    assert sys.path[0] == str(target.resolve())


def test_is_idempotent(tmp_path: Path) -> None:

    target = tmp_path / 'strategies'
    target.mkdir()

    _ensure_strategies_path_importable(target)
    _ensure_strategies_path_importable(target)
    _ensure_strategies_path_importable(target)

    occurrences = sum(1 for entry in sys.path if entry == str(target.resolve()))
    assert occurrences == 1


def test_resolves_relative_paths_to_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    target = tmp_path / 'strategies'
    target.mkdir()

    monkeypatch.chdir(tmp_path)
    relative = Path('strategies')

    _ensure_strategies_path_importable(relative)

    assert sys.path[0] == str(target.resolve())
    assert Path(sys.path[0]).is_absolute()


def test_user_sfd_module_becomes_importable(tmp_path: Path) -> None:

    strategies_dir = tmp_path / 'strategies'
    strategies_dir.mkdir()

    sfd_module = strategies_dir / 'pt_fix_19_demo_sfd.py'
    sfd_module.write_text('SFD_TOKEN = 42\n')

    _ensure_strategies_path_importable(strategies_dir)

    import importlib

    module = importlib.import_module('pt_fix_19_demo_sfd')

    try:
        assert module.SFD_TOKEN == 42
    finally:
        sys.modules.pop('pt_fix_19_demo_sfd', None)
