---
row: P4-56
baseline: 49aa659
created: 2026-10-14 10:55 UTC
modified: 2026-11-09 14:05 UTC
evidence:
  - claim: "A plan that comes to nothing finishes the change with no new rungs at all"
    source: "`execution_manager.py` 8997-9001"
  - claim: "An account frozen for protection has its placement held back and returns"
    source: "`execution_manager.py` 9016-9023"
  - claim: "A ladder being wound up retires both grids and places none"
    source: "`execution_manager.py` 8974-8976 into 9050-9054"
  - claim: "A rung already resting is skipped, and so is one already filled"
    source: "`execution_manager.py` 9280, then 9281-9284, then 9285, then 9286-9289 and 9291-9292"
  - claim: "A rung the record has ended any other way stops the change again"
    source: "`execution_manager.py` 9294-9299"
  - claim: "A send that comes back with no name stops it too"
    source: "`execution_manager.py` 9301 and 9304-9305"
---
# What stops a ladder's new rungs

The second half of [changing a ladder's prices](how-a-ladders-prices-are-changed.md) puts the new grid up, one rung at a time. Four things can leave that grid short, and the change is resumable rather than all-or-nothing.

## Nothing to place

Where what is left to buy will not divide into rungs the venue would take, the plan comes to nothing and the change simply finishes: the old grid is gone and no new one replaces it.

## Held back

An account frozen because [protection was lost](when-protection-is-lost.md) places nothing and returns, leaving the grid empty until that freeze lifts.

A ladder being wound up takes both grids down and places none at all — it is ending, and a fresh grid would only have to be cancelled.

## Stalled part way up

Each rung is checked before it is sent. One already resting is skipped, and so is one already filled: a re-run adopts what is there rather than placing it twice.

A rung the record has ended any other way stops the change where it stands, and so does a send that comes back without a name. Either leaves a grid part way up, which [the scan](how-waiting-work-is-drained.md) will try again — and can stop at the same rung each time.

## Related

- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
- [Orders at several prices](orders-at-several-prices.md)
- [What a restart puts back](what-a-restart-puts-back.md)

---

Created 2026-10-14 10:55 UTC · Last modified 2026-11-09 14:05 UTC
