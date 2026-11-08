---
row: P12-04
baseline: 49aa659
created: 2026-11-10 09:30 UTC
modified: 2026-11-10 09:30 UTC
evidence:
  - claim: "An episode still open when the walk ends records its depth"
    source: "`praxis/metrics/limen_snapshot.py` 274-275"
  - claim: "No length is recorded for it, where a closed episode records both together"
    source: "`praxis/metrics/limen_snapshot.py` 275, against 270"
---
# The falls that never ended

A fall still open when the walk ends gives the report a depth with no length beside it.

## What is recorded

Its depth goes down, in basis points, like any other. Nothing is recorded for how long it lasted.

A fall that recovered records both together, so for every closed fall the two lists gain one each.

## What that means for a reader

The depths and the lengths need not come to the same number. A run ending below its peak gives one more depth than length, and the two lists cannot be paired off position by position past that point.

Running the walk over an equity curve that only falls bears this out: one depth is recorded and no length at all.

So a reader wanting the length of the deepest fall cannot take it from the same position in the other list, and a reader counting falls must say which list they counted.

## Related

- [How a fall from a peak is recorded](how-a-fall-from-a-peak-is-recorded.md)
- [How the bars are cut into days](how-the-bars-are-cut-into-days.md)
