---
row: P88-02
baseline: 49aa659
created: 2026-11-09 06:08 UTC
modified: 2026-11-09 06:08 UTC
evidence:
  - claim: "A closing looks the order up first and answers at once where the projection does not hold it"
    source: "`trading_state.py` 365 into 366-367"
  - claim: "The venue's own name for the order is taken off the event where the event carries one, read by asking rather than by naming the field"
    source: "`trading_state.py` 369 into 370-371"
  - claim: "The final standing and the moment are set from the event before the order is closed"
    source: "`trading_state.py` 373, and 374, ahead of 375"
  - claim: "Closing takes the order out of the live book, and warns and answers where it was already gone"
    source: "`trading_state.py` 630 into 631-637"
  - claim: "The order then goes into the closed book under the same name"
    source: "`trading_state.py` 639"
  - claim: "Nothing in the closing touches the mapping from a leg to its parent"
    source: "`trading_state.py` 630, and 639, the whole of the routine"
---
# What closing an order moves it to

Closing an order moves it from the live book to the closed one, under the same name, so it stays readable afterwards.

## Before the move

The order is looked up first, and a projection that does not hold it answers at once. Then the venue's own name for the order is taken off the event — where the event carries one, read by asking the event rather than by naming the field, so a kind of event without it passes through.

The final standing and the moment are set from the event before the order is closed.

## The move

Closing takes the order out of the live book. Where it was already gone, that is reported as a warning and the closing answers there.

Otherwise the order goes into the closed book under the same name. So a name that once meant a live order means a closed one afterwards, and a reader looking in one book alone can mistake a closed order for one that never existed.

## What the closing leaves alone

The mapping from a leg to its parent. Nothing in the routine touches it, so a leg's fill arriving after its parent has closed still finds the parent.

## Related

- [How an event finds its way through the projection](how-an-event-finds-its-way-through-the-projection.md)
