---
row: P164-01
baseline: 49aa659
created: 2026-11-09 12:36 UTC
modified: 2026-11-09 12:36 UTC
evidence:
  - claim: "One reading decides which way the change is given up: whether a cancel has ever been committed to the venue"
    source: "`execution_manager.py` 9225, then 9226"
  - claim: "Where none has, the abandonment is recorded and the phase and context both forgotten"
    source: "`execution_manager.py` 9227-9233, then 9234, then 9235, then 9236, then 9242"
  - claim: "Where one has, a state-unknown is recorded instead and the phase written back"
    source: "`execution_manager.py` 9244-9251, then 9252, then 9253"
  - claim: "That road leaves the context standing, which is what keeps the change on the road a later pass drives"
    source: "`execution_manager.py` 9253, against 9236, read at 8970, then 8971 into 8972"
  - claim: "The commitment is marked the moment a resting rung is found, before any cancel is sent"
    source: "`execution_manager.py` 9143 into 9144"
  - claim: "A resumed change carries the commitment already made"
    source: "`execution_manager.py` 9225, the mark rebuilt at 1433-1441, set at 1440"
---
# Which way a ladder's change is given up

A change to a ladder's grid that cannot go on is given up in one of two ways, and which one is settled by a single reading: whether a cancel has ever been committed to the venue.

## Given up clean

Where no cancel has been committed, the abandonment is recorded and the phase and the context are both forgotten. The old grid is still whole — nothing was sent against it — and the ladder carries on as though no change had been asked for.

## Held instead

Where a cancel has been committed, a state-unknown is recorded instead and the phase written back as it was. A rung may already be gone at the venue, and nothing here can say which.

This road leaves the context standing, and that is what keeps the change on the road [a later pass](how-a-ladders-change-moves-from-one-phase-to-the-next.md) drives: a pass does nothing for a scheme whose context is gone, and the clean road is the one that takes it away.

## When the commitment is made

The moment a resting rung is found, before any cancel is sent. So the choice between the two roads turns on what was about to be attempted rather than on what the venue confirmed — and [a resumed change](what-a-resumed-scheme-comes-back-holding.md) comes back carrying the commitment already made.

## Related

- [What retiring a ladder's old grid counts](what-retiring-a-ladders-old-grid-counts.md)
- [How a ladder's change moves from one phase to the next](how-a-ladders-change-moves-from-one-phase-to-the-next.md)
- [What a resumed scheme comes back holding](what-a-resumed-scheme-comes-back-holding.md)
