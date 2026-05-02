'''Verify the launcher's `process_outcome` no-context terminal branch
invokes `capital_controller.recover_orphaned_order` (M03.1, round-18
MAJOR-003 cross-repo wire-up).

Pre-fix, the no-context cleanup branch popped the registries but left
`CapitalController._orders[command_id]` in IN_FLIGHT or WORKING. The
helper exists in Nexus and is idempotent; the launcher's job is to
call it.
'''

from __future__ import annotations

import ast
import inspect

import praxis.launcher


def _no_context_terminal_branch_calls_recover() -> bool:
    '''Walk `process_outcome` AST: find the `if order_context is None`
    block; inside it, find the inner `if outcome.outcome_type.is_terminal`
    block; assert that block contains a call to
    `capital_controller.recover_orphaned_order(...)`.
    '''

    src = inspect.getsource(praxis.launcher)
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != 'process_outcome':
            continue
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.If):
                continue
            if not _is_order_context_none_test(stmt.test):
                continue
            for inner in ast.walk(stmt):
                if not isinstance(inner, ast.If):
                    continue
                if not _is_terminal_test(inner.test):
                    continue
                for call_node in ast.walk(inner):
                    if not isinstance(call_node, ast.Call):
                        continue
                    func = call_node.func
                    if not isinstance(func, ast.Attribute):
                        continue
                    if func.attr != 'recover_orphaned_order':
                        continue
                    if not isinstance(func.value, ast.Name):
                        continue
                    if func.value.id == 'capital_controller':
                        return True
    return False


def _is_order_context_none_test(test: ast.AST) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != 'order_context':
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Is):
        return False
    if len(test.comparators) != 1:
        return False
    comp = test.comparators[0]
    return isinstance(comp, ast.Constant) and comp.value is None


def _is_terminal_test(test: ast.AST) -> bool:
    if not isinstance(test, ast.Attribute) or test.attr != 'is_terminal':
        return False
    inner = test.value
    if not isinstance(inner, ast.Attribute) or inner.attr != 'outcome_type':
        return False
    return isinstance(inner.value, ast.Name) and inner.value.id == 'outcome'


def test_no_context_terminal_calls_recover_orphaned_order() -> None:
    '''The launcher's `process_outcome` no-context terminal branch must
    call `capital_controller.recover_orphaned_order(command_id,
    outcome_type)` so the orphan order tracked in `_orders[command_id]`
    is released alongside the registry pops. Closes round-18 MAJOR-003
    (Nexus #56) M03.1.
    '''

    assert _no_context_terminal_branch_calls_recover(), (
        'launcher process_outcome must call '
        'capital_controller.recover_orphaned_order in the no-context '
        'terminal cleanup branch so capital aggregates are released'
    )
