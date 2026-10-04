---
row: P4-19
baseline: 49aa659
created: 2026-10-03 21:21 UTC
modified: 2026-10-04 06:29 UTC
evidence:
  - claim: "A paper run's figures come from the same core a replay's do"
    source: "`paper_metrics.py` 80 into `build_replay_report.py` 99-145"
  - claim: "Where a replay's steps are its bars, a paper run's are its marks"
    source: "`paper_metrics.py` 80 against `build_replay_report.py` 53-57"
  - claim: "The marks are the sampler's own, sorted and stripped of repeated moments before they arrive"
    source: "`paper_report.py` 42-55, the samples made at `mark_sampler.py` 118-125"
  - claim: "This path hands over nothing for the bar-basis figures, so what comes back for them is empty"
    source: "`paper_metrics.py` 80 into `build_replay_report.py` 126, 140-142 and 363-380"
  - claim: "A gap at or below nought refuses the summary, whatever the marks"
    source: "`paper_metrics.py` 56-58"
  - claim: "A mark whose moment carries no zone refuses it"
    source: "`paper_metrics.py` 64-66"
  - claim: "So does one whose moment fails to advance on the one before, equal moments included"
    source: "`paper_metrics.py` 68-70"
  - claim: "So does a price at or below nought, one that is endless, and one that is not a number"
    source: "`paper_metrics.py` 72-74"
  - claim: "Every mark is checked before any figure is worked out, and a bad one raises"
    source: "`paper_metrics.py` 62-76 ahead of 78-80"
  - claim: "The gap is what the risk-adjusted figure is stretched by to reach a year"
    source: "`build_replay_report.py` 376 and 427-429"
  - claim: "The gap used there is the mean between marks, not the one handed in"
    source: "`paper_metrics.py` 99-101, called at 78"
  - claim: "It is the whole span over the number of gaps, rounded to whole seconds and held at one at least"
    source: "`paper_metrics.py` 99-101"
  - claim: "A sampler can miss a tick, leaving the marks unevenly spaced"
    source: "`mark_sampler.py` 113-125 and 131-141"
  - claim: "The gap handed in serves as the stretching gap only where there are fewer than two marks"
    source: "`paper_metrics.py` 96-97, the two set at 24"
---
# What a paper run's figures add

A [paper run](the-paper-report.md) is summed up by the same core a [replay](replay.md) is. What it adds is a different step series, a set of checks on that series, and one substitution.

## A different series

A replay's steps are its bars. A paper run's are the marks [its sampler took](the-mark-sampler.md) as the run went — moments paired with a price, sorted and stripped of repeated moments before they are summed up.

This path hands over nothing for the bar-basis figures, so what comes back for [those](the-two-bases-the-figures-come-from.md) is empty.

## What the marks must be

Every mark is checked before any figure is worked out, and a bad one raises rather than being skipped — so one bad mark among the many refuses the whole summary.

A moment carrying no zone refuses it. So does a moment failing to advance on the one before, equal moments included — though a repeat recorded by the sampler has already been stripped out by then. So does a price at or below nought, one that is endless, and one that is not a number.

A gap at or below nought refuses it whatever the marks are, being checked before them.

## The gap that is substituted

Stretching the risk-adjusted figure to a year needs to know how far apart the steps are. A replay uses the gap it was given. A paper run works out its own: the whole span over the number of gaps in it, rounded to whole seconds and held at one at least.

A sampler can miss a tick, which leaves the marks unevenly spaced. The gap handed in serves as the stretching gap only where there are fewer than two marks, leaving no span to measure.

## Related

- [The paper report](the-paper-report.md)
- [The mark sampler](the-mark-sampler.md)
