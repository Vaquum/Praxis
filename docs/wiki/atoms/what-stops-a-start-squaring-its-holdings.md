---
row: P5-03
baseline: 49aa659
created: 2026-11-05 16:22 UTC
modified: 2026-11-06 06:59 UTC
evidence:
  - claim: "Where Nexus holds a position for a trade the Praxis report has no entry for, the start collects every such trade and raises"
    source: "`nexus/startup/sequencer.py` 382-385 into 404-408"
  - claim: "That raise stands before the total the squaring builds, so nothing is weighed"
    source: "`nexus/startup/sequencer.py` 404-408, which raises rather than reaching 410-472"
  - claim: "The write the squaring can ask for stands further on still"
    source: "`nexus/startup/sequencer.py` 404-408, which raises rather than reaching 478-481"
---
# What stops a start squaring its holdings

One disagreement between what Nexus recovered and what Praxis reports ends a start before anything is weighed at all.

## The holding Praxis does not report

Where Nexus holds a position for a [trade](what-a-trade-is.md) the Praxis report has no entry for, the start collects every such trade and raises. The raise stands before any total is built, so nothing is weighed, and [the write the squaring can ask for](what-a-checkpoint-holds.md) stands further on still.

## Related

- [What a start does with a dusted position](what-a-start-does-with-a-dusted-position.md)
- [What a start weighs a position at](what-a-start-weighs-a-position-at.md)
- [What a failure at startup does](what-a-failure-at-startup-does.md)
- [Where an imported position's names come from](where-an-imported-positions-names-come-from.md)
