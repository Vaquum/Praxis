---
row: N7-08
baseline: 49aa659
created: 2026-10-27 08:14 UTC
modified: 2026-11-08 14:58 UTC
evidence:
  - claim: "A checkpoint writes the state object to a temporary file, pushes it to the disk, renames it over the snapshot and pushes the directory too"
    source: "`nexus/infrastructure/state_store.py` 178-179 into `nexus/infrastructure/snapshot.py` 45-51, the directory opened and pushed at 23-30"
  - claim: "It then rewrites the log behind that snapshot, which drops every record of a state change"
    source: "`nexus/infrastructure/snapshot.py` 52-53 into `nexus/infrastructure/wal.py` 289-292"
  - claim: "That object holds the money, the risk figures, the positions, the modes and their holds, the dust, and the identifiers of what has already been worked through"
    source: "`nexus/core/domain/instance_state.py` 72-82, written out at `nexus/infrastructure/wal_codec.py` 81-96"
  - claim: "The strategy bytes are not among them, and a stopping host writes them to their own files a step before it asks for the checkpoint"
    source: "`nexus/core/domain/instance_state.py` 72-82 carrying none of them, and `nexus/startup/shutdown_sequencer.py` 191 before 193"
  - claim: "Two other callers ask for a checkpoint with no such writing before it: a timer on every tick, and a start only where the total worth of the positions it rebuilt differs from the total it had stored"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 147, and `nexus/startup/sequencer.py` 481 under the test at 472"
  - claim: "A start that altered positions without changing that total asks for no checkpoint, and writes those alterations nowhere else either"
    source: "`nexus/startup/sequencer.py` 437 under the test at 422 over the lookup at 420, or 441-448 and 450-466 where that lookup found one, all three before the test at 472, no other write on the road at 164-189"
---
# What a checkpoint holds

A checkpoint is the snapshot a store writes of one state object, plus [a rewrite of the log behind it](what-the-thirty-day-cut-leaves.md) that drops every record of a state change.

## What the snapshot carries

The money, the risk figures, [the positions](holdings.md), the modes and their holds, [the dust](where-a-positions-last-scraps-go.md), and the identifiers of everything already worked through.

[The strategy bytes](what-a-stopping-host-saves-of-its-strategies.md) sit outside it entirely: a stopping host writes those to their own files a step before it asks for the checkpoint.

## How it is written

To a temporary file, pushed to the disk, renamed over the snapshot, and the directory pushed too — so the snapshot on disk is always one whole version.

## Who asks for one

[A stopping host](the-last-record-a-stopping-host-writes.md), once, at the end. A timer, on every tick. And a start, but only where the total worth of the positions it rebuilt differs from the total it had stored. A start that altered individual positions without changing that total asks for no checkpoint — and writes those alterations nowhere else either, so they live only in memory until something else writes. A position taken in from Praxis rides the same test, so a start can adopt a holding and record it nowhere.


## Related

- [What a start reads back from a checkpoint](what-a-start-reads-back-from-a-checkpoint.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
- [The last record a stopping host writes](the-last-record-a-stopping-host-writes.md)

---

Created 2026-10-27 08:14 UTC · Last modified 2026-11-08 14:58 UTC
