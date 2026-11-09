---
row: N35-01
baseline: 49aa659
created: 2026-11-08 16:38 UTC
modified: 2026-11-08 16:38 UTC
evidence:
  - claim: "The interval is refused unless it is a whole or ordinary number, with a true-or-false refused outright, and is refused at or below nought"
    source: "`nexus/core/health_loop.py` 62-68"
  - claim: "Finiteness is never asked, so a figure that is no number by value passes the comparison and is kept"
    source: "`nexus/core/health_loop.py` 65 letting it by, kept at 73"
  - claim: "Starting takes the loop's lock and returns at once where it is already running"
    source: "`nexus/core/health_loop.py` 89-91"
  - claim: "Otherwise it marks the loop running and schedules the first tick"
    source: "`nexus/core/health_loop.py` 92-93"
  - claim: "A tick reads the mark before doing anything, the scheduling after it reads the mark again, and the applying between them reads it a third time"
    source: "`nexus/core/health_loop.py` 123-125, and 116-117 reached from 130, and 170-171"
---
# The health loop's interval and mark

The loop that reads health and moves the mode is built with a way of taking a reading, something to weigh it against, the state to write into, and an interval. The interval is the one thing it checks.

## What the interval must be

A whole or ordinary number, and above nought by comparison. A true-or-false is refused outright by a test of its own, which it needs: the test beside it counts a true-or-false as a number.

Being finite is not asked. A figure that is no number by value passes the comparison and is kept as the time between readings — the same gate, and the same gap in it, as [the checkpoint timer's](the-interval-a-checkpoint-timer-takes.md).

## Starting, and the mark

Starting takes the loop's lock and returns at once where the loop is already running. Otherwise it marks the loop running and schedules the first tick.

## The mark, read three times

A tick reads the mark before it does anything. The applying it then runs reads the mark again, after the reading has been taken and weighed, before it writes anything. The scheduling that follows reads it a third time, before setting the next countdown.

So a stop reaches this loop one place further in than it reaches [the checkpoint timer](the-interval-a-checkpoint-timer-takes.md), where nothing stands between the tick's own reading and the checkpoint being taken.

## Related

- [The interval a checkpoint timer takes](the-interval-a-checkpoint-timer-takes.md)
- [The turn that ignores the mark](the-turn-that-ignores-the-mark.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
