---
row: N79-01
baseline: 49aa659
created: 2026-11-13 13:30 UTC
modified: 2026-11-13 13:30 UTC
evidence:
  - claim: "The flag saying the loop is running starts clear, and the lock guarding it is made as the loop is built"
    source: "`nexus/core/mtm_loop.py` 114, and 115"
  - claim: "Starting takes that lock, answers at once where the flag is already set, and otherwise sets it and schedules the first tick"
    source: "`nexus/core/mtm_loop.py` 126 into 127-128, then 130-131"
  - claim: "A tick is a timer made for the interval, marked as a background one, and started"
    source: "`nexus/core/mtm_loop.py` 157, then 158, then 159"
  - claim: "Scheduling refuses where the flag is clear, so nothing is set going once a stop has cleared it"
    source: "`nexus/core/mtm_loop.py` 154-155, the flag cleared at 137"
  - claim: "A tick reads the flag under the lock and answers where it is clear, then marks with the lock released"
    source: "`nexus/core/mtm_loop.py` 162-164, then 166"
  - claim: "The next tick is scheduled only once that marking has returned, under the lock again"
    source: "`nexus/core/mtm_loop.py` 168-169, after 166"
---
# How the mark loop paces itself

The loop that values open positions runs on a timer it makes afresh for each tick, and the next timer is made only once the last pass has finished.

## Starting

The flag saying the loop is running starts clear, and the lock guarding it is made as the loop is built. Starting takes that lock, answers at once where the flag is already set, and otherwise sets it and schedules the first tick.

## The timer

A tick is a timer made for the interval, marked as a background one so it cannot hold a shutdown up, and started. Scheduling refuses where the flag is clear, so nothing is set going once a stop has cleared it.

## The gap between ticks

A tick reads the flag under the lock, answers where it is clear, and then marks with the lock released. Only once the marking has returned is the next tick scheduled, under the lock again.

So the gap is measured from the end of one pass to the start of the next. A pass slower than the interval stretches the cadence rather than overlapping itself, and two passes can never run at once.

## A stop part-way through

A stop during a marking does not reach it. The marking finishes, and the scheduling that follows finds the flag clear and sets nothing going.

## Related

- [What a mark works out for each position](what-a-mark-works-out-for-each-position.md)
- [What the mark loop leaves unguarded](what-the-mark-loop-leaves-unguarded.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
