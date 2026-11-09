---
row: N6-07
baseline: 49aa659
created: 2026-10-26 20:10 UTC
modified: 2026-11-13 17:30 UTC
evidence:
  - claim: "The loop reading outcomes is the last of the three the stopping sequence calls a stop on, and that call comes before any strategy is asked"
    source: "`nexus/startup/shutdown_sequencer.py` 186 after 184-185 and before 187-189"
  - claim: "Its worker takes outcomes off the same queue the stopping's own waiting will read from, and the stop is called before that waiting starts"
    source: "`nexus/core/outcome_loop.py` 211 reached from 379-382, against `nexus/startup/shutdown_sequencer.py` 650, the stop at 186 before 189"
  - claim: "The stop raises a flag the worker reads once per turn, and waits for the worker to come out, for a span the stopping leaves to the loop itself"
    source: "`nexus/core/outcome_loop.py` 175-177, the flag read at 380, the call made without a span at `nexus/startup/shutdown_sequencer.py` 270"
  - claim: "A worker still going when that wait ends is logged and left in place, its slot kept"
    source: "`nexus/core/outcome_loop.py` 179-185"
  - claim: "A kept slot holds off a fresh worker only while the old one is alive"
    source: "`nexus/core/outcome_loop.py` 145-147 before 149-155"
  - claim: "A worker left going finishes the turn it is in and stops at the next reading of the flag, so it can take one further outcome and no more"
    source: "`nexus/core/outcome_loop.py` 380 around 382 into 211"
  - claim: "Only a worker that came out has its slot cleared"
    source: "`nexus/core/outcome_loop.py` 187-189"
  - claim: "One still going when the strategies are asked is logged again there"
    source: "`nexus/startup/shutdown_sequencer.py` 292-298"
  - claim: "Where no such loop is wired the shutting is passed over without a line"
    source: "`nexus/startup/shutdown_sequencer.py` 267-268"
  - claim: "The list of positions handed to the strategies is built next, under a lock where one was supplied, and the lock is let go before any strategy is asked"
    source: "`nexus/startup/shutdown_sequencer.py` 300-303 before 305"
---
# Stopping the loop that reads outcomes

The loop reading outcomes is the last of the three the stopping sequence calls a stop on, and its stop can come back while the worker is still going.

## Why it is stopped before the waiting

Its worker takes [outcomes](what-an-outcome-is.md) off the same queue [the stopping's own waiting](what-a-stopping-host-waits-for.md) will read from once the sales are away. It is stopped before the waiting starts, which is what is meant to leave that queue to the waiting alone.

## What the stop does

The stop raises a flag the worker reads once per turn, and waits for it to come out — for a span the stopping leaves to the loop itself. A worker that comes out has its slot cleared. One still going when the wait ends is logged and left in place, its slot kept — which holds off a fresh worker only while the old one is alive — and logged again where it is still going when the strategies are asked.

A worker left going finishes the turn it is in and stops at the next reading of the flag. So it can take one further outcome off the queue, which the waiting then never sees, and no more than one. Where no such loop is wired at all, the stop is passed over without a line.

## What follows it

The list of positions handed to the strategies is built next, under a lock where one was supplied, and that lock is let go before any strategy is asked.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [Where an outcome outside the wait is sent](where-an-outcome-outside-the-wait-is-sent.md)

---

Created 2026-10-26 20:10 UTC · Last modified 2026-10-26 20:10 UTC
