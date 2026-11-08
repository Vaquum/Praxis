---
row: N71-04
baseline: 49aa659
created: 2026-11-13 02:30 UTC
modified: 2026-11-13 03:00 UTC
evidence:
  - claim: "The run is applied to each entry of a signal's values in turn, giving a plain mapping"
    source: "`nexus/strategy/predict_loop.py` 90-93"
  - claim: "Text is passed through as it is, a decimal figure is turned into text, and a single value from the numeric library is unwrapped and put through the run again"
    source: "`nexus/strategy/predict_loop.py` 117-118, or 119-120, or 121-122"
  - claim: "An array, a column, a mapping, a list or a tuple is replaced by a note of its kind and size where it holds more than the cap allows"
    source: "`nexus/strategy/predict_loop.py` 125-126, or 130-131, or 137-138, or 147-148"
  - claim: "The key treatment is given to one kind of mapping alone, anything else carrying keys falling through to the tests below"
    source: "`nexus/strategy/predict_loop.py` 133, naming the one kind"
  - claim: "A collision among a mapping's keys once they are text is caught by comparing the length after against the length before"
    source: "`nexus/strategy/predict_loop.py` 139, then 140-141"
  - claim: "A length is read through a step that answers with nothing on an ordinary failure for a mapping, a list and the fall-through, while an array's size and a column's length are read directly"
    source: "`nexus/strategy/predict_loop.py` 134, or 144, or 150, each into 105-108, against 124, or 129"
  - claim: "Everything reaching the end is replaced by its printed form"
    source: "`nexus/strategy/predict_loop.py` 155"
  - claim: "The signals this loop builds carry three fixed values, two of them plain numbers and one a whole number, so one branch of the run is reached and the rest are not"
    source: "`nexus/strategy/predict_loop.py` 415-419 into 90-93, reaching 153-154"
---
# How a value is made safe to log

Writing a signal to the log puts every value in it through one run of tests in a fixed order, so that a value of an awkward kind cannot cost the log line.

## The run

Text is passed through. A decimal figure becomes text, which keeps an exactness a plain number would lose. A single value from the numeric library is unwrapped and put through the run again.

An array, a column, a mapping, a list or a tuple is measured first, and replaced by a note of its kind and size where it holds more than the cap allows. One within the cap becomes a list or mapping whose entries go through the run themselves.

A plain number, a true-or-false and nothing at all are passed through near the end. Everything reaching past that is replaced by its printed form.

## Two narrower things

The key treatment is given to one kind of mapping alone. Anything else carrying keys falls through to the tests below it.

A collision among a mapping's keys once they are text is caught by comparing the length after against the length before, and reported rather than losing an entry quietly.

## How a length is read

Through a step that answers with nothing on an ordinary failure — for a mapping, a list, and the fall-through. An array's size and a column's length are read directly instead.

## What this loop actually sends it

Three fixed values: a whole number and two plain numbers. So on this road one branch of the run is reached and the rest are not.

## Related

- [What the prediction loop's stop leaves running](what-the-prediction-loops-stop-leaves-running.md)
- [Which prediction row is used](which-prediction-row-is-used.md)
