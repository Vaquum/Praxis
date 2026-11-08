---
row: N12-01
baseline: 49aa659
created: 2026-11-08 06:30 UTC
modified: 2026-11-10 17:30 UTC
evidence:
  - claim: "An outcome is refused unless its own reference and the reference of the command it answers are each text with something left in them once trimmed"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 92-94, or 96-98"
  - claim: "Its kind must be one of the named ones, its moment must be a moment, and that moment must carry the UTC marker itself"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 100-102, or 104-106, or 108-110"
  - claim: "A size left over, where one is given at all, must be a finite figure at or above nought"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 138 into 139-144, or 146-148"
  - claim: "The two measures of execution quality are checked before that choice, and so whatever the kind as well"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 112 before 114-117"
  - claim: "That check is reached after the choice between the two lists, and is made whatever the kind"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 114-117 before 138"
---
# What an outcome is checked for

An outcome is refused for any one of a fixed list of failings.

## What must be there

Its own reference, and the reference of [the command it answers](what-a-command-is-checked-for.md), each text with something left once the blank space is trimmed off. Its kind, which must be one of the named ones. Its moment, which must be a moment, and which must carry the UTC marker itself.

## The size left over

A size left over may be left out. Where one is given it must be a finite figure at or above nought, so nought is allowed and anything below it is not.

That check is reached after the record has already been sent down [the list for a fill or the list for anything else](what-a-fill-must-carry.md), and it is made whatever the kind. [The two measures of execution quality](the-two-measures-an-outcome-reports.md) are checked whatever the kind as well, and theirs is reached before that choice. The checks every outcome answers therefore sit either side of the choice rather than all of them before it.

## Related

- [What a fill must carry](what-a-fill-must-carry.md)
- [The reason an outcome may carry](the-reason-an-outcome-may-carry.md)
- [The two measures an outcome reports](the-two-measures-an-outcome-reports.md)
