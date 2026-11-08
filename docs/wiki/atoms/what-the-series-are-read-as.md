---
row: P15-01
baseline: 49aa659
created: 2026-11-10 14:30 UTC
modified: 2026-11-10 14:30 UTC
evidence:
  - claim: "The four series a snapshot is worked out from are read as arrays of floating-point numbers before any of them is checked"
    source: "`praxis/metrics/limen_snapshot.py` 96-99, ahead of the checks from 102"
  - claim: "A true-or-false becomes one or nought, and text reading as a number becomes that number, so the test for a prediction being nought or one passes for either"
    source: "`praxis/metrics/limen_snapshot.py` 96 into 119-120"
  - claim: "A value that is no number at all becomes not-a-number, which that test refuses"
    source: "`praxis/metrics/limen_snapshot.py` 96 into 119-120"
  - claim: "The same value in any of the three price series marks that bar's price unknown instead"
    source: "`praxis/metrics/limen_snapshot.py` 97-99 into 122"
  - claim: "A bar whose price is unknown is left out of everything the figures are drawn from"
    source: "`praxis/metrics/limen_snapshot.py` 133 into 139-140"
---
# What the series are read as

The series [a replay's figures](what-a-replay-reports.md) are worked out from — the predictions, the opening and closing prices, and the change between them — are read as arrays of floating-point numbers before any of them is checked.

## What the reading accepts

Whatever can be read as a number is. A true-or-false becomes one or nought, and text reading as a number becomes that number.

So the test that a prediction is nought or one is satisfied by a true, by a false, and by either digit written as text. It is applied to what the reading produced, rather than to what the caller passed.

## What becomes of a value that is no number

It becomes not-a-number, and from there the two kinds of series part company.

As a prediction, it fails the test for nought or one and the whole call is refused: one missing prediction and no figures are produced at all.

As an opening price, a closing price or a change, it marks that one bar's price unknown. The bar is then left out of everything — no return, no day, no fall — and the figures come back as if those bars had not been handed in.

## Related

- [What counts as one trade](what-counts-as-one-trade.md)
- [Where the peak begins](where-the-peak-begins.md)
- [The day a bar is filed under](the-day-a-bar-is-filed-under.md)
