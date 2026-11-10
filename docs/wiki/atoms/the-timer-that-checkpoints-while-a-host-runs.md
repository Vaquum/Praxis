---
row: N8-05
baseline: 49aa659
created: 2026-10-28 18:45 UTC
modified: 2026-10-29 09:37 UTC
evidence:
  - claim: "The timer sets each turn a span after the last, the span read from the environment and standing at five minutes where it carries nothing"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 114-116, the span read at `praxis/launcher.py` 4591-4593 over the figure at 207"
  - claim: "A failed checkpoint is passed over and the turn after it still runs, each turn calling for a whole checkpoint of its own and carrying nothing over from one that failed"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 123 into 147, the failure swallowed at 148-149, the next turn set at 125-126 after it returns"
  - claim: "The timer's stop takes the lock, clears the flag and cancels the turn due next, and writes no record of its own"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 92-96"
---
# The timer that checkpoints while a host runs

A timer asks the host for [a checkpoint](what-a-checkpoint-holds.md) at a fixed spacing.

## How the spacing is set

Each turn is set a span after the one before it, rather than at a fixed point on the clock, so a slow checkpoint pushes the next turn later by however long it took.

The span comes from the host's surroundings when Praxis starts it. Where nothing is given there, it stands at five minutes.

## What a failed turn costs

A turn whose checkpoint fails is passed over, and the turn after it is set as usual. The timer makes no second attempt of its own and waits the full span.

Each turn is a checkpoint in its own right and carries nothing over from one that failed, so [a half-finished rewrite](how-the-checkpoint-rewrites-the-log.md) is not resumed by the turn that follows it.

## How it ends

The stop takes the timer's lock, lowers the flag the turns run under, and cancels the turn already due next.

It writes no record of its own on the way out, so the last turn to complete is the last checkpoint the timer causes.

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [How the checkpoint rewrites the log](how-the-checkpoint-rewrites-the-log.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)

---

Created 2026-10-28 18:45 UTC · Last modified 2026-10-29 09:37 UTC
