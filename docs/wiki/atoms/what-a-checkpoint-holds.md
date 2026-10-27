---
row: N7-08
baseline: 49aa659
created: 2026-10-27 15:10 UTC
modified: 2026-10-27 17:20 UTC
evidence:
  - claim: "A checkpoint writes the state object to a temporary file, pushes it to the disk, renames it over the snapshot and pushes the directory too"
    source: "`nexus/infrastructure/state_store.py` 178-179 into `nexus/infrastructure/snapshot.py` 45-51"
  - claim: "It then rewrites the log behind that snapshot, which drops every record of a state change"
    source: "`nexus/infrastructure/snapshot.py` 52-53 into `nexus/infrastructure/wal.py` 289-292"
  - claim: "That object holds the money, the risk figures, the positions, the modes and their holds, the dust, and the identifiers of what has already been worked through"
    source: "`nexus/core/domain/instance_state.py` 72-82, written out at `nexus/infrastructure/wal_codec.py` 81-96"
  - claim: "The strategy bytes are not among them, and a stopping host writes them to their own files a step before it asks for the checkpoint"
    source: "`nexus/core/domain/instance_state.py` 72-82 carrying none of them, and `nexus/startup/shutdown_sequencer.py` 191 before 193"
  - claim: "Two other callers ask for a checkpoint with no such writing before it: a timer on every tick, and a start only where the total worth of the positions it rebuilt differs from the total it had stored"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 147, and `nexus/startup/sequencer.py` 481 under the test at 472"
  - claim: "A start that altered positions without changing that total asks for no checkpoint, and writes those alterations nowhere else either"
    source: "`nexus/startup/sequencer.py` 441-448 and 450-466 before the test at 472, no other write on the road at 164-189"
  - claim: "A start reads the state from the snapshot and then lets any record of a state change the log still holds replace it"
    source: "`nexus/infrastructure/state_store.py` 260-261 into 266-267, the records appended again as the host runs at 198-207"
  - claim: "It then works each strategy's losses and realized result out again from what the log still holds, while the peaks and the deepest fall are kept at whichever is larger, the stored figure or the new one"
    source: "`nexus/infrastructure/state_store.py` 314-324, the peaks kept at 325-327 and at `nexus/core/domain/risk_state.py` 243-251 and 266-270 through 333"
---
# What a checkpoint holds

A checkpoint is the snapshot a store writes of one state object, plus [a rewrite of the log behind it](what-the-thirty-day-cut-leaves.md) that drops every record of a state change.

## What the snapshot carries

The money, the risk figures, [the positions](holdings.md), the modes and their holds, [the dust](where-a-positions-last-scraps-go.md), and the identifiers of everything already worked through.

[The strategy bytes](what-a-stopping-host-saves-of-its-strategies.md) sit outside it entirely: a stopping host writes those to their own files a step before it asks for the checkpoint.

## How it is written

To a temporary file, pushed to the disk, renamed over the snapshot, and the directory pushed too — so the snapshot on disk is always one whole version.

## Who asks for one

[A stopping host](the-last-record-a-stopping-host-writes.md), once, at the end. A timer, on every tick. And a start, but only where the total worth of the positions it rebuilt differs from the total it had stored. A start that altered individual positions without changing that total asks for no checkpoint — and writes those alterations nowhere else either, so they live only in memory until something else writes.

## What a start reads back

The state from the snapshot, and then any record of a state change the log still holds replacing it. A checkpoint leaves none of those behind; the host appends more as it runs.

Even then the snapshot is not simply taken as read: a start [works each strategy's losses and realized result out again](what-the-thirty-day-cut-leaves.md) from the events the log still holds. The peaks and the deepest fall are treated the other way — kept at whichever is larger, the stored figure or the newly worked-out one.

## Related

- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
- [The last record a stopping host writes](the-last-record-a-stopping-host-writes.md)

---

Created 2026-10-27 15:10 UTC · Last modified 2026-10-27 17:20 UTC
