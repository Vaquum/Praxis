---
row: P70-05
baseline: 49aa659
created: 2026-11-13 02:00 UTC
modified: 2026-11-13 02:00 UTC
evidence:
  - claim: "A slice of an evenly spread order would be weighed against the smallest size alone, the slice taken as the whole divided by the count"
    source: "`validate_trade_command.py` 416-422"
  - claim: "A slice of a weighted order would be weighed the same single way, once per weight"
    source: "`validate_trade_command.py` 424-426"
  - claim: "A hidden order's shown amount would be weighed four ways: the smallest size, the step in size, the step in price on its resting price, and the smallest value on the two multiplied"
    source: "`validate_trade_command.py` 428-432"
  - claim: "A ladder's levels would be weighed three ways each, the step in size not among them"
    source: "`validate_trade_command.py` 434-441"
  - claim: "A ladder level's size comes from its weight where weights were given, and from the whole divided by the number of levels where they were not"
    source: "`validate_trade_command.py` 438"
  - claim: "Four small checks do all of it, each raising with a label naming what was weighed"
    source: "`validate_trade_command.py` 447-449, or 461-463, or 469-471, or 477-479"
---
# What the per-child rules would weigh

[The step that never runs](the-venue-rules-that-are-never-applied.md) weighs the pieces a request would be broken into, and weighs a different number of things for each shape.

## One thing each

A slice of an evenly spread order: the smallest size the venue trades in, and nothing else. The slice is taken as the whole amount divided by the count.

A slice of a weighted order: the same single thing, once per weight.

So neither shape would have its slices weighed against the step in size, the step in price, or the smallest value — and an evenly spread order gets one check for all its slices, since they are all the same size.

## Four things

A hidden order's shown amount: the smallest size, the step in size, the step in price on its resting price, and the smallest value on the two multiplied.

## Three things

A ladder's levels, each: the smallest size, the step in price, and the smallest value. The step in size is not among them, so a level sized off a weight could stand between two steps and pass.

A level's size comes from its weight where weights were given, and from the whole divided by the number of levels where they were not.

## How it is written

Four small checks do all of it, each raising with a label naming what was weighed.

## Related

- [The venue rules that are never applied](the-venue-rules-that-are-never-applied.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)
