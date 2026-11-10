---
row: N10-05
baseline: 49aa659
created: 2026-11-07 04:30 UTC
modified: 2026-11-07 05:05 UTC
evidence:
  - claim: "Each turn is set going by a one-shot countdown of its own, marked so it cannot hold the process up, and kept under a name made of the strategy and the timer joined by a nul"
    source: "`nexus/strategy/timer_loop.py` 95-99, 100, 101 and 102 before the start at 103"
  - claim: "A turn tests whether the loop still runs before it asks for what the strategy is handed, and where that test falls through it tests again once it has it"
    source: "`nexus/strategy/timer_loop.py` 106-107 ahead of 111, then 113-114 ahead of 117"
  - claim: "Where either test sends the turn back, the next turn is never asked for"
    source: "`nexus/strategy/timer_loop.py` 108, or else 115, each returning rather than reaching 144-145"
  - claim: "A raise of the kind that catch covers is logged and the next turn still asked for, the asking standing outside the catch itself"
    source: "`nexus/strategy/timer_loop.py` 144-145 standing outside the try opened at 110, against the catch at 135 and the logging at 136-142"
  - claim: "A failure of the kind the inner catch covers, in the thing that takes the actions away, is caught around that call alone, and the turn carries on"
    source: "`nexus/strategy/timer_loop.py` 126 inside the try at 125 and caught at 127-134, with the test at 124 standing outside it, before 144-145"
  - claim: "Asking for the next turn builds no countdown where the loop has stopped by then"
    source: "`nexus/strategy/timer_loop.py` 92-93 returning rather than reaching the countdown built at 95-99"
---
# What a turn of a timer does

A turn of a timer is set going by a countdown of its own, which fires once, is marked so it cannot hold the process up, and is kept under a name made of the strategy and the timer together.

## What it checks, and when

A turn tests whether the loop still runs before it asks for [what the strategy is handed](what-a-strategy-is-handed.md). Where that test falls through it tests again once it has it, so a stop the second test sees abandons the turn with the fetch already done. Where either test sends the turn back, the next turn is never asked for.

## The failures the catches cover

A raise of the kind the outer catch covers is logged and the next turn asked for all the same, because the asking stands outside the catch itself. A failure of the kind the inner catch covers, in the thing that takes the actions away, is caught around that call alone, and the turn carries on from there to the asking.

## Where the asking leads to nothing

Asking for the next turn still builds no countdown where the loop has stopped by then. So a chain of turns can end at either test or at the asking, where a raise either catch covers ends nothing.

## Related

- [Which roads reach a strategy](which-roads-reach-a-strategy.md)
- [What a strategy is handed](what-a-strategy-is-handed.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
