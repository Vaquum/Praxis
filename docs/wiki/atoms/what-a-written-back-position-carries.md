---
row: N4-03
baseline: 49aa659
created: 2026-10-23 11:20 UTC
modified: 2026-10-25 09:00 UTC
evidence:
  - claim: "Its size and price are read off what the host gave for it"
    source: "`nexus/startup/sequencer.py` 414-415"
  - claim: "Its strategy, symbol and side are worked out first, and where they cannot be, nothing is built"
    source: "`nexus/startup/sequencer.py` 276-280, the working out at 317-346"
  - claim: "That size becomes the position's size, and that price stands as both the price it was entered at and its cost basis"
    source: "`nexus/startup/sequencer.py` 288-290"
  - claim: "Building it can refuse what it is given, and a refusal answers with nothing"
    source: "`nexus/startup/sequencer.py` 292-298, the checks that refuse at `nexus/core/domain/position.py` 60-88"
  - claim: "The caller then passes the position over, leaving it out of the record and out of the sum alike"
    source: "`nexus/startup/sequencer.py` 423-436 against 437-438"
  - claim: "A position the record built itself keeps those two prices apart, the cost basis taking the fees in as the position grows and the price entered at staying the price alone"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 480-485 into 489-490"
  - claim: "The gain on a later sale is taken from the price entered at"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 523-525"
  - claim: "The money that sale releases is taken from the cost basis"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438 into 242-247"
  - claim: "Nothing is given for what is already sold against it, which leaves that figure at the nought it is declared with"
    source: "`nexus/startup/sequencer.py` 284-291 against `nexus/core/domain/position.py` 54"
---
# What a written-back position carries

A written-back position is one a start builds from what the host holds, and it carries less than a position the record built for itself.

## What is taken from the host

Its size and price are read off what the host gave for it. Its strategy, symbol and side are worked out first; where they cannot be, nothing is built at all.

That size becomes the position's size. That price stands twice over: as the price the position was entered at, and as its cost basis.

Building it can still refuse what it is given. A refusal answers with nothing, and the caller passes the position over — leaving it out of [the record and the sum](what-a-start-weighs-a-position-at.md) alike.

## Where that differs

A position the record built for itself keeps those two prices apart. The cost basis takes the fees in as the position grows; the price entered at stays the price alone. A written-back position collapses them onto one figure.

The two are read for different things. The gain on a later sale is taken from the price entered at; the money that sale releases is taken from the cost basis. On a written-back position both come off the same number.

## What it does not carry

Nothing is given for [what is already sold against it](what-a-pending-sale-is.md), which leaves that figure at the nought it is declared with.

## Related

- [What a start weighs a position at](what-a-start-weighs-a-position-at.md)
- [What a pending sale is](what-a-pending-sale-is.md)

---

Created 2026-10-23 11:20 UTC · Last modified 2026-10-25 09:00 UTC
