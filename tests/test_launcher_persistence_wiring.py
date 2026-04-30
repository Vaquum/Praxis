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


def _append_mutation_guard_mentions_capital_updated() -> bool:
    '''Walk `process_outcome`'s body, find the `if` whose body contains
    the `state_store.append_mutation` call, return True if its condition
    references `capital_updated`. Pins MAJOR-M's fix that capital-only
    mutations (ACK / non-fill REJECT / non-fill CANCEL) also persist.
    '''

    src = inspect.getsource(praxis.launcher)
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != 'process_outcome':
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.If):
                continue
            body_has_append_mutation = False
            for stmt in ast.walk(inner):
                if not isinstance(stmt, ast.Call):
                    continue
                func = stmt.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr != 'append_mutation':
                    continue
                if not isinstance(func.value, ast.Name):
                    continue
                if func.value.id == 'state_store':
                    body_has_append_mutation = True
                    break
            if not body_has_append_mutation:
                continue
            for sub in ast.walk(inner.test):
                if isinstance(sub, ast.Attribute) and sub.attr == 'capital_updated':
                    return True
    return False


def test_launcher_append_mutation_gate_includes_capital_updated() -> None:
    '''MAJOR-M: the `if` gate around `state_store.append_mutation` must
    reference `capital_updated` so ACK / non-fill REJECT / non-fill
    CANCEL outcomes (which mutate `in_flight_order_notional`,
    `working_order_notional`, `per_strategy_deployed` but return
    `position_updated=False`) persist to WAL between checkpoints. Pre-fix
    the gate was `result.success and result.position_updated` — a crash
    before the next position-updating fill rolled back to a snapshot
    whose `per_strategy_deployed` overcounted by the released-but-
    unpersisted amount.
    '''

    assert _append_mutation_guard_mentions_capital_updated(), (
        'launcher process_outcome\'s state_store.append_mutation gate '
        'must include capital_updated so capital-only mutations '
        '(ACK / non-fill REJECT / non-fill CANCEL) are durable'
    )
