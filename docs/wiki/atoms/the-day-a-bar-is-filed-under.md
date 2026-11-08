---
row: P15-03
baseline: 49aa659
created: 2026-11-10 14:30 UTC
modified: 2026-11-10 14:30 UTC
evidence:
  - claim: "A bar is filed under the calendar day of its own moment, as that moment was written"
    source: "`praxis/metrics/limen_snapshot.py` 220, the only earlier test of the moments at 108-114"
  - claim: "Every moment must carry a zone, and that is all that is asked of it"
    source: "`praxis/metrics/limen_snapshot.py` 108-114"
  - claim: "A replay's clock keeps whatever zone the moment it is started from carries"
    source: "`praxis/replay/replay_clock.py` 33, the one refusal before it at 29-31"
---
# The day a bar is filed under

The day [a bar is grouped into](how-the-bars-are-cut-into-days.md) is the calendar day of its own moment, as that moment was written.

## What is asked of a moment

That it carry a zone. Nothing asks which zone, and nothing brings the moments into a common one before they are filed.

## What follows from that

The same instant written in two zones is filed under two different days. Ten at night in universal time is seven the next morning nine hours east: one instant, two calendar days, two groups.

So which bars share a day, and therefore every figure a day carries, follows the zone the moments arrived in rather than a zone the figures fix.

Nothing upstream fixes one either: [a replay's clock](replay.md) keeps whatever zone the moment it was started from carries, refusing only a moment with no zone at all.

## Related

- [How the bars are cut into days](how-the-bars-are-cut-into-days.md)
- [What the series are read as](what-the-series-are-read-as.md)
