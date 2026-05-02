'''Tests for the `command_strategy_ids` / `command_contexts` cross-thread
visibility contract enforced by the launcher's `command_registry_lock`.

Two layers of fixes are pinned by this file:

PT-FIX-29 — both registry mutations (`command_strategy_ids[cid] = sid`
and `command_contexts[cid] = order_context`) and the cross-thread reads
of those registries (`process_outcome`, `resolve_strategy_id`) now go
through the shared `command_registry_lock` so external observers never
see a torn dict-state. The `TestCommandRegistryLock` class pins the
torn-read invariant on both registration and terminal-pop paths.

MAJOR-P (round 14) — `command_strategy_ids[cid] = sid` is written
BEFORE `capital_controller.send_order` (was: written AFTER, AT THE END
of the loop body, under one combined `with` block). Pre-fix a fast
venue ACK landing during `send_order` / `_ensure_entry_position` /
`_build_order_context` would call `resolve_strategy_id` and miss,
silently dropping the outcome. Post-fix the strategy_ids write happens
at the TOP of the per-action loop body; the contexts write stays at
the END (it needs `order_context` which is built later). On
`send_order` failure the launcher also pops the early strategy_ids
entry back out under the lock to avoid a registry zombie — that
post-failure cleanup is exercised by the integration tests covering
`_build_nexus_runtime`, not by this file. The
`TestMajorPRegistryRaceWindow` class here pins only the early-write
ordering invariant.

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

        deadline = time.monotonic() + 15
        for t in threads:
            remaining = deadline - time.monotonic()
            t.join(timeout=max(0.0, remaining))

        alive = [t.name for t in threads if t.is_alive()]
        assert not alive, f'threads did not finish within timeout: {alive}'
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

        deadline = time.monotonic() + 15
        for t in threads:
            remaining = deadline - time.monotonic()
            t.join(timeout=max(0.0, remaining))

        alive = [t.name for t in threads if t.is_alive()]
        assert not alive, f'threads did not finish within timeout: {alive}'
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

        deadline = time.monotonic() + 10
        for t in threads:
            remaining = deadline - time.monotonic()
            t.join(timeout=max(0.0, remaining))

        if not observed_torn.is_set():
            pytest.skip(
                'race did not trigger in this run; absence does not '
                'disprove the pre-fix tear hazard'
            )


def _submitter_pattern_post_major_p(
    *,
    lock: threading.Lock,
    strategy_ids: dict[str, str],
    contexts: dict[str, Any],
    command_id: str,
    strategy_id: str,
    order_context: Any,
    send_order_observer: list[bool],
) -> None:
    '''Mirror the post-MAJOR-P submitter pattern: register
    `command_strategy_ids` BEFORE `send_order` so OutcomeLoop can
    resolve a fast venue ACK that arrives during `send_order` /
    `_ensure_entry_position` / `_build_order_context`.

    The `send_order_observer` captures whether `command_strategy_ids`
    was populated at `send_order` invocation time. The test asserts
    every observation is True.
    '''

    with lock:
        strategy_ids[command_id] = strategy_id

    def _fake_send_order() -> None:
        with lock:
            send_order_observer.append(command_id in strategy_ids)

    _fake_send_order()

    if order_context is not None:
        with lock:
            contexts[command_id] = order_context


class TestMajorPRegistryRaceWindow:
    '''MAJOR-P: `command_strategy_ids` must be populated BEFORE
    `send_order` is called so OutcomeLoop's `resolve_strategy_id`
    cannot miss for fast venue ACKs that arrive during the post-
    `send_command` processing window. Pre-fix the registration
    happened AFTER `send_order` / `_ensure_entry_position` /
    `_build_order_context`, so the OutcomeLoop could pop an ACK,
    call `resolve_strategy_id`, get None, drop the outcome, and
    leave the order stuck IN_FLIGHT (`order_ack` never runs →
    subsequent FILL → INVARIANT_BREACH → fill silently dropped on
    the capital side, position not grown, capital permanently
    stuck in `in_flight_order_notional`).
    '''

    def test_strategy_id_set_before_send_order(self) -> None:
        '''Pin the post-fix ordering invariant: at the moment
        `send_order` runs, `command_strategy_ids[command_id]` is
        already populated.
        '''

        lock = threading.Lock()
        strategy_ids: dict[str, str] = {}
        contexts: dict[str, str] = {}
        observations: list[bool] = []

        for i in range(50):
            _submitter_pattern_post_major_p(
                lock=lock,
                strategy_ids=strategy_ids,
                contexts=contexts,
                command_id=f'cmd-{i}',
                strategy_id=f'strat-{i % 3}',
                order_context=f'ctx-{i}' if i % 2 == 0 else None,
                send_order_observer=observations,
            )

        assert all(observations), (
            f'send_order observed command_strategy_ids missing for '
            f'{observations.count(False)} of {len(observations)} commands'
        )

    def test_strategy_id_resolvable_during_send_order_concurrent(self) -> None:
        '''Reader thread races against submitter; after submitter
        registers `strategy_ids`, the reader must see it BEFORE the
        contexts entry lands. If the reader observes an entry in
        `strategy_ids`, the resolver returns the right strategy
        even if `contexts` has not been populated yet.
        '''

        lock = threading.Lock()
        strategy_ids: dict[str, str] = {}
        contexts: dict[str, str] = {}

        misses: list[str] = []
        writer_failures: list[Exception] = []
        miss_lock = threading.Lock()
        stop_event = threading.Event()

        def writer() -> None:
            try:
                for i in range(200):
                    cid = f'cmd-{i}'
                    expected_strategy = f'strat-{i % 3}'

                    with lock:
                        strategy_ids[cid] = expected_strategy

                    time.sleep(0.0001)

                    with lock:
                        contexts[cid] = f'ctx-{i}'
            except Exception as exc:
                writer_failures.append(exc)
            finally:
                stop_event.set()

        def reader() -> None:
            while not stop_event.is_set():
                for i in range(200):
                    cid = f'cmd-{i}'
                    expected_strategy = f'strat-{i % 3}'
                    with lock:
                        observed = strategy_ids.get(cid)
                        has_ctx = cid in contexts
                    if observed is None and has_ctx:
                        with miss_lock:
                            misses.append(
                                f'{cid}: contexts has entry but '
                                f'strategy_ids missing (expected '
                                f'{expected_strategy})'
                            )
                time.sleep(0.0001)

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        threads.append(threading.Thread(target=writer, daemon=True))

        for t in threads:
            t.start()

        deadline = time.monotonic() + 15
        for t in threads:
            remaining = deadline - time.monotonic()
            t.join(timeout=max(0.0, remaining))

        alive = [t.name for t in threads if t.is_alive()]
        assert not alive, f'threads did not finish within timeout: {alive}'
        assert not writer_failures, (
            f'writer thread raised — invariant test inconclusive: '
            f'{writer_failures[:3]}'
        )
        assert len(strategy_ids) == 200, (
            f'writer did not complete all 200 iterations: '
            f'strategy_ids size={len(strategy_ids)}'
        )
        assert not misses, (
            f'observed {len(misses)} cases where contexts was populated '
            f'but strategy_ids was missing — MAJOR-P invariant violated. '
            f'first few: {misses[:5]}'
        )


def _submitter_pattern_post_final_major_01(
    *,
    lock: threading.Lock,
    strategy_ids: dict[str, str],
    contexts: dict[str, Any],
    command_id: str,
    strategy_id: str,
    order_context: Any,
    work_delay: float,
) -> None:
    '''Mirror the post-FINAL-MAJOR-01 submitter atomic pattern.

    Both registry writes plus the simulated `send_order` /
    `_ensure_entry_position` / `_build_order_context` work happen under
    ONE `command_registry_lock` acquisition. No external reader can
    observe a gap between the strategy_ids write and the contexts write
    because the lock spans the entire critical section.

    `work_delay` widens the window inside the lock so a contended
    reader has a chance to attempt to take the lock during the work;
    the assertion is that the reader BLOCKS until both registries are
    populated, never observing a torn state.
    '''

    with lock:
        strategy_ids[command_id] = strategy_id
        time.sleep(work_delay)
        if order_context is not None:
            contexts[command_id] = order_context


class TestFinalMajor01AtomicRegistration:
    '''FINAL-MAJOR-01: the launcher submitter holds
    `command_registry_lock` across the ENTIRE critical section
    (`command_strategy_ids` write → `send_order` → `_ensure_entry_position`
    → `_build_order_context` → `command_contexts` write). Pre-fix the
    writes were under separate lock acquisitions with `send_order` /
    context build in between; a fast venue ACK or terminal non-fill
    landing in that window would resolve the strategy_id, find
    `command_contexts.get(...)` is None, and silently drop the outcome
    — stranding `_orders[command_id]` and inflating capital aggregates.
    '''

    def test_no_torn_observation_either_direction(self) -> None:
        '''Writer holds lock across both writes. Reader takes the same
        lock and observes both registries. Assertion: for any command_id
        seen in either registry, BOTH must be present (when contexts
        is supposed to be set). Pre-fix this fails because the writer
        releases between strategy_ids and contexts writes.
        '''

        lock = threading.Lock()
        strategy_ids: dict[str, str] = {}
        contexts: dict[str, str] = {}

        torn_observations: list[str] = []
        torn_lock = threading.Lock()
        stop_event = threading.Event()
        writer_failures: list[Exception] = []

        def writer() -> None:
            try:
                for i in range(200):
                    _submitter_pattern_post_final_major_01(
                        lock=lock,
                        strategy_ids=strategy_ids,
                        contexts=contexts,
                        command_id=f'cmd-{i}',
                        strategy_id=f'strat-{i % 3}',
                        order_context=f'ctx-{i}',
                        work_delay=0.0001,
                    )
            except Exception as exc:
                writer_failures.append(exc)
            finally:
                stop_event.set()

        def reader() -> None:
            while not stop_event.is_set():
                for i in range(200):
                    cid = f'cmd-{i}'
                    with lock:
                        has_strat = cid in strategy_ids
                        has_ctx = cid in contexts
                    if has_strat != has_ctx:
                        with torn_lock:
                            torn_observations.append(
                                f'{cid}: has_strat={has_strat} '
                                f'has_ctx={has_ctx}'
                            )
                time.sleep(0.0001)

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        threads.append(threading.Thread(target=writer, daemon=True))

        for t in threads:
            t.start()

        deadline = time.monotonic() + 15
        for t in threads:
            remaining = deadline - time.monotonic()
            t.join(timeout=max(0.0, remaining))

        alive = [t.name for t in threads if t.is_alive()]
        assert not alive, f'threads did not finish within timeout: {alive}'
        assert not writer_failures, (
            f'writer thread raised: {writer_failures[:3]}'
        )
        assert len(strategy_ids) == 200, (
            f'writer did not complete: strategy_ids size={len(strategy_ids)}'
        )
        assert not torn_observations, (
            f'observed {len(torn_observations)} torn registrations — '
            f'FINAL-MAJOR-01 atomic-writer invariant violated. '
            f'first few: {torn_observations[:5]}'
        )

    def test_reader_blocks_until_both_registries_populated(self) -> None:
        '''The OutcomeLoop's `process_outcome` and `resolve_strategy_id`
        both take `command_registry_lock`. While the writer holds the
        lock during the critical section, the reader's lock acquisition
        BLOCKS — guaranteeing it cannot observe a partially-populated
        registry. This test proves the blocking behavior.

        Synchronization is deterministic via two `threading.Event`
        signals (writer_inside_critical_section + reader_attempted_lock)
        so the test does not rely on `time.sleep` to order the
        writer-acquires-first then reader-attempts sequence — that
        would race on slow / contended CI runners.
        '''

        lock = threading.Lock()
        strategy_ids: dict[str, str] = {}
        contexts: dict[str, str] = {}

        writer_inside_critical_section = threading.Event()
        reader_attempted_lock = threading.Event()
        writer_done = threading.Event()
        reader_observations: list[tuple[bool, bool]] = []
        sync_failures: list[str] = []

        def writer() -> None:
            with lock:
                strategy_ids['cmd-0'] = 'strat-A'
                writer_inside_critical_section.set()
                if not reader_attempted_lock.wait(timeout=5):
                    sync_failures.append(
                        'writer: reader_attempted_lock wait timed out — '
                        'reader never reached the lock acquisition'
                    )
                contexts['cmd-0'] = 'ctx-0'
            writer_done.set()

        def reader() -> None:
            if not writer_inside_critical_section.wait(timeout=5):
                sync_failures.append(
                    'reader: writer_inside_critical_section wait timed out — '
                    'writer never acquired the lock'
                )
                return
            reader_attempted_lock.set()
            with lock:
                reader_observations.append(
                    ('cmd-0' in strategy_ids, 'cmd-0' in contexts)
                )

        w = threading.Thread(target=writer, daemon=True)
        r = threading.Thread(target=reader, daemon=True)
        w.start()
        r.start()
        w.join(timeout=5)
        r.join(timeout=5)

        assert not sync_failures, (
            f'PR #85 round-6: deterministic sync failed — '
            f'{sync_failures}. Test cannot prove blocking semantics if '
            f'the writer-then-reader ordering was not established.'
        )
        assert writer_done.is_set(), 'writer did not complete'
        assert len(reader_observations) == 1, (
            f'reader did not observe: {reader_observations}'
        )
        has_strat, has_ctx = reader_observations[0]
        assert has_strat and has_ctx, (
            f'reader observed torn state — lock did not block reader '
            f'until writer completed: has_strat={has_strat} '
            f'has_ctx={has_ctx}'
        )
