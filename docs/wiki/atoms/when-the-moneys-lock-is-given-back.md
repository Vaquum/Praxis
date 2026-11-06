---
row: P6-03
baseline: 49aa659
created: 2026-11-06 15:07 UTC
modified: 2026-11-07 00:00 UTC
evidence:
  - claim: "Where a release is worked out for the exit and granted, the lock over the account's money is taken inside the release and given back as it answers, both before the write is reached"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438 making the test at 243 true, so that 244 reaches `nexus/core/capital_controller/capital_controller.py` 768 and answers at 808, all before `nexus/infrastructure/praxis_connector/outcome_processor.py` 285"
---
# When the money's lock is given back

Where an exit's release is granted, the lock over the account's money is given back as that release answers, which falls before [the result is written down](where-a-realized-result-is-written-down.md).

## Where it is taken

Inside the release itself, rather than by the road that calls for one. The release settles its answer while still holding the lock, so the lock drops as that answer returns — and the write is reached after it.

## Related

- [Where a realized result is written down](where-a-realized-result-is-written-down.md)
- [What a write of the whole state waits on](what-a-write-of-the-whole-state-waits-on.md)
- [What an exit outcome changes](what-an-exit-outcome-changes.md)
- [Which fills come back with a result](which-fills-come-back-with-a-result.md)
- [Which of the store's writes take which locks](which-of-the-stores-writes-take-which-locks.md)
