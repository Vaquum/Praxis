---
row: P46-02
baseline: 49aa659
created: 2026-11-08 17:18 UTC
modified: 2026-11-08 17:18 UTC
evidence:
  - claim: "An interval at or below nought answers nothing"
    source: "`praxis/replay/build_replay_report.py` 409-410"
  - claim: "Fewer than two returns answers nothing"
    source: "`praxis/replay/build_replay_report.py` 418-419 with the floor at 28"
  - claim: "A variance of nought across the returns answers nothing"
    source: "`praxis/replay/build_replay_report.py` 424-425"
  - claim: "A step whose previous value stands at or below nought forms no return, which can leave fewer than two where the series has many steps"
    source: "`praxis/replay/build_replay_report.py` 412-416 into 418-419"
  - claim: "Otherwise it is the mean return divided by the square root of the variance, multiplied by the square root of how many intervals fit a year"
    source: "`praxis/replay/build_replay_report.py` 421-422 into 427-429"
  - claim: "The variance is divided by one fewer than the count of returns"
    source: "`praxis/replay/build_replay_report.py` 422"
---
# When the risk-adjusted figure is absent

The risk-adjusted return in [a replay's report](what-a-replay-reports.md) is left empty in three cases, and a reader cannot tell them apart from the report.

## The three

An interval at or below nought: answered before anything is worked out.

Fewer than two returns to work from.

A variance of nought across those returns — every return exactly the mean, which includes a run whose equity never moved.

## The step that forms no return

A step whose previous value stands at or below nought forms no return at all. The step is passed over and the walk goes on.

That alone does not empty the figure: a long series with one such gap still has returns either side of it. What it can do is leave fewer than two returns where the series has many steps, and then the second case above answers nothing.

## The figure itself

The mean of the step-to-step returns, divided by the square root of their variance, multiplied by the square root of how many intervals of that length fit a year.

The variance is divided by one fewer than the count of returns, which is why two are the fewest that can give an answer at all.

## Related

- [What a replay reports](what-a-replay-reports.md)
- [The worst fall a replay reports](the-worst-fall-a-replay-reports.md)
- [The metrics](the-metrics.md)
