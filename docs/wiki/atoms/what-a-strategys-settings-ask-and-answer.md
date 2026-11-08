---
row: N14-05
baseline: 49aa659
created: 2026-11-08 23:20 UTC
modified: 2026-11-08 23:20 UTC
evidence:
  - claim: "A parameter set is refused unless what it was handed is a dictionary"
    source: "`nexus/strategy/params.py` 27-29"
  - claim: "Nothing else about what it was handed is weighed"
    source: "`nexus/strategy/params.py` 24-31, which tests it for nothing else"
  - claim: "Asking it for something it does not hold answers with whatever the asking named as its default"
    source: "`nexus/strategy/params.py` 44"
---
# What a strategy's settings ask and answer

The settings a strategy is configured with ask one thing of what they are handed and answer one question about it.

## The one check

What it was handed must be a dictionary; a mapping that is not one is refused. Nothing else is weighed: no key is read, no value is looked at, and no shape is required of either.

## The one answer

Asking for something the mapping does not hold gives back whatever the asking named as its default. So a caller decides for itself what a missing setting means, and the record takes no view.

The mapping is [copied and sealed](the-sealing-three-records-do.md) as the record is built.

## Related

- [The sealing three records do](the-sealing-three-records-do.md)
- [What a strategy must provide](what-a-strategy-must-provide.md)
