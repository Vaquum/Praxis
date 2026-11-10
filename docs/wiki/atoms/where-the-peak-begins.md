---
row: P15-02
baseline: 49aa659
created: 2026-11-08 14:34 UTC
modified: 2026-11-08 14:34 UTC
evidence:
  - claim: "The peak each fall is measured against starts at one"
    source: "`praxis/metrics/limen_snapshot.py` 250"
  - claim: "The peak then rises to the equity of any bar above it, and each bar's fall is its equity against the peak"
    source: "`praxis/metrics/limen_snapshot.py` 256-257"
  - claim: "So a curve whose first evaluated bar sits below one is already in a fall at that bar"
    source: "`praxis/metrics/limen_snapshot.py` 250 into 256-257, opening an episode at 260-263"
  - claim: "The opening moment is set before the walk, with no episode open, and every episode writes its own as it opens"
    source: "`praxis/metrics/limen_snapshot.py` 251-253 against 262"
---
# Where the peak begins

The peak that [a fall](how-a-fall-from-a-peak-is-recorded.md) is measured against begins at one, before any bar is looked at.

## What that makes the first bar

One is where the curve itself begins, since the curve is the bars' returns multiplied out from a starting stake of one. A bar at one is level with the peak and has no fall.

A first evaluated bar below one therefore has a fall already, and opens an episode there. A curve starting at nine tenths and climbing back above one records that as a fall of a thousand basis points, measured from the stake rather than from the curve's own first value.

A curve whose every bar is above one, rising throughout, records no fall at all.

## The moment set and never read

Two things are set beside the peak before the walk: that no episode is open, and an opening moment, taken from the first evaluated bar.

The second cannot be reached. An episode's length is measured from the moment written as that episode opened, and no episode can be open before the walk begins, so the moment set here is overwritten before anything asks for it.

## Related

- [How a fall from a peak is recorded](how-a-fall-from-a-peak-is-recorded.md)
- [The falls that never ended](the-falls-that-never-ended.md)
- [What the series are read as](what-the-series-are-read-as.md)
