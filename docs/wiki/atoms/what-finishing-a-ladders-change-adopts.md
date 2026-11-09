---
row: P163-02
baseline: 49aa659
created: 2026-11-16 02:00 UTC
modified: 2026-11-16 13:30 UTC
evidence:
  - claim: "The completion is recorded before anything is adopted"
    source: "`execution_manager.py` 9318 reaching 9337-9342, then 9343"
  - claim: "A fresh command is made carrying the new grid and installed under the name the old one had"
    source: "`execution_manager.py` 9345, then 9346, then 9347"
  - claim: "The scheme's generation is promoted to the one just placed"
    source: "`execution_manager.py` 9348"
  - claim: "The phase and the context are both forgotten"
    source: "`execution_manager.py` 9349, then 9350"
  - claim: "Forgetting the context is what takes the change off the road a later pass drives"
    source: "`execution_manager.py` 9350, against 8970, then 8971 into 8972"
  - claim: "The scheme is then given its chance to finish"
    source: "`execution_manager.py` 9358"
  - claim: "A change that planned no rungs at all arrives here straight from the planning"
    source: "`execution_manager.py` 8997 into 8998"
---
# What finishing a ladder's change adopts

Finishing a change to a ladder's grid makes the new grid the live one, and it does so by replacing the command rather than editing it.

## The order of it

The completion is recorded before anything is adopted, so a crash between the record and the adoption leaves a record saying the change finished.

A fresh command is then made carrying the new grid, put on the scheme, and installed under the name the old one had. Anything still holding the command as it was keeps the old grid: the name is what is shared, and the thing behind it is new.

The scheme's generation is promoted to the one just placed, and [a later change](how-a-ladders-prices-are-changed.md) merges against the grid this one left.

## What is forgotten

The phase and the context are both forgotten. Forgetting the context is what takes the change off the road [a later pass](how-a-ladders-change-moves-from-one-phase-to-the-next.md) drives, because that pass does nothing for a scheme whose context is gone.

The scheme is then given its chance to finish, which is how a change that planned no rungs at all — arriving here straight from the planning — can see the ladder through to filled on the cursor it already had.

## Related

- [How a ladder's change moves from one phase to the next](how-a-ladders-change-moves-from-one-phase-to-the-next.md)
- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
- [How a new ladder grid is renumbered](how-a-new-ladder-grid-is-renumbered.md)
