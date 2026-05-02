'''Verify the launcher's `process_outcome` closure invokes
`self._append_outcome_acked` after a successful OutcomeProcessor.process
(round-18 MAJOR-004). Pinned via AST inspection so a refactor that
drops the call (re-introducing the "no ack" gap) fails CI.
'''

from __future__ import annotations

import ast
import inspect

import praxis.launcher


def _process_outcome_calls_append_outcome_acked() -> bool:
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
            if func.attr != '_append_outcome_acked':
                continue
            if not isinstance(func.value, ast.Name):
                continue
            if func.value.id == 'self':
                return True
    return False


def test_process_outcome_appends_outcome_acked_on_success() -> None:
    '''The launcher's `_build_nexus_runtime.process_outcome` closure must
    invoke `self._append_outcome_acked(account_id, outcome.outcome_id)`
    after the OutcomeProcessor reports success, so the durable record
    of "this outcome was applied at the consumer" lands on the spine.
    Closes round-18 MAJOR-004 part B (Praxis #86).
    '''

    assert _process_outcome_calls_append_outcome_acked(), (
        'launcher process_outcome must call self._append_outcome_acked '
        'after successful OutcomeProcessor.process so MAJOR-004 has a '
        'durable consumption marker on the spine'
    )
