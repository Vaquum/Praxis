---
row: N71-06
baseline: 49aa659
created: 2026-11-13 02:30 UTC
modified: 2026-11-13 03:00 UTC
evidence:
  - claim: "The cohort's reference and its name are read off the manifest's entry and written out on every turn that reaches this step"
    source: "`nexus/strategy/predict_loop.py` 527, and 528, reached at 407"
  - claim: "The step is reached past the manifest, the series entry, the row and the moment and the prediction, so an earlier ending writes no line at all"
    source: "`nexus/strategy/predict_loop.py` 407, standing after 355-405"
  - claim: "Neither is asked to be anything before it is written out"
    source: "`nexus/strategy/predict_loop.py` 527 and 528, with no test between them and 539"
  - claim: "A reference that is not text ends the recording there, so it is written to the log and remembered nowhere"
    source: "`nexus/strategy/predict_loop.py` 539-540"
  - claim: "A change is reported only where a reference was remembered before and differs from this one"
    source: "`nexus/strategy/predict_loop.py` 542, then 543"
  - claim: "The reference is then remembered against that strategy and series"
    source: "`nexus/strategy/predict_loop.py` 554"
  - claim: "All of it stands before the closing price is looked up, so a turn ending for want of a price has written the first line"
    source: "`nexus/strategy/predict_loop.py` 407, standing before 409"
---
# What the cohort line records

A prediction comes from a trained cohort, and a turn of [the loop](which-prediction-row-is-used.md) writes down which one before it looks up a price.

## The line it writes

The series, the cohort's name, and the cohort's reference. Both are read off the manifest's entry and neither is asked to be anything, so whatever the producer put there is what the log carries.

## Which turns write it

Those that get this far. The step stands past the manifest, the entry for the series, the row, the moment and the prediction — so a turn ending at any of those writes no cohort line at all.

It stands before the price is looked up. A turn ending for want of a price has therefore written its cohort line, and the log says a cohort was serving a turn that produced nothing.

## The second line

Written only where a reference was remembered before and differs from this one, naming the old and the new.

So the first reference seen for a pair writes no second line, there being nothing to differ from.

## A reference that is not text

The recording ends there. The cohort still appears in the first line, and nothing is remembered.

So a producer writing a reference of some other kind never gets a change reported, however often the cohort moves — the comparison needs something remembered, and nothing ever is.

## Related

- [Which prediction row is used](which-prediction-row-is-used.md)
- [How a close is found for a prediction](how-a-close-is-found-for-a-prediction.md)
