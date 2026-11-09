---
row: P111-02
baseline: 49aa659
created: 2026-11-14 09:00 UTC
modified: 2026-11-14 09:00 UTC
evidence:
  - claim: "An amount is snapped onto the symbol's step before anything is weighed against it"
    source: "`binance_adapter.py` 1518, ahead of 1520"
  - claim: "The snapped amount is what the order checks are made against"
    source: "`binance_adapter.py` 1520"
  - claim: "A paired order answers through its own parsing, and an order carrying a stop limit price without being paired is refused"
    source: "`binance_adapter.py` 1536, against 1538 into 1539-1540"
  - claim: "The parameters are then built from the snapped amount and whatever else was given"
    source: "`binance_adapter.py` 1542-1548"
  - claim: "The order is sent and its answer parsed by the same parsing a money-sized one uses"
    source: "`binance_adapter.py` 1549-1551, then 1552, and 1512"
---
# What an amount-sized order goes through

An order sized in coin is snapped to the venue's step first, and everything after is weighed against the snapped figure.

## The snapping comes first

The amount is snapped onto the symbol's step before anything is weighed against it. The snapped amount is then what the order checks are made against.

So a caller's amount is never checked as given: an amount that would fail a check before snapping may pass after it, and one that passes before may fail after. The figure the venue will see is the figure that was judged.

## The paired road

A paired order answers through its own parsing. An order carrying a stop limit price without being paired is refused — that figure means nothing outside a pair.

So the stop limit price is the one parameter whose presence alone decides nothing, and whose absence from a pair is an error rather than a default.

## What is sent

Parameters built from the snapped amount and whatever else was given, then sent.

## The shared ending

The answer is parsed by the same parsing a money-sized order uses. So the two roads differ in everything they check and agree on how they read what comes back.

## Related

- [What a money-sized order is refused for](what-a-money-sized-order-is-refused-for.md)
- [What an order type decides about its parameters](what-an-order-type-decides-about-its-parameters.md)
