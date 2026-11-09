---
row: P169-02
baseline: 49aa659
created: 2026-11-16 05:00 UTC
modified: 2026-11-16 05:00 UTC
evidence:
  - claim: "The shown size is carried only where it falls below the whole size, and left out otherwise"
    source: "`execution_manager.py` 5295, then 5296"
  - claim: "The order's name is worked out with a place of nought, the command having one order and no more"
    source: "`execution_manager.py` 5297-5299"
  - claim: "One moment is taken and carried into the record of the intent"
    source: "`execution_manager.py` 5300, then 5302-5316, the moment set at 5304"
  - claim: "The intent is recorded, applied, and the command mapped to the order's name before anything is sent"
    source: "`execution_manager.py` 5317, then 5318, then 5319, then 5321"
  - claim: "The whole size is what the intent names, with no spend"
    source: "`execution_manager.py` 5311, and 5312"
  - claim: "The shown size left out is what the venue is sent, so the order rests as a plain limit"
    source: "`execution_manager.py` 5296, carried to 5322-5325"
---
# What a hidden-size order shows the venue

An order that shows only part of itself carries two sizes — the whole one and the one on display — and the second is sent only when it is smaller than the first.

## The one reading

The shown size is carried only where it falls below the whole size. A shown size at or above the whole one is left out, and the venue is sent no shown size at all — the order rests as a plain limit, which is what showing all of it means.

## Before the venue hears

The order's name is worked out with a place of nought: the command has one order and no more.

One moment is taken and carried into the record of the intent. The intent names the whole size and no spend, and it is recorded, applied, and the command mapped to the order's name — all three before anything is sent.

So the record holds the order, under the name it will be sent with, before the venue knows of it.

## Related

- [What figures a changed order's replacement is given](what-figures-a-changed-orders-replacement-is-given.md)
- [Where the order type decides](where-the-order-type-decides.md)
- [What is written down when a flatten goes out](what-is-written-down-when-a-flatten-goes-out.md)
