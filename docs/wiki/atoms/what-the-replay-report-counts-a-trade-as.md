---
row: P86-01
baseline: 49aa659
created: 2026-11-09 05:25 UTC
modified: 2026-11-09 05:25 UTC
evidence:
  - claim: "Every trade handed to the ledger figures is recorded as a long one, with nothing consulted to decide it"
    source: "`build_replay_report.py` 204-206, the mark set at 205"
  - claim: "Each trade's volume is recorded as its entry price times its quantity"
    source: "`build_replay_report.py` 205"
  - claim: "A win is a trade whose net stands above nought and a loss one whose net stands below it"
    source: "`build_replay_report.py` 357, and 358"
  - claim: "A trade whose net lands exactly on nought falls into neither group"
    source: "`build_replay_report.py` 357, and 358, each comparing against nought strictly"
  - claim: "The two totals are summed from those groups and the net from every trade, so the net can differ from their sum"
    source: "`build_replay_report.py` 359, and 360, against 361"
  - claim: "A bar counts as one spent holding something only where the position stands above nought"
    source: "`build_replay_report.py` 337 into 338"
---
# What the replay report counts a trade as

The report turns a replay's trades into figures, and two of its choices decide what those figures can mean.

## Long, whatever happened

Every trade handed to the ledger figures is recorded as a long one, with nothing consulted to decide it. Each trade's volume is recorded as its entry price times its quantity.

A bar likewise counts as one spent holding something only where the position stands above nought. So both the per-trade mark and the time-in-market count read the replay as long-only.

## Win, loss, and neither

A win is a trade whose net stands above nought; a loss one whose net stands below it. Both comparisons are strict.

So a trade whose net lands exactly on nought falls into neither group. It is counted in neither the wins nor the losses, while still counting in the trade total.

## Why the net is its own sum

The two totals are summed from those groups, and the net from every trade. Because a trade at exactly nought belongs to no group, the net is summed over a different set from the two it sits beside.

The three agree whenever no trade lands on nought, which is almost always — and the one case where they part is the one a reader would never think to check.

## Related

- [How the replay report places a fill in a bar](how-the-replay-report-places-a-fill-in-a-bar.md)
