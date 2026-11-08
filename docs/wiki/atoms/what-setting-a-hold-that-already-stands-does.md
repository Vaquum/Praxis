---
row: N69-03
baseline: 49aa659
created: 2026-11-13 01:30 UTC
modified: 2026-11-13 01:30 UTC
evidence:
  - claim: "Setting a hold that already stands answers from a recompute without touching the hold at all"
    source: "`nexus/core/mode_controller.py` 433-434"
  - claim: "So the reason and the moment recorded on it stay as they were from the first setting"
    source: "`nexus/core/mode_controller.py` 433-434, the writing at 436-438 passed over"
  - claim: "Setting a hold that does not stand marks it, writes the reason, and stamps the moment from the clock the controller was given"
    source: "`nexus/core/mode_controller.py` 436-438"
  - claim: "Clearing a hold that does not stand likewise answers from a recompute without touching it"
    source: "`nexus/core/mode_controller.py` 445-446"
  - claim: "Clearing one that stands unmarks it, empties the reason and drops the moment"
    source: "`nexus/core/mode_controller.py` 448-450"
  - claim: "Either way a recompute is made, so a call that changes no hold still rewrites the blame where the blame has moved"
    source: "`nexus/core/mode_controller.py` 434, or 440, or 446, or 452"
  - claim: "The two named roads hold the lock for the moving and the recompute and drain the notification once the lock is let go"
    source: "`nexus/core/mode_controller.py` 415-418, and 423-426"
---
# What setting a hold that already stands does

Each of the holds on [an account's mode](how-the-mode-is-recomputed.md) is set and cleared through one pair of steps, and both do something even where the hold does not move.

## Setting one that already stands

The hold is not touched. The reason recorded on it, and the moment it was stamped with, stay as they were from the first setting.

So a hold set again with a fresher reason keeps the older one, and a reader of the reason learns why the hold first went on rather than why it was last asked for.

## Setting one that does not stand

It is marked, the reason written, and the moment taken from the clock the controller was given.

## Clearing

Clearing one that is already clear leaves it alone too. Clearing one that stands unmarks it, empties the reason, and drops the moment.

## What happens either way

A recompute is made in all four cases.

The two named roads to a hold hold the lock across the moving and the recompute, and drain the notification once the lock is let go. [The risk breakers](what-the-two-risk-breakers-do.md) reach the same moving by a different road.

So a call that moves no hold can still rewrite the record, where the blame has moved for some other reason. The call answers whether the mode changed, which is a third thing again.

## Related

- [How the mode is recomputed](how-the-mode-is-recomputed.md)
- [Which hold the mode is blamed on](which-hold-the-mode-is-blamed-on.md)
- [What the two risk breakers do](what-the-two-risk-breakers-do.md)
