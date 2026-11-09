---
row: P50-02
baseline: 49aa659
created: 2026-11-08 17:35 UTC
modified: 2026-11-08 17:35 UTC
evidence:
  - claim: "The windows are cut by truncating each step's moment to a named span"
    source: "`snapshot_metrics.py` 115-117"
  - claim: "The span is whatever the caller names, and the one caller names a day"
    source: "`snapshot_metrics.py` 49 into 116, named at `praxis/replay/build_replay_report.py` 137 with the span at 27"
  - claim: "A window's return is its steps' returns compounded, reported as the gain or loss over the window"
    source: "`snapshot_metrics.py` 119"
  - claim: "Its exposure is the share of its steps holding a position"
    source: "`snapshot_metrics.py` 120"
  - claim: "The return for each unit of exposure is that return over the share, and nothing at all where the share is nought"
    source: "`snapshot_metrics.py` 124-129"
  - claim: "Where there are no steps, no window is reported"
    source: "`snapshot_metrics.py` 105-106"
---
# How the portfolio windows are cut

On [the whole-account basis](the-two-bases-the-figures-come-from.md) the steps are grouped into windows by truncating each step's moment to a span, and the span is named by whoever asks.

## The span

Whatever the caller names. The one thing that asks for these figures names a day, so the same steps could be reported by the hour or the week without the figures being worked out differently — only cut differently.

[The bar basis](how-the-bars-are-cut-into-days.md) has no such choice: it files each bar under the calendar day of its own moment, and a caller cannot ask for another span.

## The two figures each window carries

Its return: the steps' returns compounded, reported as the gain or loss over the window rather than as the sum of its steps.

Its return for each unit of exposure: that return divided by the share of its steps that held a position. Where no step in the window held one, the share is nought and the figure is nothing at all rather than nought.

## Where there are no steps

No window is reported, and both lists come back empty.

## Related

- [The two bases the figures come from](the-two-bases-the-figures-come-from.md)
- [How the bars are cut into days](how-the-bars-are-cut-into-days.md)
- [What a trade is on the portfolio basis](what-a-trade-is-on-the-portfolio-basis.md)
