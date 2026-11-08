---
row: P7-01
baseline: 49aa659
created: 2026-11-09 07:30 UTC
modified: 2026-11-09 07:30 UTC
evidence:
  - claim: "Seven of a fill's fields are walked by name and each handed to a shared check that refuses an empty one"
    source: "`praxis/core/domain/fill.py` 65-68 over the seven names, into 69, refused at `praxis/core/domain/_require_str.py` 28-30"
  - claim: "The venue's own name for the trade is not among those seven, so nothing requires it to have anything in it"
    source: "`praxis/core/domain/fill.py` 65-68, which names it nowhere, the field itself at 46"
  - claim: "Where that field has something in it the key for spotting a repeat is that field alone"
    source: "`praxis/core/domain/fill.py` 94 into 95"
  - claim: "Where it is empty the key is four other fields taken together"
    source: "`praxis/core/domain/fill.py` 96, reached rather than 95"
  - claim: "Its moment must carry a zone, and that zone must give an offset, one test asking both"
    source: "`praxis/core/domain/fill.py` 71-73"
  - claim: "The event record a fill is reported as is held to that same test on its moment"
    source: "`praxis/core/domain/events.py` 115-117"
  - claim: "Every one of that event record's names is required, the venue's name for the trade among them"
    source: "`praxis/core/domain/events.py` 577-583, with the account reached through 574 into 113"
---
# What a fill's own record requires

A fill's own record is refused for failing any one of a fixed list of checks, and one of its names is not on that list.

## The seven names

One loop takes seven of its fields by name and hands each to a shared check: the venue's name for the order, the client name, the account, the trade, the command, the trading pair, and the asset the fee was charged in. An empty one is refused.

## The name left off the list

The venue's own name for the trade is not among the seven. Nothing requires it to have anything in it, so a record may carry it empty.

That is the field the key for spotting a repeat is taken from. Where it has something in it, the key is that field alone. Where it is empty, the key is four other fields taken together: the venue's name for the order, the price, the amount, and the moment.

## The moment

It must carry a zone, and that zone must give an offset. One test asks both.

[The event record a fill is reported as](what-a-fill-is.md) is held to the same test on its moment, and every one of its names is required.

## Related

- [What a fill's own record never asks](what-a-fills-own-record-never-asks.md)
- [The record nothing builds](the-record-nothing-builds.md)
- [Fills](what-a-fill-is.md)
