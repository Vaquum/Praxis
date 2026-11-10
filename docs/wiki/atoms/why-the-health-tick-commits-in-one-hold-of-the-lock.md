---
row: N69-04
baseline: 49aa659
created: 2026-11-08 20:50 UTC
modified: 2026-11-08 20:50 UTC
evidence:
  - claim: "The health tick writes the health reading, evaluates both breakers and recomputes under one hold of the lock"
    source: "`nexus/core/mode_controller.py` 118-123"
  - claim: "It decides whether the mode changed by comparing the mode before with the mode after, rather than by what any one recompute answered"
    source: "`nexus/core/mode_controller.py` 119, then 124"
  - claim: "That is needed because each breaker's own setting or clearing recomputes as well, so the last recompute's answer covers only the last step"
    source: "`nexus/core/mode_controller.py` 121-122 reaching 434 and 446, ahead of 123"
  - claim: "The road that writes the health reading alone answers with its one recompute's answer instead"
    source: "`nexus/core/mode_controller.py` 88-90, answered at 95"
  - claim: "A third road evaluates the two breakers alone, under the same pair of locks, and answers nothing at all"
    source: "`nexus/core/mode_controller.py` 327-329, answering at 331-332 with no value"
  - claim: "Both roads take a flag saying whether to fire the waiting notification here, for a caller holding a lock of its own"
    source: "`nexus/core/mode_controller.py` 92-93, and 126-127"
  - claim: "The reads of the risk figures take the risk record's own lock, or take nothing further where that lock is the one already held"
    source: "`nexus/core/mode_controller.py` 118 into 302-303, or 305"
---
# Why the health tick commits in one hold of the lock

A health tick has three things to do to [the mode](how-the-mode-is-recomputed.md), and it does all three without letting the lock go in between.

## The three

The health reading is written, both risk breakers are evaluated, and the mode is recomputed.

Splitting them would leave a window in which a reader taking this lock sees a mode settled from the new health reading and the old breakers, which the same tick then overwrites.

## How it decides what changed

By reading the mode before and comparing it with the mode after.

That is needed because each breaker's own setting or clearing recomputes as it goes. The recompute at the end therefore answers for its own step alone, and a mode moved by a breaker and left there would be reported as unchanged.

The simpler road — writing the health reading and nothing else — has one recompute, and answers with what that recompute said.

A third road evaluates the two breakers alone, under the same pair of locks, and answers nothing at all. A caller of it learns whether the mode moved only by reading the mode.

## Where the notification goes

Both roads take a flag saying whether to fire [the waiting notification](the-halt-notification-that-is-dropped.md) here.

A caller holding a lock of its own passes it off and drains the notification later, so the callback never runs under two locks.

## The risk figures

The reads of them take the risk record's own lock — or take nothing further where that lock is the one already held, since taking it twice would stop the tick dead. Either way the reads are protected; what varies is whether a second lock is needed to do it.

## Related

- [How the mode is recomputed](how-the-mode-is-recomputed.md)
- [The halt notification that is dropped](the-halt-notification-that-is-dropped.md)
