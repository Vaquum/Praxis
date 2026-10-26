---
row: N6-11
baseline: 49aa659
created: 2026-10-27 00:30 UTC
modified: 2026-10-27 00:30 UTC
evidence:
  - claim: "Each of the four stops the launcher calls clears a flag and cancels the next turn, and none waits for the turn in hand to end"
    source: "`nexus/core/health_loop.py` 98-102, `nexus/core/mtm_loop.py` 136-140, `nexus/infrastructure/snapshot_scheduler.py` 93-96 and `praxis/launcher.py` 2275-2279, none of them joining"
  - claim: "The health one does take the lock its own turn holds while it works, so it can wait on that part of it"
    source: "`nexus/core/health_loop.py` 98 against 169-182"
  - claim: "Each loop reads the flag again inside its turn and gives up where it finds it cleared, the valuation one reading it twice"
    source: "`nexus/core/health_loop.py` 170-171, `nexus/core/mtm_loop.py` 219-222 and 249-252, and `nexus/infrastructure/snapshot_scheduler.py` 119-121"
  - claim: "A turn past its last reading is no longer stoppable, and runs to whatever end its own work reaches"
    source: "`nexus/core/mtm_loop.py` 249-252 before 271-278 and 293-309, and `nexus/infrastructure/snapshot_scheduler.py` 119-121 before 123"
  - claim: "The loop reading outcomes is the one stop that does wait, and it too can come back with its worker going"
    source: "`nexus/core/outcome_loop.py` 175-177 into 179-185"
---
# What a loop's stop leaves running

Stopping the health, valuation or snapshot loop — or the launcher's own watch — clears a flag and cancels the turn that was due next. It does not end the turn already in hand.

## What the turn in hand does

Each loop reads the flag again inside its turn and gives up where it finds it cleared — the valuation loop reads it twice, once before fetching prices and once after. A turn already past its last reading can no longer be stopped, and runs to whatever end its own work reaches — the valuation one may still abandon its update over a position it has no mark for, and the snapshot one writes its record.

So a stop called at the wrong moment leaves a write still to come, and the caller has no way to know from the call.

## The one that waits

[The loop reading outcomes](stopping-the-loop-that-reads-outcomes.md) is the exception: its stop waits for the worker. Even that can come back with the worker still going.

## Where the health stop differs

It takes the lock its own turn holds while that turn works, so it waits on that part before it even clears the flag. The others clear theirs and return.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [Stopping the loop that reads outcomes](stopping-the-loop-that-reads-outcomes.md)

---

Created 2026-10-27 00:30 UTC · Last modified 2026-10-27 00:30 UTC
