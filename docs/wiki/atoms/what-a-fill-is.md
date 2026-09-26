---
row: P2-15
baseline: 49aa659
created: 2026-09-26 05:44 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "A fill carries venue and Praxis names, symbol, side, amount, price, fee and fee asset, and whether it was posted or taken"
    source: "built with all of them at `execution_manager.py` 4312-4326"
  - claim: "One send can come back reporting several"
    source: "`execution_manager.py` 4311"
  - claim: "A protective replacement found already finished is held instead, and the reply's reports go unmade"
    source: "`execution_manager.py` 9749-9767, the loop it returns before at 9769"
  - claim: "A later reconciling can still make them, from the venue's own trade list"
    source: "`execution_manager.py` 8188-8206, called at 7452-7455"
  - claim: "Refused unless the amount and price are above zero and the fee is not below it"
    source: "`events.py` 585-595"
  - claim: "Refused unless its names are present and its time carries a zone"
    source: "`events.py` 577-583, the time checked by the base at 574"
---
# Fills

A **fill** is one execution a [venue](what-a-venue-is.md) reports against an [order](what-a-trade-is.md): an amount, at a price, at a time. A single send can come back reporting several, and on the ordinary path a fill is made for each.

Each one carries the venue's own name for the execution and for the order, the Praxis names for the trade and the command behind it, the symbol, the side, the amount, the price, the fee and the asset the fee was charged in, and whether the order waited to be taken or took what was already there.

## What a fill must have

A fill is refused as it is made unless its amount and its price are both above zero, and its fee is zero or more.

It is refused too unless every one of its names is a real name rather than an empty one, and unless its time carries a zone. A fill with no zone on it cannot be placed against the others in order, so it is turned away rather than guessed at.

## An execution the reply does not turn into one

A protective pair put up to replace another, found already finished the moment it was placed, is held aside to be sorted out later. The executions its reply reported are passed over there.

They are not lost. A later reconciling reads the venue's own list of trades for that order and makes the fills from those instead — one of the [several routes](where-duplicates-stop.md) by which the same execution can arrive.

Every fill, however it was made, is offered to the record before anything acts on it.

## Related

- [Where duplicates stop](where-duplicates-stop.md)
- [What a fill changes](what-a-fill-changes.md)
