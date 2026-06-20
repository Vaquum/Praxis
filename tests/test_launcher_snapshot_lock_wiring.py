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


@pytest.mark.parametrize('consumer', ['outcome_loop', 'snapshot_scheduler'])
def test_attach_precedes_store_consumer_start(consumer: str) -> None:
    build_src = inspect.getsource(Launcher._build_nexus_runtime)
    start_src = inspect.getsource(Launcher._start_nexus_loops)
    run_src = inspect.getsource(Launcher._run_nexus_instance)

    def is_attach(func: ast.expr) -> bool:
        return isinstance(func, ast.Attribute) and func.attr == 'attach_snapshot_locks'

    def is_runtime_consumer_start(func: ast.expr) -> bool:
        return (
            isinstance(func, ast.Attribute)
            and func.attr == 'start'
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == consumer
        )

    def is_build(func: ast.expr) -> bool:
        return isinstance(func, ast.Attribute) and func.attr == '_build_nexus_runtime'

    def is_start_loops(func: ast.expr) -> bool:
        return isinstance(func, ast.Attribute) and func.attr == '_start_nexus_loops'

    assert _call_lineno(build_src, is_attach) is not None, (
        '_build_nexus_runtime must call state_store.attach_snapshot_locks'
    )
    assert _call_lineno(start_src, is_runtime_consumer_start) is not None, (
        f'_start_nexus_loops must start {consumer}'
    )

    build_call = _call_lineno(run_src, is_build)
    start_call = _call_lineno(run_src, is_start_loops)

    assert build_call is not None and start_call is not None, (
        '_run_nexus_instance must build the runtime then start its loops'
    )
    assert build_call < start_call, (
        'attach_snapshot_locks (in _build_nexus_runtime) must run before the '
        f'loops start (in _start_nexus_loops) so the store owns the bundle '
        f'before {consumer} reaches append_mutation / checkpoint'
    )


def test_build_nexus_runtime_constructs_bundle_via_helper() -> None:
    src = inspect.getsource(praxis.launcher.Launcher._build_nexus_runtime)

    def is_helper(func: ast.expr) -> bool:
        return isinstance(func, ast.Name) and func.id == '_build_state_snapshot_locks'

    assert _call_lineno(src, is_helper) is not None, (
        '_build_nexus_runtime must build the bundle via _build_state_snapshot_locks '
        'so the state.risk.lock identity is asserted at the composition point'
    )
