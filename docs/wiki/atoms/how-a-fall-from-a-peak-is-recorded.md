---
row: P12-03
baseline: 49aa659
created: 2026-11-08 14:05 UTC
modified: 2026-11-08 14:05 UTC
evidence:
  - claim: "A peak is kept that only rises, and each fall is measured against it"
    source: "`praxis/metrics/limen_snapshot.py` 256-257"
  - claim: "An episode opens on the first fall below the peak"
    source: "`praxis/metrics/limen_snapshot.py` 260-263"
  - claim: "It deepens while the fall continues"
    source: "`praxis/metrics/limen_snapshot.py` 265-266, reached rather than 261"
  - claim: "It closes on the first recovery, recording its depth in basis points and its length in days"
    source: "`praxis/metrics/limen_snapshot.py` 268-272, reached rather than 261 or 266"
  - claim: "Where nothing is evaluated, no episode is counted"
    source: "`praxis/metrics/limen_snapshot.py` 245-246"
---
# How a fall from a peak is recorded

One walk over the evaluated bars turns an equity curve into a list of falls, and a single test with three arms decides what each bar does to the list.

## The peak

A running peak is kept that only rises. Each bar's fall is that bar's equity against the peak, so a bar above every bar before it has no fall at all.

Where nothing is evaluated the walk has nothing to cover and no episode is counted.

## The three arms

A bar below the peak with no episode open opens one, noting the moment and taking that fall as the trough so far.

A bar below the peak with an episode already open deepens it where the fall is worse, and leaves it where the fall is shallower.

A bar back at the peak with an episode open closes it: the trough goes down as a depth in basis points, and the time since the opening moment goes down as a length in days.

A bar back at the peak with nothing open does none of the three.

## Related

- [The falls that never ended](the-falls-that-never-ended.md)
- [What counts as one trade](what-counts-as-one-trade.md)
