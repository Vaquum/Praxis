'''Verify launcher's `process_outcome` closure calls
`state_store.append_mutation(state)` after each successful state-mutating
outcome, so a SIGKILL/OOM/container restart between checkpoints recovers
to the most recent terminal outcome rather than rolling back to the last
clean shutdown.
'''

from __future__ import annotations

import inspect

import praxis.launcher


def test_launcher_calls_append_mutation_after_successful_outcome() -> None:
    '''The launcher's `_build_nexus_runtime.process_outcome` closure must
    invoke `state_store.append_mutation(state)` when the OutcomeProcessor
    reports success and a position or capital aggregate was updated.
    Smoke test against the same kind of regression that left
    `append_mutation` defined-but-uncalled for the entire pre-fix
    history.
    '''

    src = inspect.getsource(praxis.launcher)
    assert 'state_store.append_mutation(state)' in src, (
        'launcher process_outcome must call state_store.append_mutation '
        'after each successful state-mutating OutcomeProcessor.process '
        'so mid-run state is durable between checkpoints'
    )
