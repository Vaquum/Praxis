---
row: N71-01
baseline: 49aa659
created: 2026-11-13 02:30 UTC
modified: 2026-11-13 03:00 UTC
evidence:
  - claim: "The frame is read from the manifest entry's path joined onto the folder predictions are mounted at, with nothing holding the joined path inside that folder"
    source: "`nexus/strategy/predict_loop.py` 465, joining what 382 read"
  - claim: "A path leading to no file warns and the turn ends"
    source: "`nexus/strategy/predict_loop.py` 466-471"
  - claim: "The whole frame is read in, and rows whose reason code is anything but the usable one are dropped"
    source: "`nexus/strategy/predict_loop.py` 473, then 474"
  - claim: "A frame with nothing left after that dropping ends the turn without a word"
    source: "`nexus/strategy/predict_loop.py` 476-477"
  - claim: "Of what survives, the row with the greatest moment is the one taken, whatever order the frame held them in"
    source: "`nexus/strategy/predict_loop.py` 479"
  - claim: "That moment must stand strictly above the last one recorded for the same strategy and series, and a repeat ends the turn without a word"
    source: "`nexus/strategy/predict_loop.py` 394-397"
  - claim: "The prediction is cut to a whole number and then weighed against the two values, so one standing between them is taken as the whole number below it"
    source: "`nexus/strategy/predict_loop.py` 399, then 400-405"
  - claim: "A prediction that will not cut to a whole number raises rather than warning"
    source: "`nexus/strategy/predict_loop.py` 399, standing in no attempt"
---
# Which prediction row is used

A turn of [the loop that reads predictions](what-the-prediction-loops-stop-leaves-running.md) takes one row out of a frame of them, and most of the frame is never looked at.

## Where the frame comes from

The path the manifest's entry names, joined onto the folder predictions are mounted at. Nothing holds the joined path inside that folder, so a manifest naming a path that climbs out of it is read from wherever it leads.

A path leading to no file warns, and the turn ends.

## Which rows are candidates

The whole frame is read in, and every row whose reason code is anything but the usable one is dropped.

A frame with nothing left after that ends the turn without a word.

## Which candidate wins

The one with the greatest moment, whatever order the frame held its rows in. So the frame is treated as a set rather than a sequence, and a row appended out of order is still found.

## The moment it must beat

Strictly above the last moment recorded for that strategy and series. A repeat ends the turn without a word.

## What the prediction is held to

It is cut to a whole number, and the result weighed against the two allowed values.

So a figure standing between them is taken as the whole number below it rather than refused, and one that will not cut to a whole number at all raises rather than warning.

## Related

- [What the prediction loop's stop leaves running](what-the-prediction-loops-stop-leaves-running.md)
- [How a close is found for a prediction](how-a-close-is-found-for-a-prediction.md)
