---
row: P116-01
baseline: 49aa659
created: 2026-11-14 11:30 UTC
modified: 2026-11-14 11:30 UTC
evidence:
  - claim: "A venue trade is built from fields each read by name, so one the venue leaves out stops the reading"
    source: "`binance_adapter.py` 1090-1104"
  - claim: "A submitted order's answer names the venue's order, its status put through a mapping, and the fills that came with it"
    source: "`binance_adapter.py` 948-951"
  - claim: "An order list names four fields read the same way, beside its legs"
    source: "`binance_adapter.py` 1070-1075"
  - claim: "The fills are read with an empty list standing in for one absent"
    source: "`binance_adapter.py` 937-947"
  - claim: "The legs are read the same way"
    source: "`binance_adapter.py` 1054-1061"
  - claim: "A list answering with no legs is refused outright, the refusal naming the list, where a submit answering with no fills is built all the same"
    source: "`binance_adapter.py` 1063 into 1064-1068, against 948-951"
  - claim: "Every fill read off a submitted order is marked a taker rather than read as one, where a venue trade's own maker flag is read"
    source: "`binance_adapter.py` 937-947, against 1090-1104"
  - claim: "An execution report's kind is looked up in a fixed mapping, and one the mapping does not hold stops the reading"
    source: "`binance_adapter.py` 2514, then 2515 into 2516, or 2518-2519"
  - claim: "Its order type is worked out from two fields, the second read with an empty standing in"
    source: "`binance_adapter.py` 2521"
  - claim: "Every other field of it is read from one"
    source: "`binance_adapter.py` 2523-2546"
---
# How a venue answer becomes a record

Four readings turn an answer from the venue into a record Praxis keeps, and each takes the fields it needs by name.

## Read by name

A venue trade is built from fields each read by name, so a field the venue leaves out stops the reading rather than standing in as nothing. A submitted order's answer and an order list are read the same way: the first names the venue's order, its status put through a mapping, and the fills that came with it, the second four fields beside its legs.

## The two collections

Fills on a submitted order, and legs on an order list, are the exception. Each is read with an empty list standing in for one absent, so neither has to be there.

## What the empty costs

A list answering with no legs is refused outright, the refusal naming the list. A submit answering with no fills is built all the same and carries none.

So the same leniency in the reading ends in a refusal on one side and a record on the other, and which it is depends on the record being built rather than on the answer.

## A taker by assumption

Every fill read off a submitted order is marked a taker rather than read as one. A venue trade reads its own maker flag instead, so the two readings part on that one field.

## The kind of an execution report

Looked up in a fixed mapping, and one the mapping does not hold stops the reading. The report's order type is worked out from two fields, the second read with an empty standing in, where every other field of it is read from one.

## Related

- [What an execution report is held to](what-an-execution-report-is-held-to.md)
- [What the venue's own records are held to](what-the-venues-own-records-are-held-to.md)
- [Part-shown orders](part-shown-orders.md)
