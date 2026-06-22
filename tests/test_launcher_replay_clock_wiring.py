'''Pin the clock-threading wiring a replay run depends on.

These guard the seams codex flagged: the validation pipeline must hand
its clock to the intake hooks (so the duplicate-order and order-rate
hooks gate on simulated time, not wall time), and the per-account build
must pass the launcher clock into that pipeline.
'''

from __future__ import annotations

import ast
import inspect

from praxis.launcher import Launcher, _build_validation_pipeline


def _has_call_with_kwarg(src: str, func_name: str, kwarg: str) -> bool:
    tree = ast.parse(inspect.cleandoc(src))

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == func_name
            and any(kw.arg == kwarg for kw in node.keywords)
        ):
            return True

    return False


def test_pipeline_passes_clock_to_intake_hooks() -> None:
    src = inspect.getsource(_build_validation_pipeline)

    assert _has_call_with_kwarg(src, 'build_default_intake_hooks', 'now_fn'), (
        '_build_validation_pipeline must pass now_fn to build_default_intake_hooks '
        'so the intake hooks gate on the injected clock'
    )


def test_build_passes_clock_to_pipeline() -> None:
    src = inspect.getsource(Launcher._build_nexus_runtime)

    assert _has_call_with_kwarg(src, '_build_validation_pipeline', 'clock'), (
        '_build_nexus_runtime must pass clock to _build_validation_pipeline'
    )
