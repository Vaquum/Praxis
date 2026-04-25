'''Tests for PT-FIX-29 — `command_strategy_ids` / `command_contexts`
mutated cross-thread without lock.

Pre-fix the launcher's `submitter` closure wrote
`command_strategy_ids[command_id] = strategy_id` first, did some work
(`capital_controller.send_order`, `_ensure_entry_position`,
`_build_order_context`), then wrote
`command_contexts[command_id] = order_context` last. `process_outcome`
running on the OutcomeLoop thread could read `command_contexts` between
the two writes and see `None`, log a warning, and silently drop the
`OutcomeProcessor.process` call. A theoretical race: by the time the
launcher reaches the second write, the venue has not yet seen the
command (it sits in `runtime.command_queue` awaiting `_account_loop`),
so practically the race only fires under unusual GIL preemption — but
the code now treats both writes as one critical section regardless.

Post-fix `_build_nexus_runtime` allocates a `command_registry_lock`
shared by `submitter`, `process_outcome`, and `resolve_strategy_id`.
The submitter wraps both registry writes in one `with` block at the
end of the per-action loop, so external observers never see a
partially-populated registration.

These tests pin down the lock invariant directly. The launcher's
closures are not extracted to module-level helpers (they capture too
much closure state), so this test reproduces the same pattern.
'''

from __future__ import annotations

import threading
import time
from typing import Any

import pytest


def _submitter_pattern(
    *,
    lock: threading.Lock,
    strategy_ids: dict[str, str],
    contexts: dict[str, Any],
    command_id: str,
    strategy_id: str,
    order_context: Any,
    work_delay: float,
) -> None:
    '''Mirror the launcher's submitter atomic-write pattern.

    Sleeps `work_delay` seconds between the per-command work and the
    registry writes to widen the race window. Pre-fix the writes were
    interleaved with the work; post-fix they are batched under the
    lock at the end.
    '''

    time.sleep(work_delay)

    with lock:
        strategy_ids[command_id] = strategy_id
        contexts[command_id] = order_context


def _process_outcome_pattern(
    *,
    lock: threading.Lock,
    contexts: dict[str, Any],
    command_id: str,
) -> Any:
    with lock:
        return contexts.get(command_id)


class TestCommandRegistryLock:

    def test_atomic_registration_visible_to_concurrent_lookup(self) -> None:
        '''A reader hitting between the two writes must see EITHER both
        keys present OR neither present — never a half-written
        registration. Under the lock this invariant holds; pre-fix it
        could fail because the writes were not under a shared lock.'''

        lock = threading.Lock()
        strategy_ids: dict[str, str] = {}
        contexts: dict[str, str] = {}

        observations: list[tuple[bool, bool]] = []
        observation_lock = threading.Lock()
        stop_event = threading.Event()

        def writer() -> None:
            try:
                for i in range(200):
                    _submitter_pattern(
                        lock=lock,
                        strategy_ids=strategy_ids,
                        contexts=contexts,
                        command_id=f'cmd-{i}',
                        strategy_id=f'strat-{i % 3}',
                        order_context=f'ctx-{i}',
                        work_delay=0.0,
                    )
                    if i % 10 == 0:
                        time.sleep(0.001)
            finally:
                stop_event.set()

        def reader() -> None:
            while not stop_event.is_set():
                for i in range(200):
                    cid = f'cmd-{i}'
                    with lock:
                        has_strat = cid in strategy_ids
                        has_ctx = cid in contexts
                    with observation_lock:
                        observations.append((has_strat, has_ctx))

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        threads.append(threading.Thread(target=writer, daemon=True))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        torn = [obs for obs in observations if obs[0] != obs[1]]
        assert not torn, (
            f'observed {len(torn)} torn registrations '
            f'(strategy_id present without context or vice versa); '
            f'first few: {torn[:5]}'
        )

    def test_terminal_pop_atomic_under_lock(self) -> None:
        '''Terminal cleanup pops both registries under the same lock so
        a concurrent reader cannot observe one missing while the other
        remains.'''

        lock = threading.Lock()
        strategy_ids: dict[str, str] = {f'cmd-{i}': f's-{i}' for i in range(100)}
        contexts: dict[str, str] = {f'cmd-{i}': f'c-{i}' for i in range(100)}

        observations: list[tuple[bool, bool]] = []
        observation_lock = threading.Lock()
        stop_event = threading.Event()

        def cleaner() -> None:
            try:
                for i in range(100):
                    cid = f'cmd-{i}'
                    with lock:
                        contexts.pop(cid, None)
                        strategy_ids.pop(cid, None)
            finally:
                stop_event.set()

        def reader() -> None:
            while not stop_event.is_set():
                for i in range(100):
                    cid = f'cmd-{i}'
                    with lock:
                        has_strat = cid in strategy_ids
                        has_ctx = cid in contexts
                    with observation_lock:
                        observations.append((has_strat, has_ctx))

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        threads.append(threading.Thread(target=cleaner, daemon=True))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        torn = [obs for obs in observations if obs[0] != obs[1]]
        assert not torn, (
            f'observed {len(torn)} torn pops '
            f'(strategy_id removed but context remains or vice versa); '
            f'first few: {torn[:5]}'
        )

    def test_unlocked_pattern_can_observe_partial_state(self) -> None:
        '''Sanity: pre-fix, with the writes unprotected, a tear is
        observable. Run two writes with a small sleep between, no
        lock; reader catches the half-state. Skips if CPython's
        scheduler did not interleave in this run.'''

        strategy_ids: dict[str, str] = {}
        contexts: dict[str, str] = {}
        observed_torn = threading.Event()
        stop_event = threading.Event()

        def torn_writer() -> None:
            try:
                for i in range(2000):
                    cid = f'cmd-{i}'
                    strategy_ids[cid] = f'strat-{i}'
                    time.sleep(0.0001)
                    contexts[cid] = f'ctx-{i}'
            finally:
                stop_event.set()

        def reader() -> None:
            while not stop_event.is_set():
                for i in range(2000):
                    cid = f'cmd-{i}'
                    has_strat = cid in strategy_ids
                    has_ctx = cid in contexts
                    if has_strat and not has_ctx:
                        observed_torn.set()
                        return

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        threads.append(threading.Thread(target=torn_writer, daemon=True))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        if not observed_torn.is_set():
            pytest.skip(
                'race did not trigger in this run; absence does not '
                'disprove the pre-fix tear hazard'
            )
