---
row: N25-01
baseline: 49aa659
created: 2026-11-11 07:30 UTC
modified: 2026-11-11 08:00 UTC
evidence:
  - claim: "The interval is refused unless it is a whole or ordinary number, with a true-or-false refused outright, and it is refused at or below nought"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 51-57"
  - claim: "Nothing asks it to be finite or to be a number at all by value, so one that is no number passes and is kept"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 54 letting it by, kept at 61"
  - claim: "Starting takes the timer's lock and returns at once where it is already running"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 75-77"
  - claim: "Otherwise it marks the timer running and schedules the first tick"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 79-80"
  - claim: "A tick reads the running mark before it does anything, and gives up where the mark has gone"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 119-121"
  - claim: "A tick that got past that reading schedules the next one, and the scheduling reads the mark again before setting a countdown"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 126 into 111-112"
---
# The interval a checkpoint timer takes

[The timer that checkpoints while a host runs](the-timer-that-checkpoints-while-a-host-runs.md) is built with a store, a state and an interval, and the interval is the one thing it checks.

## What the interval must be

A whole or ordinary number, above nought. A true-or-false is refused outright by a test of its own, which it needs: the test beside it counts a true-or-false as a number.

Being finite is not asked. A figure that is no number by value passes the comparison, since that comparison answers false for it, and is kept as the interval between checkpoints.

[The sampler on the Praxis side](what-the-mark-sampler-is-built-with.md) lets the same figure through, asking nothing of the kind either. So the two differ in one thing only: this one turns back an interval of the wrong kind, and that one takes any kind the comparison survives.

## Starting

Starting takes the timer's lock. Where the timer is already running it returns at once, leaving the chain of ticks as it is.

Otherwise it marks the timer running and schedules the first tick.

## The mark, read twice

A tick reads the running mark before anything else and gives up where the mark has gone. A tick that got past that reading takes the checkpoint and then schedules the next tick — and the scheduling reads the mark once more before setting a countdown.

So a stop reaches the chain in three ways: it cancels a countdown that has not fired, it turns back a tick at the mark, and it leaves a tick already past that reading to find the mark gone at its scheduling.

## Related

- [The timer that checkpoints while a host runs](the-timer-that-checkpoints-while-a-host-runs.md)
- [What the mark sampler is built with](what-the-mark-sampler-is-built-with.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
