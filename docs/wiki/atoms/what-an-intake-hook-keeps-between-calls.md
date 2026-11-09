---
row: N82-02
baseline: 49aa659
created: 2026-11-13 17:00 UTC
modified: 2026-11-13 17:00 UTC
evidence:
  - claim: "Each of the two counting hooks is handed a clock or makes one that reads the current moment in UTC"
    source: "`nexus/core/validator/intake_stage.py` 97, or 143"
  - claim: "The record each keeps and the lock guarding it are made once, as the hook is built"
    source: "`nexus/core/validator/intake_stage.py` 98-99, or 145-147"
  - claim: "The hook is handed back from inside that building, so every call of it shares the one record"
    source: "`nexus/core/validator/intake_stage.py` 123, or 200, each standing after the record made at 98-99, or 145-147"
  - claim: "A call reads the clock once and works its cutoff from that one reading"
    source: "`nexus/core/validator/intake_stage.py` 105-106, or 175-176"
  - claim: "The dropping of stale entries and the weighing both happen under the lock"
    source: "`nexus/core/validator/intake_stage.py` 108, or 178"
  - claim: "A call that found nothing wrong answers with nothing, from outside the lock"
    source: "`nexus/core/validator/intake_stage.py` 121, or 198"
  - claim: "The window one of them measures is worked out once, as the hook is built, from the figure given in thousandths"
    source: "`nexus/core/validator/intake_stage.py` 144"
---
# What an intake hook keeps between calls

Two of the intake hooks count things over a window, and each keeps its own record of what it has seen.

## What is made once

The record and the lock guarding it are made as the hook is built, not per call. The hook is handed back from inside that building, so every call of it shares the one record.

One of the two also works out its window then, from the figure it was given in thousandths of a second.

## The clock

Each is handed a clock or makes one that reads the current moment in UTC. So a caller can hand in a clock of its own, and the hook has no other way of knowing the time.

## What a call does

Reads the clock once, and works its cutoff from that one reading. Everything after is measured against that moment, not against a clock read again part-way.

The dropping of stale entries and the weighing both happen under the lock, so a second call cannot see the record half-pruned.

## The quiet answer

A call that found nothing wrong answers with nothing, from outside the lock — [which is what lets the stage move to the next hook](what-the-intake-stage-holds-its-hooks-to.md).

## Related

- [What the intake stage holds its hooks to](what-the-intake-stage-holds-its-hooks-to.md)
- [The order the intake hooks stand in](the-order-the-intake-hooks-stand-in.md)
