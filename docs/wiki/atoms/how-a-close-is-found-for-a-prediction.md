---
row: N71-03
baseline: 49aa659
created: 2026-11-08 21:14 UTC
modified: 2026-11-08 21:14 UTC
evidence:
  - claim: "The frame of prices is read from a fixed name under a folder named for the series, not from any path the manifest gives"
    source: "`nexus/strategy/predict_loop.py` 493"
  - claim: "A path leading to no file warns, naming the series and the path, and the turn ends"
    source: "`nexus/strategy/predict_loop.py` 494-499"
  - claim: "The frame is then read and filtered on the moment being exactly equal, with no window and no nearest match"
    source: "`nexus/strategy/predict_loop.py` 501, then 502"
  - claim: "That reading and filtering stand before the guard that reports a miss, so a frame without the columns named raises rather than warning"
    source: "`nexus/strategy/predict_loop.py` 501-502 ahead of 504"
  - claim: "A miss warns with the prediction's moment and the lowest and highest moments the frame holds"
    source: "`nexus/strategy/predict_loop.py` 504-515"
  - claim: "That range is read only where the column is there and the frame holds something, and reported as nothing otherwise"
    source: "`nexus/strategy/predict_loop.py` 505"
  - claim: "A match gives the first matching row's closing price as a plain number"
    source: "`nexus/strategy/predict_loop.py` 517"
---
# How a close is found for a prediction

A prediction says what to do and not at what price, so a turn of [the loop](which-prediction-row-is-used.md) looks the price up and will not go on without it.

## Where it looks

A fixed name, under a folder named for the series. Not a path the manifest gives — the manifest names where predictions live, and the prices are found by convention instead.

A path leading to no file warns, naming the series and the path, and the turn ends.

## How the match is made

The frame is read and filtered on the moment being exactly equal. There is no window, no nearest match, and no tolerance.

So the two producers must agree on what a moment means. A prediction whose moment is shifted from the bar it was made for matches whatever row carries the shifted moment, or nothing.

## What a miss reports

The prediction's moment, together with the lowest and highest moments the frame holds. That is what makes a disagreement readable from the log rather than showing up as a system that simply never trades.

The range is read only where the column is there and the frame holds something, and reported as nothing otherwise.

## What raises instead

The reading and the filtering stand before that guard. A frame without the columns named, or one that cannot be read at all, therefore raises before any of it — so the careful complaint answers a missing row and not a malformed frame.

## What a match gives

The first matching row's closing price, as a plain number.

## Related

- [Which prediction row is used](which-prediction-row-is-used.md)
- [What the prediction loop's stop leaves running](what-the-prediction-loops-stop-leaves-running.md)
