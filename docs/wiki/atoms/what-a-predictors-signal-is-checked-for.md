---
row: N14-03
baseline: 49aa659
created: 2026-11-08 06:15 UTC
modified: 2026-11-08 06:15 UTC
evidence:
  - claim: "A signal is refused unless the predictor's reference is text with something left in it once trimmed, and unless what it was handed for its values is a dictionary"
    source: "`nexus/strategy/signal.py` 32-34, or 36-38"
  - claim: "Every key in those values must be text"
    source: "`nexus/strategy/signal.py` 40 into 41-43"
  - claim: "A value that is a whole number or a floating one must be finite, and so must a decimal one"
    source: "`nexus/strategy/signal.py` 45-47, or 49-51"
  - claim: "A value of any other kind is weighed in no way at all"
    source: "`nexus/strategy/signal.py` 40-51, which tests a value for nothing else"
  - claim: "Its moment must be a moment, and must carry the UTC marker itself"
    source: "`nexus/strategy/signal.py` 53-55, or 57-59"
---
# What a predictor's signal is checked for

A signal is refused for failing any one of a fixed list of checks.

## What must be there

The reference of the predictor it came from, text with something left once the blank space is trimmed off. A dictionary of values; a mapping that is not one is refused. A moment, which must be a moment and must carry the universal-time marker itself.

## What is asked of the values

Each key must be text. A key that is not is turned back, whatever its value.

Each value meets two tests in turn, both about numbers, the second reached only where the first let the value by: a whole number or a floating one must be finite, and a decimal one must be finite. Nothing else about a value is tested, so a value that is text, a list, a mapping of its own, or a none, is weighed in no way at all.

## Related

- [The sealing three records do](the-sealing-three-records-do.md)
- [What a strategy is handed](what-a-strategy-is-handed.md)
