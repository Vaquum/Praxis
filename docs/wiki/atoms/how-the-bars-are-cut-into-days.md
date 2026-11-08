---
row: P12-02
baseline: 49aa659
created: 2026-11-10 09:30 UTC
modified: 2026-11-10 09:30 UTC
evidence:
  - claim: "The evaluated bars are grouped by the day their moment falls in"
    source: "`praxis/metrics/limen_snapshot.py` 220"
  - claim: "The days are reported in order"
    source: "`praxis/metrics/limen_snapshot.py` 225"
  - claim: "Where no bar is evaluated the grouping stays empty and no day is reported"
    source: "`praxis/metrics/limen_snapshot.py` 217-218, leaving 225 nothing to walk"
  - claim: "A day's return is its bars' returns multiplied together, given in basis points"
    source: "`praxis/metrics/limen_snapshot.py` 227 into 229"
  - claim: "A day's return for each unit of exposure is that return over the share of its bars holding a position"
    source: "`praxis/metrics/limen_snapshot.py` 228 into 230-232"
  - claim: "That second figure is given as nothing at all where no bar of the day held a position"
    source: "`praxis/metrics/limen_snapshot.py` 231, which answers nothing where the share is nought"
---
# How the bars are cut into days

The same bars a replay counts as trades are also cut a second way, by the calendar day each falls in.

## The grouping

Each evaluated bar is filed under the day of its moment, and the rest are passed over. Where the walk finds none to file, the grouping stays empty and no day is reported.

The days are then walked in order, so the figures come out oldest first.

## The two figures each day carries

Its return is its bars' returns multiplied together, given in basis points — compounded within the day as a trade's is within itself.

Its return for each unit of exposure is that return divided by the share of its bars that held a position. A day holding a position in half its bars and returning a hundred points reports two hundred per unit.

## The day that held nothing

Where no bar of the day held a position, the second figure is given as nothing at all rather than as nought.

So a reader averaging the days must decide what to do with the gap. Treating it as nought would pull the average down with days that were never exposed to anything.

## Related

- [What counts as one trade](what-counts-as-one-trade.md)
- [The falls that never ended](the-falls-that-never-ended.md)
