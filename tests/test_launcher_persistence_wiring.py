'''Verify launcher's `process_outcome` closure calls
`state_store.append_mutation(state)` after each successful state-mutating
outcome, so a SIGKILL/OOM/container restart between checkpoints recovers
to the most recent terminal outcome rather than rolling back to the last
clean shutdown.
'''

from __future__ import annotations

import ast
import inspect

import praxis.launcher


def _process_outcome_calls_append_mutation() -> bool:
    '''Inspect launcher source via AST to confirm the `process_outcome`
    closure contains a call to `state_store.append_mutation`.

    Stronger than a raw substring match: rejects matches that appear
    only in comments / docstrings, and binds the assertion to a call
    INSIDE the closure body rather than anywhere in the file.
    '''

    src = inspect.getsource(praxis.launcher)
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != 'process_outcome':
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            func = inner.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr != 'append_mutation':
                continue
            if not isinstance(func.value, ast.Name):
                continue
            if func.value.id == 'state_store':
                return True
    return False


def test_launcher_calls_append_mutation_after_successful_outcome() -> None:
    '''The launcher's `_build_nexus_runtime.process_outcome` closure must
    invoke `state_store.append_mutation(state)` when the OutcomeProcessor
    reports success and a position was updated. Pinned via AST inspection
    to defend against regression that leaves `append_mutation` defined-
    but-uncalled — the failure mode that hid this hole for the entire
    pre-fix history.
    '''

    assert _process_outcome_calls_append_mutation(), (
        'launcher process_outcome must call state_store.append_mutation '
        'after each successful state-mutating OutcomeProcessor.process '
        'so mid-run state is durable between checkpoints'
    )
