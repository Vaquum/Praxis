'''Test for PT-FIX-16 launcher tie-in: drain_pending_startup_actions runs.

Pre-tie-in: `StartupSequencer._dispatch_startup` buffered `on_startup`
return values into `_pending_startup_actions` because the launcher
submitter doesn't exist until after `sequencer.start()` finishes
materialising `instance_state`. The Praxis launcher must call
`sequencer.drain_pending_startup_actions(submitter)` after building
the submitter so the buffered actions actually get submitted.

This test asserts the call happens. It does not exercise the full
runtime — `_build_nexus_runtime` has many dependencies that would
take a fixture forest to wire up — so we just check that the
launcher source contains the call (smoke test against future
regressions).
'''

from __future__ import annotations

from pathlib import Path


def test_launcher_calls_drain_pending_startup_actions() -> None:

    launcher_src = Path('praxis/launcher.py').read_text()
    assert 'sequencer.drain_pending_startup_actions(submitter)' in launcher_src
