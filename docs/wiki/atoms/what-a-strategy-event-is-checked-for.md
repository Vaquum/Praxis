---
row: N14-01
baseline: 49aa659
created: 2026-11-08 06:15 UTC
modified: 2026-11-08 06:15 UTC
evidence:
  - claim: "A strategy event is refused unless the strategy's reference and the kind it names are each text with something left in them once trimmed"
    source: "`nexus/infrastructure/strategy_event.py` 56-58, or 60-62"
  - claim: "The result it carries must be a finite decimal figure"
    source: "`nexus/infrastructure/strategy_event.py` 64-69"
  - claim: "No check of the record's own weighs that figure against nought"
    source: "`nexus/infrastructure/strategy_event.py` 53-89, which compares it with nought nowhere"
  - claim: "Its moment must be a moment, and must carry the UTC marker itself"
    source: "`nexus/infrastructure/strategy_event.py` 71-73, or 75-77"
---
# What a strategy event is checked for

A strategy event is refused for failing any one of a fixed list of checks.

## What must be there

The reference of the strategy it belongs to, and the kind it names, each text with something left once the blank space is trimmed off. Its moment, which must be a moment, and which must carry the universal-time marker itself.

## The result it carries

A finite decimal figure. A whole number is refused, however ordinary, because the check asks for a decimal and nothing else.

No check of the record's own weighs that figure against nought. A loss, a gain and nought are alike to it; [what the cut over thirty days leaves](what-the-thirty-day-cut-leaves.md) is where the sign is read.

## Related

- [The empty reference a strategy event allows](the-empty-reference-a-strategy-event-allows.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
- [Where a realized result is written down](where-a-realized-result-is-written-down.md)
