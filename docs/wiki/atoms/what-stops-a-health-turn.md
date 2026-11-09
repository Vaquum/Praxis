---
row: N15-05
baseline: 49aa659
created: 2026-11-08 10:13 UTC
modified: 2026-11-08 10:13 UTC
evidence:
  - claim: "The seconds between turns are refused where they are a true-or-false, and refused where they stand at or below nought"
    source: "`nexus/core/health_loop.py` 62-68"
  - claim: "That check compares rather than asking for finiteness, so a figure that is not a number and one standing at infinity are both let by"
    source: "`nexus/core/health_loop.py` 65, against `nexus/core/health_evaluator.py` 42, which asks for finiteness"
  - claim: "A failed refresh is told and passed over, the turn going on to fetch"
    source: "`nexus/core/health_loop.py` 151-155 before 157"
  - claim: "A failed fetch abandons the turn, and so does a failed weighing"
    source: "`nexus/core/health_loop.py` 157-161, or 163-167"
---
# What stops a health turn

One check at the loop's making and two failures in the turn itself are what stop a turn of the health loop.

## The seconds between turns

Refused where they are a true-or-false, and refused where they stand at or below nought.

That check compares rather than asking for finiteness. A figure that is not a number is let by, because the comparison answers false for it, and so is one standing at infinity — where [the snapshot's own figures](what-a-health-snapshot-refuses.md) are asked for finiteness and both are turned back.

## The failure the turn survives

Where a refresher of the rolling loss was supplied, the turn calls it first. A failure there is told and passed over: the turn goes on to fetch, and reaches its answer.

## The two that end it

A failed fetch abandons the turn. So does a failed weighing. Either leaves the mode as it stood, and the next turn starts over.

So where a refresher was supplied, the first of the three things a turn does before it writes is the only one that may fail without costing the turn.

## Related

- [The two roads a turn's answer takes](the-two-roads-a-turns-answer-takes.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
