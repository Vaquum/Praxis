---
row: N78-03
baseline: 49aa659
created: 2026-11-09 02:48 UTC
modified: 2026-11-09 02:48 UTC
evidence:
  - claim: "Every check that a figure is present at all is an assertion, and each one names a field of the outcome"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 413, or 445-446, or 458-461, or 499-501"
  - claim: "How many are asserted differs by routine, from the one the cost working needs to the four a growing does"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 413, against 458-461"
  - claim: "Every check that raises is about the state instead: no trade named, no position under that name, or a size the position cannot cover"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 465, or 471, or 505, or 511, or 521, or 600 into 601-602"
  - claim: "An exit against a position whose cost basis stands at nought is noticed as the figures are worked out, and the reducing goes on"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 535, the work carrying on at 558-560"
---
# What a position change checks

Each routine that moves a position checks something before it starts, and the checks fall into two kinds.

## What is asserted

Every check that a figure is present at all is an assertion, and every one of them names a field of the outcome. How many differs by routine: the cost working asserts one, a growing asserts four.

So the assertions all say the same kind of thing — that the record arriving carries what this routine reads from it.

## What raises

Every check that raises is about the state instead. No trade named, no position under that name, or a size the position cannot cover.

The line is drawn between a field the arriving record should carry and a thing that should already exist to be changed. The first is asserted, the second refused.

## The check that stops nothing

An exit against a position whose cost basis stands at nought is noticed as the figures are worked out. Nothing stops: the reducing goes on and the position shrinks as it would otherwise.

It is the one check on this path whose answer changes nothing about what happens next.

## Related

- [What an entry outcome changes](what-an-entry-outcome-changes.md)
- [Where the locks sit on a position change](where-the-locks-sit-on-a-position-change.md)
