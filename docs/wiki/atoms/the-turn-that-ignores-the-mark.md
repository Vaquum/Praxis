---
row: N35-02
baseline: 49aa659
created: 2026-11-08 16:38 UTC
modified: 2026-11-08 16:38 UTC
evidence:
  - claim: "A turn driven by hand asks the applying not to respect the mark, so it applies whether or not the loop is running"
    source: "`nexus/core/health_loop.py` 113 against 170-171"
  - claim: "A turn the countdown drives asks it to respect the mark, and schedules the next tick afterwards"
    source: "`nexus/core/health_loop.py` 127, scheduling at 129-130"
  - claim: "A turn driven by hand schedules nothing"
    source: "`nexus/core/health_loop.py` 113, which ends there"
  - claim: "Where a controller is wired, the reading is handed to it rather than written, and what the state ends up saying is the controller's answer"
    source: "`nexus/core/health_loop.py` 176-177 into 182-183"
  - claim: "With no controller, the reading is written only where it differs from the mode standing"
    source: "`nexus/core/health_loop.py` 179-180 into 201-202"
  - claim: "The comparison at the end suppresses the record of a transition, the writing having already happened"
    source: "`nexus/core/health_loop.py` 188-189 standing after 176-180"
---
# The turn that ignores the mark

[The health loop](the-health-loops-interval-and-mark.md) can be turned by hand as well as by its own countdown, and the hand-driven turn differs in two ways.

## The two differences

It asks the applying to skip the running mark. A loop that was never started, and one already stopped, therefore still takes a reading and still applies it.

And it schedules nothing. A turn the countdown drives sets the next countdown going after it applies; a turn driven by hand ends where it finishes.

So a caller can drive the cadence itself, one turn at a time, without starting the loop.

## What the turn applies

Where [a mode controller](what-stops-a-health-turn.md) is wired, the reading is handed to it rather than written. What the state ends up saying is the controller's answer, which weighs holds and risk alongside the reading — so the mode written need not be the mode read.

With no controller wired, the reading is written straight into the state, and only where it differs from the mode already standing.

## What the comparison at the end does

The turn ends by comparing the mode and reason standing afterwards with those standing before, and returns where both match.

That comparison reaches only the record of a transition. The writing has already happened by then, whichever road it took.

## Related

- [The health loop's interval and mark](the-health-loops-interval-and-mark.md)
- [The two roads a turn's answer takes](the-two-roads-a-turns-answer-takes.md)
- [What stops a health turn](what-stops-a-health-turn.md)
