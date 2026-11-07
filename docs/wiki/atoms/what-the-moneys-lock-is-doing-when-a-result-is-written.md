---
row: P6-03
baseline: 49aa659
created: 2026-11-06 15:07 UTC
modified: 2026-11-07 00:35 UTC
evidence:
  - claim: "Where a release is worked out for the exit and granted, the lock over the account's money is taken inside the release and given back as it answers, both before the write is reached"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438 making the test at 243 true, so that 244 reaches `nexus/core/capital_controller/capital_controller.py` 768 and answers at 808, all before `nexus/infrastructure/praxis_connector/outcome_processor.py` 285"
  - claim: "Where no release is worked out, that lock is never taken and the write is reached all the same"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 422-423, or 426 before 437, returning rather than reaching 438, so that the test at 243 skips 244, with 597 answering for 285"
---
# What the money's lock is doing when a result is written

Nothing, on either road that reaches [the write recording a realized result](where-a-realized-result-is-written-down.md) — but the two roads arrive at that by opposite means.

## The road that takes it and lets go

Where an exit's release is granted, the lock is taken inside the release itself, rather than by the road calling for one. The release settles its answer while still holding it, so the lock drops as that answer returns, and the write comes after.

## The road that never takes it

[Where no release is worked out for the exit](what-an-exit-outcome-changes.md), nothing reaches for that lock at all, and the write is reached all the same.

## Related

- [Where a realized result is written down](where-a-realized-result-is-written-down.md)
- [What a write of the whole state waits on](what-a-write-of-the-whole-state-waits-on.md)
- [What an exit outcome changes](what-an-exit-outcome-changes.md)
- [Which fills come back with a result](which-fills-come-back-with-a-result.md)
- [Which of the store's writes take which locks](which-of-the-stores-writes-take-which-locks.md)
