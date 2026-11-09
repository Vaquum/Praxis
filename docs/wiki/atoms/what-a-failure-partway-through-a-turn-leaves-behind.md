---
row: N71-02
baseline: 49aa659
created: 2026-11-08 21:14 UTC
modified: 2026-11-08 21:14 UTC
evidence:
  - claim: "A turn writes the signal to the log, hands it to the strategy, records the moment, and submits the answer, in that order"
    source: "`nexus/strategy/predict_loop.py` 334, then 337-342, then 344, then 346-347"
  - claim: "The answer is submitted only where a road for submitting was given and the answer holds something"
    source: "`nexus/strategy/predict_loop.py` 346"
  - claim: "The moment is recorded after the handing over, so a handing over that raises leaves it unrecorded"
    source: "`nexus/strategy/predict_loop.py` 344, standing after 337-342"
  - claim: "A later turn then resolves the same row again, where the manifest is still fresh and that row is still the newest usable one"
    source: "`nexus/strategy/predict_loop.py` 396 reading what 344 did not write, past 363-371 and 474-479"
  - claim: "The moment is recorded before the submitting, so a submitting that raises leaves it recorded and no later turn resolves that row"
    source: "`nexus/strategy/predict_loop.py` 344, standing before 346-347, read at 396"
  - claim: "A failure of either is logged where the turn was the loop's own, and handed to the caller where the turn was asked for by hand"
    source: "`nexus/strategy/predict_loop.py` 307-316, against 282"
  - claim: "The next due moment is set either way, and the cohort remembered for that pair was written before any of this"
    source: "`nexus/strategy/predict_loop.py` 317-322, and 554 reached at 407"
---
# What a failure partway through a turn leaves behind

A turn of [the prediction loop](what-the-prediction-loops-stop-leaves-running.md) does four things in order, and the record of where it got to sits between two of them.

## The order

The signal is written to the log. It is handed to the strategy. The moment is recorded. The answer is submitted — where a road for submitting was given and the answer holds something.

## A handing over that fails

The moment is not recorded. A later turn resolves the same row again, so long as the manifest is still fresh and that row is still the newest usable one.

So a strategy failing on a signal is handed it again, turn after turn, until one of those two things changes.

## A submitting that fails

The moment is recorded. No later turn resolves that row, and the answers go nowhere.

## What is left either way

The signal is in the log, written before the handing over. The failure is logged where the turn was the loop's own, and handed to the caller where the turn was asked for by hand. The next due moment is set, and the cohort for that pair was written down earlier still.

So neither failure is silent, and neither leaves the turn looking untaken. What they differ in is whether the row comes round again.

## Related

- [What the prediction loop's stop leaves running](what-the-prediction-loops-stop-leaves-running.md)
- [Which prediction row is used](which-prediction-row-is-used.md)
