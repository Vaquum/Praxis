---
row: N78-04
baseline: 49aa659
created: 2026-11-09 02:48 UTC
modified: 2026-11-09 02:48 UTC
evidence:
  - claim: "Growing a position reads the five figures it works from before any lock is taken"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 473, and 474, and 475, and 476, and 477, ahead of 487"
  - claim: "Reducing reads two of its own into names of their own the same way"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 513, and 514, ahead of 558"
  - claim: "A growing answers from outside the lock it took"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 492, the lock let go after 490"
  - claim: "Clearing a pending sale takes the positions lock before it looks the position up"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 604, ahead of 605"
  - claim: "Moving the strategy's own figures has a second way in that takes their lock itself, and nothing under `nexus/` calls it outside a comment"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 778-779, against the one call at 286, which names the form that assumes the lock"
---
# Where the locks sit on a position change

The routines that move a position take the positions lock for the writing alone, with one exception.

## Reading before locking

Growing a position reads the five figures it works from before any lock is taken, and reducing reads two of its own into names of their own the same way. The working out therefore happens outside the lock, and only the writing of the result is inside it.

A growing then answers from outside the lock as well — it is let go once the three fields are written, before the answer is given.

## Where the lock comes first

Clearing a pending sale is the exception. It takes the positions lock before it even looks the position up, so the lookup and the lowering happen under one hold.

So a position found there is a position still in the book when it is lowered, which the other routines cannot say of what they read.

## The lock nothing takes

Moving the strategy's own figures has a second way in, one that takes their lock itself. Nothing on this side calls it outside a comment — [the one place those figures move](where-a-realized-result-is-written-down.md) names the form that assumes the lock is already held.

## Related

- [What a position change checks](what-a-position-change-checks.md)
- [Where a realized result is written down](where-a-realized-result-is-written-down.md)
