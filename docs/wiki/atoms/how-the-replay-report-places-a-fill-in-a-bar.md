---
row: P86-02
baseline: 49aa659
created: 2026-11-09 05:25 UTC
modified: 2026-11-09 05:25 UTC
evidence:
  - claim: "A fill's bar is found by searching the settle moments for its own, and taking the one before"
    source: "`build_replay_report.py` 212"
  - claim: "That answer is held at nought at the least, so a fill earlier than the first settle lands in the first bar"
    source: "`build_replay_report.py` 212, the floor applied to the same expression"
  - claim: "Both walks pull the settle moments out of the timeline and group every fill by the bar it lands in"
    source: "`build_replay_report.py` 156 into 157-160, or 312 into 313-316"
  - claim: "Both start their running cash at the capital pool and their position at nought"
    source: "`build_replay_report.py` 162-167, or 318-321"
  - claim: "Each bar's worth is the cash standing plus the position priced at that bar's close"
    source: "`build_replay_report.py` 335"
  - claim: "The walk answers the worth of every bar together with how many were spent holding something"
    source: "`build_replay_report.py` 340"
  - claim: "A snapshot asked for over no bars at all answers with nothing"
    source: "`build_replay_report.py` 74 into 75"
  - claim: "The fall from a peak is walked from the first bar's worth, with the worst standing at nought until something is worse"
    source: "`build_replay_report.py` 394, and 395"
---
# How the replay report places a fill in a bar

Every fill in a replay is put in one bar, and which bar is decided by a search rather than by anything the fill carries.

## The search

The settle moments are searched for the fill's own, and the bar before is taken. That answer is held at nought at the least.

So a fill whose moment is earlier than the first settle lands in the first bar rather than being dropped. Nothing is lost for being early, and nothing says it was moved.

## The two walks

Both walks pull the settle moments out of the timeline and group every fill by the bar it lands in. Both start their running cash at the capital pool and their position at nought.

## What a bar is worth

The cash standing plus the position priced at that bar's close. The walk answers the worth of every bar together with how many were spent holding something.

## The two empty answers

A snapshot asked for over no bars at all answers with nothing. The fall from a peak is walked from the first bar's worth, with the worst standing at nought until something is worse — so a replay that only ever rose reports its worst fall as nought.

## Related

- [What the replay report counts a trade as](what-the-replay-report-counts-a-trade-as.md)
