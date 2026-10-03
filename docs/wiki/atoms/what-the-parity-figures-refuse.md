---
row: P4-41
baseline: 49aa659
created: 2026-10-03 21:05 UTC
modified: 2026-10-03 21:19 UTC
evidence:
  - claim: "A run of no bars is refused"
    source: "`limen_snapshot.py` 102-103"
  - claim: "Columns of unequal length are refused"
    source: "`limen_snapshot.py` 105-106"
  - claim: "A moment that is not a moment, or carries no zone, is refused"
    source: "`limen_snapshot.py` 108-114"
  - claim: "A lag below nought is refused"
    source: "`limen_snapshot.py` 116-117"
  - claim: "A prediction that is neither nought nor one is refused"
    source: "`limen_snapshot.py` 119-120"
  - claim: "A price change that does not equal the close less the opening is refused, within a tolerance"
    source: "`limen_snapshot.py` 122-131, the tolerance at 32-33"
  - claim: "A bar counts only where all three of its figures are there and its opening differs from nought"
    source: "`limen_snapshot.py` 122 and 133, applied at 139-140"
  - claim: "A bar left out breaks the run of held bars across it, so one before it can read as an exit"
    source: "`limen_snapshot.py` 140-144"
  - claim: "The prediction is shifted forward by the lag, one bar unless another is given"
    source: "`limen_snapshot.py` 35-48, called at 138, the one at 31"
  - claim: "The first bars, as many as the lag, are left out of the reckoning"
    source: "`limen_snapshot.py` 135-136"
  - claim: "A bar entered on returns the change across it over its opening"
    source: "`limen_snapshot.py` 147 and 150"
  - claim: "A bar held returns its close divided by the close before it, less one"
    source: "`limen_snapshot.py` 148 and 150"
  - claim: "A gross return that comes out undefined is taken as nothing"
    source: "`limen_snapshot.py` 151"
  - claim: "A fee and a slip are charged at entry and at exit, five hundredths of a percent each unless given"
    source: "`limen_snapshot.py` 153-157, the two defaults at 29-30"
  - claim: "Entry divides by one plus the slip where exit multiplies by one less it"
    source: "`limen_snapshot.py` 156-157"
---
# What the parity figures refuse

The [bar basis](the-two-bases-the-figures-come-from.md) checks what it is given before working anything out, and refuses six things outright.

## The six refusals

A run of no bars at all. Columns of unequal length. A moment that is not a moment, or carries no zone. A lag below nought. A prediction that is neither nought nor one.

And a price change that does not equal the closing price less the opening one, within a tolerance.

## What is left out instead

Past those checks, a bar counts only where all three of its figures are there and its opening differs from nought. One failing that is left out rather than refused.

Left out, though, is not the same as absent. The run of held bars is broken across it, so the bar before it can read as an exit and the bar after as a fresh entry.

The first bars are left out too, as many of them as the lag. The prediction is shifted forward by that lag — one bar unless another is given — so the earliest bars have nothing shifted into them.

## How a return is reckoned

A bar entered on returns the change across it, over its opening price. A bar merely held returns its close divided by the close before it, less one. A gross return coming out undefined is taken as nothing.

## What costs are assumed

A fee and a slip, five hundredths of a percent each unless given otherwise, charged at entry and at exit.

The slip is applied differently at each end: entry divides by one plus it, where exit multiplies by one less it.

## Related

- [The two bases the figures come from](the-two-bases-the-figures-come-from.md)
- [The metrics](the-metrics.md)
