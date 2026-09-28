---
row: P2-20
baseline: 49aa659
created: 2026-09-27 21:39 UTC
modified: 2026-09-28 07:25 UTC
evidence:
  - claim: "The prices are named outright, at least two of them"
    source: "`ladder_dca_params.py` 43-45 with the figure at 18, the prices held at 36"
  - claim: "The amount is split by weights where given"
    source: "`execution_manager.py` 517"
  - claim: "It is split evenly where none were given"
    source: "`execution_manager.py` 519"
  - claim: "Each amount is paired with the price at the same position"
    source: "`execution_manager.py` 521"
  - claim: "It keeps a record of the same kind as work fed out over time, in the same place"
    source: "built at `execution_manager.py` 6120-6133, put at 6134 where 5779-5795 puts its own"
  - claim: "That record carries no gap between parts, where timed work carries one"
    source: "`execution_manager.py` 6127 against 5783"
  - claim: "Every order goes out in one pass, one after another"
    source: "`execution_manager.py` 6136-6137"
  - claim: "On that first placing the count moves on after each, and progress is written down"
    source: "`execution_manager.py` 6152-6153"
  - claim: "Replacing them later moves neither count inside the loop, setting both once all are placed"
    source: "`execution_manager.py` 9301-9313 against 9315-9317"
  - claim: "One that cannot be placed stops the rest"
    source: "`execution_manager.py` 6139-6146"
  - claim: "An order already finished when it returns is not counted among those working"
    source: "`execution_manager.py` 6148-6150"
  - claim: "Anything it filled at once is dealt with as it is sent"
    source: "`execution_manager.py` 6251-6270"
  - claim: "No next time is set, the field being left at its default"
    source: "`execution_manager.py` 373, left alone by 6123-6133"
  - claim: "The worker sends more only where a next time is set"
    source: "`execution_manager.py` 5831-5839"
  - claim: "A repair can still finish placing replacements from a change already under way"
    source: "`execution_manager.py` 7328-7329 into 9016-9027 and 9301-9303"
---
# Orders at several prices

Some work is not one order at one price. An amount is spread across several prices named outright, each getting an order of its own. There must be at least two.

It keeps a record of the same kind as [work fed out over time](work-fed-out-over-time.md), in the same place, but with no gap between parts: the prices do the waiting instead of a clock.

## How the amount is split

The amount is split by weights where weights were given, evenly where not — the same two ways timed work divides.

Each amount is then paired with the price at the same position: the first to the first, and so on down.

## How they go out

All the orders go out in one pass, one after another. On that first placing the count of parts sent moves on after each, and the progress is written down, so there is a record of how far the placing got.

Replacing them later works differently. Neither the number sent nor the total moves inside the loop; both are set once every replacement is placed.

An order that cannot be placed stops the rest. Those already out stay out, and the loop ends where it stood.

Not all end up waiting. Whatever an order fills as it is sent is dealt with there, and one returning already finished is not counted among those still working.

## What comes after

No next time is set, and [the worker](how-waiting-work-is-drained.md) sends more only where one is. So it will not add to these of its own accord.

A repair can finish placing replacements where a change to the prices was already under way. It does not go back for orders missed when the first placing failed.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [The worker](how-waiting-work-is-drained.md)
