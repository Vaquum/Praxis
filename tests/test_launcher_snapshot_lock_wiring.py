'''Tests for the launcher's StateStore snapshot-lock bundle wiring.

The Nexus `StateSnapshotLocks` bundle moved lock ownership into
`StateStore` (Nexus v0.61.0/v0.62.0). The launcher cannot pass the
bundle at construction — the store is built first so `StartupSequencer`
can recover `InstanceState`, and only after recovery do `positions_lock`
/ `capital_controller` exist — so it attaches the bundle after recovery
via `StateStore.attach_snapshot_locks`. These pin the composition-point
identity assertion and the attach-before-consumers ordering.
'''

from __future__ import annotations

import ast
import inspect
import textwrap
import threading
from collections.abc import Callable
from decimal import Decimal

import pytest

from nexus.core.capital_controller.capital_controller import CapitalController
from nexus.core.domain.capital_state import CapitalState
from nexus.core.domain.instance_state import InstanceState

import praxis.launcher
from praxis.launcher import Launcher, _build_state_snapshot_locks


def _make_state() -> InstanceState:
    return InstanceState(capital=CapitalState(capital_pool=Decimal('100000')))


def test_build_state_snapshot_locks_returns_shared_locks() -> None:
    state = _make_state()
    positions_lock = threading.Lock()
    state.risk.lock = positions_lock
    controller = CapitalController(state.capital)

    bundle = _build_state_snapshot_locks(state, positions_lock, controller)

    assert bundle.positions_lock is positions_lock
    assert bundle.capital_lock is controller.lock_cm()


def test_build_state_snapshot_locks_rejects_risk_lock_mismatch() -> None:
    state = _make_state()
    state.risk.lock = threading.Lock()
    controller = CapitalController(state.capital)

    with pytest.raises(RuntimeError, match='same object as'):
        _build_state_snapshot_locks(state, threading.Lock(), controller)


def _call_lineno(func_src: str, predicate: Callable[[ast.expr], bool]) -> int | None:
    tree = ast.parse(textwrap.dedent(func_src))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and predicate(node.func):
            return node.lineno
    return None


def test_attach_precedes_snapshot_scheduler_start() -> None:
    src = inspect.getsource(Launcher._build_nexus_runtime)

    def is_attach(func: ast.expr) -> bool:
        return isinstance(func, ast.Attribute) and func.attr == 'attach_snapshot_locks'

    def is_scheduler_start(func: ast.expr) -> bool:
        return (
            isinstance(func, ast.Attribute)
            and func.attr == 'start'
            and isinstance(func.value, ast.Name)
            and func.value.id == 'snapshot_scheduler'
        )

    attach_line = _call_lineno(src, is_attach)
    scheduler_start_line = _call_lineno(src, is_scheduler_start)

    assert attach_line is not None, (
        '_build_nexus_runtime must call state_store.attach_snapshot_locks'
    )
    assert scheduler_start_line is not None, (
        '_build_nexus_runtime must start the snapshot_scheduler'
    )
    assert attach_line < scheduler_start_line, (
        'attach_snapshot_locks must run before snapshot_scheduler.start so the '
        'store owns the bundle before the periodic checkpoint thread mutates it'
    )


def test_build_nexus_runtime_constructs_bundle_via_helper() -> None:
    src = inspect.getsource(praxis.launcher.Launcher._build_nexus_runtime)

    def is_helper(func: ast.expr) -> bool:
        return isinstance(func, ast.Name) and func.id == '_build_state_snapshot_locks'

    assert _call_lineno(src, is_helper) is not None, (
        '_build_nexus_runtime must build the bundle via _build_state_snapshot_locks '
        'so the state.risk.lock identity is asserted at the composition point'
    )
