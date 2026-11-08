---
row: P46-01
baseline: 49aa659
created: 2026-11-12 03:30 UTC
modified: 2026-11-12 03:30 UTC
evidence:
  - claim: "An empty series answers nought"
    source: "`praxis/replay/build_replay_report.py` 391-392"
  - claim: "The first peak is the series' own first value"
    source: "`praxis/replay/build_replay_report.py` 394"
  - claim: "The peak rises to any value above it, and the worst fall is the largest drop from the peak as a share of that peak"
    source: "`praxis/replay/build_replay_report.py` 397-402"
  - claim: "A peak at or below nought is passed over rather than divided by"
    source: "`praxis/replay/build_replay_report.py` 401"
  - claim: "The answer is given as a percentage"
    source: "`praxis/replay/build_replay_report.py` 404"
---
# The worst fall a replay reports

The worst fall in [a replay's report](what-a-replay-reports.md) is the largest drop from a running peak, measured as a share of that peak and given as a percentage.

## Where the peak starts

At the series' own first value.

So a run that only ever falls reports the fall from where it began, and a run whose equity starts below the stake it was given reports nothing of that — the stake is not the peak here.

That is the opposite of [where the training side's peak begins](where-the-peak-begins.md), which is seeded at the stake and so counts a first bar below it as a fall already.

## What the walk keeps

For each value: the peak rises to it where it is higher, and the worst is kept at whichever is larger — what was already worst, or this value's drop from the peak.

A peak at or below nought is passed over rather than divided by, so a series that starts at nought reports no fall until it has risen above it.

## What an empty series answers

Nought. A replay with no steps therefore reports no fall rather than nothing at all, which a reader averaging across runs would want to know.

## Related

- [What a replay reports](what-a-replay-reports.md)
- [Where the peak begins](where-the-peak-begins.md)
- [When the risk-adjusted figure is absent](when-the-risk-adjusted-figure-is-absent.md)
