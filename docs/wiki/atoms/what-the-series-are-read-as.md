---
row: P15-01
baseline: 49aa659
created: 2026-11-08 14:34 UTC
modified: 2026-11-08 15:12 UTC
evidence:
  - claim: "The four series a snapshot is worked out from are read as arrays of floating-point numbers before any of them is checked"
    source: "`praxis/metrics/limen_snapshot.py` 96-99, ahead of the checks from 102"
  - claim: "A true-or-false becomes one or nought, and text reading as a number becomes that number, so the test for a prediction being nought or one passes for either"
    source: "`praxis/metrics/limen_snapshot.py` 96 into 119-120"
  - claim: "Text that reads as no number at all is turned back by the reading itself, before any check is made"
    source: "`praxis/metrics/limen_snapshot.py` 96-99, ahead of 102"
  - claim: "A value with no numeric form of its own becomes not-a-number, which the test for a prediction refuses"
    source: "`praxis/metrics/limen_snapshot.py` 96 into 119-120"
  - claim: "The same value in any of the three price series marks that bar's price unknown instead"
    source: "`praxis/metrics/limen_snapshot.py` 97-99 into 122"
  - claim: "A bar whose price is unknown holds nothing, so it carries no return, no day and no fall of its own"
    source: "`praxis/metrics/limen_snapshot.py` 133 into 139-140"
  - claim: "It keeps its place among the bars, so a held run it falls inside is counted as two trades, each with an opening and a closing of its own"
    source: "`praxis/metrics/limen_snapshot.py` 142 and 144 over the held bars at 140, charged at 156-157"
---
# What the series are read as

The series [a replay's figures](what-a-replay-reports.md) are worked out from — the predictions, the opening and closing prices, and the change between them — are read as arrays of floating-point numbers before any of them is checked.

## What the reading accepts

Whatever can be read as a number is. A true-or-false becomes one or nought, and text reading as a number becomes that number.

So the test that a prediction is nought or one is satisfied by a true, by a false, and by either digit written as text. It is applied to what the reading produced, rather than to what the caller passed.

Text that reads as no number at all does not get that far: the reading itself turns it back, before the first check runs.

## What becomes of a value with no numeric form

Nothing at all, handed in where a number was expected, becomes not-a-number. From there the two kinds of series part company.

As a prediction, it fails the test for nought or one and the whole call is refused: one such value and no figures are produced.

As an opening price, a closing price or a change, it marks that one bar's price unknown. Nothing is held there, so the bar carries no return, no day and no fall of its own.

## What an unknown price still does

The bar keeps its place in the series. A held run that it falls inside is therefore two runs, counted as two trades, each with an opening and a closing of its own — and each charged for both.

So one unknown price in the middle of a position does not shorten that position by a bar. It splits it, and the figures show an extra round of costs.

## Related

- [What counts as one trade](what-counts-as-one-trade.md)
- [Where the peak begins](where-the-peak-begins.md)
- [The day a bar is filed under](the-day-a-bar-is-filed-under.md)
