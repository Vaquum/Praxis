---
row: P50-01
baseline: 49aa659
created: 2026-11-08 17:35 UTC
modified: 2026-11-08 17:35 UTC
evidence:
  - claim: "A trade is a run of consecutive steps holding a position"
    source: "`snapshot_metrics.py` 73-76"
  - claim: "The first step holding none closes the run and records it"
    source: "`snapshot_metrics.py` 78-83"
  - claim: "A run still open when the steps end is recorded as it stands"
    source: "`snapshot_metrics.py` 85-87"
  - claim: "Each step holding a position multiplies its return into the run, net and gross side by side"
    source: "`snapshot_metrics.py` 74-75"
  - claim: "What is recorded is the gain or loss over the run rather than the sum of its steps"
    source: "`snapshot_metrics.py` 79-80, or 86-87"
  - claim: "The edge for each signal is the gross return of every step holding a position, counted one by one"
    source: "`snapshot_metrics.py` 47"
---
# What a trade is on the portfolio basis

On [the whole-account basis](the-two-bases-the-figures-come-from.md), one trade is a run of consecutive steps that held a position.

## Where a run begins and ends

It begins at the first step holding a position and runs while they keep holding one. The first step holding none closes it, and the run is recorded then.

A run still open when the steps run out is recorded as it stands, so a position held to the end of a run counts as a trade rather than being dropped.

## What a run is worth

The step returns are compounded rather than added: each step's return applies to what the run has already made. Net and gross are kept side by side, and what is reported is the gain or loss over the whole run — two steps of a tenth give just over a fifth.

## How this differs from the bar basis

[The bar basis](what-counts-as-one-trade.md) numbers its bars by a running count of entry marks and treats each number occurring on a held bar as a trade. Here there are no marks: a run is a stretch of the holding flag, and two positions separated by a single step out of position are two trades on both bases for different reasons.

The edge for each signal is counted differently again — one figure per step holding a position, rather than one per trade.

## Related

- [The two bases the figures come from](the-two-bases-the-figures-come-from.md)
- [What counts as one trade](what-counts-as-one-trade.md)
- [How the portfolio windows are cut](how-the-portfolio-windows-are-cut.md)
