---
row: P4-47
baseline: 49aa659
created: 2026-10-14 07:10 UTC
modified: 2026-10-16 08:20 UTC
evidence:
  - claim: "Another change already under way, a ladder under any hold, and settings that are not a ladder's each turn it away first"
    source: "`execution_manager.py` 8882-8889, 8891-8897 and 8899-8904"
  - claim: "The change is written down and the stage set to cancelling before the venue is touched"
    source: "`execution_manager.py` 8941-8942 before 8951"
  - claim: "A rung the record already has as ended is accepted, one it has no order for is passed over, and the rest are cancelled and asked after before any new rung is placed"
    source: "`execution_manager.py` 9131-9141 and 9143-9174, before 9026"
  - claim: "A cancel that fails, a query that fails, a rung not ended, and fills that will not reconcile each stop the change"
    source: "`execution_manager.py` 9147-9156, 9159-9167, 9169-9174 and 9176-9186"
  - claim: "A cancel is committed before any of those four stops is reached, so the write-off that clears the stage is not the road they take"
    source: "`execution_manager.py` 9144 before 9153 and 9163, against 9226 into 9234-9235"
  - claim: "A stop once a cancel has gone writes the stage down as unknown and keeps it for the watch"
    source: "`execution_manager.py` 9252-9253"
  - claim: "The new plan is sized from what the old grid actually filled, and written down before any rung goes out"
    source: "`execution_manager.py` 8991-8995 and 9003-9014"
---
# How a ladder's prices are changed

Changing the prices of [a ladder](orders-at-several-prices.md) replaces its whole grid: the rungs resting now come down, and a fresh set goes up for what is left to buy. The stage reached is written down, so the same work finishes whoever picks it up.

## Cancelled first, confirmed second

Another change already under way, a ladder under any hold, and settings that belong to another way of working each turn it away first, logged and returned.

Past those, the change is written down and the stage set to cancelling, before the venue hears anything.

Each rung of the old grid is then taken down. One the record already has as ended is accepted as it stands, and one it has no order for is passed over; the rest are cancelled and asked after, and must come back ended with their fills taken in. Only once all of them have can a new rung go out. Four things stop the change here: a cancel the venue refuses, a query that fails, a rung it still shows working, and fills that will not reconcile.

## What a stop leaves

By the time any of those four stops the change, a cancel has already been committed, so the stage is written down as unknown and kept: the grid is part-dismantled, and [the scan](how-waiting-work-is-drained.md) picks it up again. The clean write-off that clears the stage and leaves the old grid whole belongs to a stop before any cancel was committed.

## Then placed

What is left to buy is worked out from what the old grid filled, and the new plan written down before any rung goes out. [What happens to that plan](what-stops-a-ladders-new-rungs.md) is its own matter: it can come to nothing, be held back, or stall part way up.

## Related

- [Orders at several prices](orders-at-several-prices.md)
- [Changing work already sent](changing-work-already-sent.md)
- [What stops a ladder's new rungs](what-stops-a-ladders-new-rungs.md)
- [What a restart puts back](what-a-restart-puts-back.md)

---

Created 2026-10-14 07:10 UTC · Last modified 2026-10-16 08:20 UTC
