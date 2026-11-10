---
row: P5-06
baseline: 49aa659
created: 2026-11-05 16:22 UTC
modified: 2026-11-06 06:59 UTC
evidence:
  - claim: "The pair of locks the store's two state writes reach for is handed over only once the start has run"
    source: "`praxis/launcher.py` 4085 before 4141-4143"
  - claim: "A checkpoint the start may ask for falls before that handover"
    source: "`nexus/startup/sequencer.py` 177 and 481 reaching `nexus/infrastructure/state_store.py` 178, all of it before `praxis/launcher.py` 4141-4143"
  - claim: "The log lock the store makes for itself is taken by each of its writes"
    source: "`nexus/infrastructure/state_store.py` 117, taken at 178, 198 and 236"
  - claim: "The handover may happen once, a second being refused, as is anything that is not the pair"
    source: "`nexus/infrastructure/state_store.py` 153 and 162, the refusals at 154-156 and 158-160"
---
# When the store writes without its locks

The store Praxis builds for a Nexus host is handed the pair of locks its two state writes reach for only once the start has run.

## What falls inside the window

[A checkpoint the start may ask for](what-a-checkpoint-holds.md) falls before that handover, so the store has no pair in hand when it runs. [What such a write takes is settled inside the store](the-last-record-a-stopping-host-writes.md).

## What the store holds throughout

The store makes its own log lock as it is built, and each of its writes takes that one. It is the pair those two state writes reach for that arrives late.

## The handover

It may happen once. A second handover is refused, and so is anything that is not the pair.

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [The last record a stopping host writes](the-last-record-a-stopping-host-writes.md)
- [Which of the store's writes take which locks](which-of-the-stores-writes-take-which-locks.md)
