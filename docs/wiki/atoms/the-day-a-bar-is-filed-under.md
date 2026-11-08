---
row: P15-03
baseline: 49aa659
created: 2026-11-10 14:30 UTC
modified: 2026-11-10 20:00 UTC
evidence:
  - claim: "A bar is filed under the calendar day of the moment handed in for it"
    source: "`praxis/metrics/limen_snapshot.py` 220"
  - claim: "That moment must be a moment carrying a zone whose offset is something, and nothing more is asked of it"
    source: "`praxis/metrics/limen_snapshot.py` 108-114"
  - claim: "The one caller hands in universal-time moments, built from each bar's own stamp"
    source: "`praxis/replay/build_replay_report.py` 82 into 94-96, the only call at 77"
  - claim: "A bar's own stamp is not its closing moment, which for a series whose stamps open its bars is that stamp plus the interval"
    source: "`praxis/replay/load_replay_bars.py` 74 and 82, the stamp kept at 91"
  - claim: "The window the bars were chosen by was filtered on that closing moment"
    source: "`praxis/replay/load_replay_bars.py` 84-85"
---
# The day a bar is filed under

The day [a bar is grouped into](how-the-bars-are-cut-into-days.md) is the calendar day of the moment handed in for that bar.

## Which moment that is

The bar's own stamp, in universal time. The one thing that works these figures out builds each moment from the bar's stamp and hands it over in universal time, so the days are universal-time days and no zone of the caller's shows through.

The grouping itself asks only that each moment be a moment carrying a zone whose offset is something. Any zone would do; it is the caller that settles on one.

## Why the stamp and not the close

For a series whose stamps open its bars, a bar's closing moment is its stamp plus the interval handed in. The grouping is given the stamp.

So a bar that opens before midnight and closes after it is filed under the earlier day — while [the window those bars were chosen by](where-a-replays-bars-come-from.md) was filtered on the closing moment, which falls on the later one.

A run asked for over a window therefore files its last bars under the day their closes have already left.

## Related

- [How the bars are cut into days](how-the-bars-are-cut-into-days.md)
- [Where a replay's bars come from](where-a-replays-bars-come-from.md)
- [What the series are read as](what-the-series-are-read-as.md)
