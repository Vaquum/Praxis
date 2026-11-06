---
row: P5-04
baseline: 49aa659
created: 2026-11-05 16:22 UTC
modified: 2026-11-06 06:59 UTC
evidence:
  - claim: "The holdings figure on a freshly built state takes its default of nought, the pool being the only figure passed in"
    source: "`nexus/core/domain/instance_state.py` 156-157, the figure taking `nexus/core/domain/capital_state.py` 34 off 15"
  - claim: "Where the squaring begins a total of its own, that total begins at nought"
    source: "`nexus/startup/sequencer.py` 410 off 28"
  - claim: "Recovery sets the state, and runs ahead of the squaring"
    source: "`nexus/startup/sequencer.py` 239, and 246 where that found none, both inside the 175 that runs before 177"
---
# Where the figures a start squares start from

A freshly built state carries a holdings figure of nought, and the total the squaring builds begins at nought too.

## The figure the state carries

[A state built afresh](what-money-arriving-in-the-account-changes.md) is passed the account's capital pool and no other figure, so the holdings figure on it takes its default, which is nought.

## The total the squaring builds

The squaring builds a total of its own, and where it gets that far the total begins at nought.

## Which is standing when

Recovery is what sets the state, and it runs ahead of the squaring, so the figure the state carries is in place before the total is begun.

## Related

- [What a start weighs a position at](what-a-start-weighs-a-position-at.md)
- [What money arriving in the account changes](what-money-arriving-in-the-account-changes.md)
- [What stops a start squaring its holdings](what-stops-a-start-squaring-its-holdings.md)
