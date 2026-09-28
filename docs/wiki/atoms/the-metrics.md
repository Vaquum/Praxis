---
row: P3-10
baseline: 49aa659
created: 2026-09-28 11:30 UTC
modified: 2026-09-28 18:06 UTC
evidence:
  - claim: "A replay's figures come from the record and from the scenario's own bars"
    source: "`build_replay_report.py` 53-57 and 77-83"
  - claim: "A paper run is given its starting money separately"
    source: "`launcher.py` 3366-3368"
  - claim: "Distribution returns are scaled to hundredths of one percent"
    source: "`snapshot_result.py` 76-79 with the unit at `metric_conventions.py` 13"
  - claim: "Drawdown lengths are turned into days"
    source: "`snapshot_metrics.py` 162-165 with the unit at `metric_conventions.py` 15"
  - claim: "Four figures over closed trades are rounded to a fixed step"
    source: "`ledger_metrics.py` 67-71 with the step at 20"
  - claim: "Those four come back as zeroes where no trade closed"
    source: "`ledger_metrics.py` 52-59"
  - claim: "An undefined figure is kept in the report as an empty value"
    source: "`metrics_serialization.py` 27-45, which names them all regardless"
  - claim: "Most distribution figures come back as three points"
    source: "`percentiles.py` 62-66, assembled at `snapshot_result.py` 93-102"
  - claim: "One comes back as a single number"
    source: "`snapshot_result.py` 103"
  - claim: "With no real values among the inputs, the three are empty rather than zero"
    source: "`percentiles.py` 59-60"
---
# The metrics

The **metrics** are the figures a [replay](replay.md) or [paper run](the-paper-report.md) is summed up by, worked out after the fact. A paper run's come from the recorded fills and marks together with the starting money; a replay's come from [the record](the-event-spine.md), the starting money, and the scenario's own bars and predictions.

Two kinds are kept apart. Figures over closed trades come from the trades. Figures over a distribution — how returns were spread, how deep the drawdowns went — come from a step-by-step series instead.

## The units

Distribution returns are scaled to hundredths of one percent, and the length of a drawdown is turned into days.

The rest are in whatever suits them — money, counts, percentages, plain ratios with no unit at all, and amounts of coin.

## Where a figure is missing

Four figures over closed trades are rounded to a fixed step, and those same four come back as zeroes where no trade closed at all.

Elsewhere an undefined figure is kept but left empty. A win rate with no trades behind it is still named in the report, holding nothing rather than nought.

## Three points, not one

Most distribution figures come back as three points — a low, a middle and a high — so the spread is visible rather than averaged away. One is an exception and comes back as a single number.

Where no real values remain among the inputs, the three are empty rather than zero.

## Related

- [The paper report](the-paper-report.md)
- [Replay](replay.md)
