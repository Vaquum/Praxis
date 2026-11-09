---
row: P163-01
baseline: 49aa659
created: 2026-11-16 02:00 UTC
modified: 2026-11-16 02:00 UTC
evidence:
  - claim: "A change with no context left on the scheme does nothing"
    source: "`execution_manager.py` 8970, then 8971 into 8972"
  - claim: "A scheme held for draining is handed to the draining instead"
    source: "`execution_manager.py` 8974, then 8975, then 8976"
  - claim: "The new grid's settings are rebuilt from the context on every pass"
    source: "`execution_manager.py` 8978"
  - claim: "In the first phase the old grid is retired, and a retiring that answers nothing ends the pass"
    source: "`execution_manager.py` 8983, then 8984, then 8988 into 8989"
  - claim: "The remainder is worked out from the figures the retiring answered with, and the new grid planned against it"
    source: "`execution_manager.py` 8991, then 8993, then 8994, then 8995"
  - claim: "A plan with no rungs in it finishes the change there"
    source: "`execution_manager.py` 8997 into 8998, then 9001"
  - claim: "The plan is recorded, kept on the context, and the phase moved to placing"
    source: "`execution_manager.py` 9003-9011, then 9012, then 9013, then 9014"
  - claim: "The placing phase is tested after the first phase rather than instead of it, so one pass can run both"
    source: "`execution_manager.py` 9014, then 9016"
  - claim: "A scheme held for protection places nothing and leaves the phase where it is"
    source: "`execution_manager.py` 9017, then 9023"
  - claim: "Otherwise the planned rungs are placed"
    source: "`execution_manager.py` 9025, then 9026"
---
# How a ladder's change moves from one phase to the next

Changing a ladder's grid runs in two phases — retiring the old rungs and placing the new ones — and the phase written on the scheme is what lets a second pass pick up where the first stopped.

## What a pass does first

A change with no context left on the scheme does nothing: the context is the change, and its absence means there is none to drive.

A scheme held for draining is handed to the draining instead. Otherwise the new grid's settings are rebuilt from the context, on this pass as on every other.

## Retiring

In the retiring phase the old grid is retired, and a retiring that answers nothing ends the pass — the phase stays as it was, so the next pass retires again.

The remainder is then worked out from the figures the retiring answered with, and the new grid planned against it. A plan with no rungs in it finishes the change there. Otherwise the plan is recorded, kept on the context, and the phase moved to placing.

## Placing

The placing phase is tested after the retiring phase rather than instead of it, so a pass that has just finished retiring goes straight on to place. The phase is what a later pass reads, and nothing re-reads it in between.

A scheme held for protection places nothing and leaves the phase at placing. Otherwise the planned rungs are placed.

## Related

- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
- [How a new ladder grid is renumbered](how-a-new-ladder-grid-is-renumbered.md)
- [What retiring a ladder's old grid counts](what-retiring-a-ladders-old-grid-counts.md)
