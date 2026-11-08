---
row: P10-03
baseline: 49aa659
created: 2026-11-10 05:30 UTC
modified: 2026-11-10 05:30 UTC
evidence:
  - claim: "Where no lot step is known the last slice is the total less the others, so the slices come to the total exactly"
    source: "`praxis/core/plan_even_slices.py` 56-58"
  - claim: "Where a step is known the last slice is floored to it as the others are"
    source: "`praxis/core/plan_even_slices.py` 69 into 78"
  - claim: "A last slice that floors to nought or below is refused"
    source: "`praxis/core/plan_even_slices.py` 71-76"
---
# The quantity a lot step leaves behind

An even split comes to the total exactly where no lot step is known, and can come to less where one is.

## Without a step

Every slice but the last is the total divided by the count. The last is the total less all of them, so whatever the division left over goes into it and the slices come to the total exactly.

## With a step

Each slice is floored to the step. The last is floored too: it is the remainder after the others, rounded down to the step rather than taken whole.

So what is left after that flooring is sent to nobody. Ten split three ways with a step of three gives three, three and three — nine sent of ten asked for, with one left behind.

A last slice that floors to nought or below is refused outright, so the shortfall is bounded by one step: the split either loses less than a step or does not happen.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [When a weight curve plans nothing](when-a-weight-curve-plans-nothing.md)
