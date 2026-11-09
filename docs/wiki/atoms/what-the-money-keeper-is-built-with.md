---
row: N84-04
baseline: 49aa659
created: 2026-11-13 18:30 UTC
modified: 2026-11-13 18:30 UTC
evidence:
  - claim: "The share allowed per trade must read as a figure at all, and a thing that does not raises a different kind of complaint from the rest"
    source: "`nexus/core/capital_controller/capital_controller.py` 86 into 87-91"
  - claim: "It must then be finite, and must stand above nought"
    source: "`nexus/core/capital_controller/capital_controller.py` 92 into 93-97, then 98 into 99-103"
  - claim: "The clock the keeper uses, where none is handed in, reads the current moment in UTC"
    source: "`nexus/core/capital_controller/capital_controller.py` 41"
  - claim: "The sweeping of stale reservations takes its moment from that clock where none is handed to it"
    source: "`nexus/core/capital_controller/capital_controller.py` 477 into 478"
  - claim: "A send asks for that sweep before it builds the order it is about to track"
    source: "`nexus/core/capital_controller/capital_controller.py` 578, ahead of 580"
  - claim: "A send that got through answers a success carrying nothing else"
    source: "`nexus/core/capital_controller/capital_controller.py` 595"
---
# What the money keeper is built with

Building the keeper of a host's money weighs one figure three ways, and takes a clock it will use for everything timed.

## The three weighings

The share allowed per trade must read as a figure at all; a thing that does not raises a different kind of complaint from the other two. It must then be finite, and must stand above nought.

So a share handed in as text is a complaint about its type, and a share handed in as an unusable number is a complaint about its value. Both stop the building.

## The clock

Where none is handed in, the clock reads the current moment in UTC. Everything timed afterwards goes through it, so a caller handing in a clock of its own moves every deadline the keeper keeps.

## What the clock is used for

The sweeping of stale reservations takes its moment from that clock where none is handed to it. A send asks for that sweep before it builds the order it is about to track.

So the order a send begins tracking is built against a book from which [everything already expired](when-a-reservation-times-out.md) has just been cleared. A send that got through answers a success carrying nothing else.

## Related

- [When a reservation times out](when-a-reservation-times-out.md)
- [What a strategy's budget is worked out from](what-a-strategys-budget-is-worked-out-from.md)
