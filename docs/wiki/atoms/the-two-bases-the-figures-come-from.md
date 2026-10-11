---
row: P4-18
baseline: 49aa659
created: 2026-10-03 21:05 UTC
modified: 2026-10-11 19:33 UTC
evidence:
  - claim: "Both bases pass their series through the same assembler, which publishes eight names"
    source: "`snapshot_result.py` 27-36 and 82-105, called at `snapshot_metrics.py` 52-61 and `limen_snapshot.py` 173-181"
  - claim: "Six distributions come back as a low, a middle and a high, each rounded, or as three nothings where no real figure is left to read"
    source: "`snapshot_result.py` 82-97 into `percentiles.py` 57-66"
  - claim: "A seventh does too, rounded to three places, being a length in days"
    source: "`snapshot_result.py` 99-102, the three at 23, the days worked at `snapshot_metrics.py` 163-165 against `metric_conventions.py` 15"
  - claim: "The eighth is a single figure: the average of the finite window returns at or below their lowest twentieth, rounded to one place"
    source: "`snapshot_result.py` 116-123, the twentieth and the place at 24-25, the filtering at `percentiles.py` 34-36"
  - claim: "Where none of them is finite, no figure is given"
    source: "`snapshot_result.py` 118-119"
  - claim: "Two of the six are worked out in the assembler itself, from the trades handed in"
    source: "`snapshot_result.py` 76-80"
  - claim: "One basis reduces a run to a series of steps, one per bar or one per mark"
    source: "`build_replay_report.py` 169-199, and `paper_metrics.py` 78-80"
  - claim: "A step carries a moment, whether a position was held over it, and a return before and after costs"
    source: "`metric_step.py` 37-40"
  - claim: "The two returns are taken from separate running totals, one charged the fees and one not"
    source: "`build_replay_report.py` 176-183 and 192-197"
  - claim: "A step refuses a moment with no zone"
    source: "`metric_step.py` 44-45"
  - claim: "It refuses a return that is not finite"
    source: "`metric_step.py` 47-48"
  - claim: "The other basis works over arrays of bars instead, and is checked against stored expected figures"
    source: "`limen_snapshot.py` 100-181, compared at `test_limen_snapshot.py` 42-45"
---
# The two bases the figures come from

[The summary figures](the-metrics.md) over a run's distribution are worked out two ways, from two different starting points. Both pass their series through the same assembler, so the eight names they publish are the same eight.

## What the assembler publishes

Six distributions each come back as a low, a middle and a high, each rounded — or as three nothings, where no real figure is left to read. A seventh comes back the same way, rounded to three places, being a length in days rather than a return.

The eighth is a single figure: the average of the finite window returns at or below their lowest twentieth, rounded to one place. Where none of those returns is finite, no figure is given at all.

Two of the six are worked out in the assembler itself, from the per-trade returns handed in — one scaling the net return, the other taking the difference between gross and net as the drag of costs.

## The step basis

One basis reduces a run to a series of **steps**: one per bar in a [replay](replay.md), one per mark in a [paper run](the-paper-report.md).

A step carries a moment, whether a position was held over it, and the return across it before and after costs. Those two come from separate running totals, one charged the fees and one not — so the two can differ on later steps even where nothing was filled.

A step refuses a moment with no zone, and refuses a return that is not finite.

## The bar basis

The other works over arrays of bars instead — the predictions and the prices — and is checked against stored expected figures.

[What it refuses](what-the-parity-figures-refuse.md) of what it is given is its own subject.

## Related

- [The metrics](the-metrics.md)
- [What the parity figures refuse](what-the-parity-figures-refuse.md)
