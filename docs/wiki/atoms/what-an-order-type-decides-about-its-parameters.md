---
row: P109-02
baseline: 49aa659
created: 2026-11-09 08:28 UTC
modified: 2026-11-09 08:28 UTC
evidence:
  - claim: "Each order kind is looked up in a table of what it demands, and a kind the table lacks is refused as unsupported"
    source: "`binance_adapter.py` 775, then 777 into 778-779"
  - claim: "A kind whose table entry demands a price refuses an order without one, and the same for a stop price"
    source: "`binance_adapter.py` 784 into 785-786, and 788 into 789-790"
  - claim: "A kind whose entry demands no price refuses an order that carries one"
    source: "`binance_adapter.py` 792"
  - claim: "A price or a stop price is written out in full decimal rather than as a figure"
    source: "`binance_adapter.py` 808 into 809, and 811 into 812"
  - claim: "A time in force is filled in from a default where none was chosen"
    source: "`binance_adapter.py` 826"
  - claim: "A caller's own name for the order is added only where one was given"
    source: "`binance_adapter.py` 828 into 829, the whole answered at 831"
  - claim: "Reading a kind back weighs the plain limit kind first, splitting it by its time in force before any table is consulted"
    source: "`binance_adapter.py` 912, then 914 into 915, or 916"
  - claim: "Every other kind comes from a table, and one the table lacks raises"
    source: "`binance_adapter.py` 918 into 919-920, then 922-923"
---
# What an order type decides about its parameters

Each kind of order carries a table entry saying what it must and must not have, and the building checks the order against that entry.

## The table

Each kind is looked up in a table of what it demands. A kind the table lacks is refused as unsupported, so the table is the list of kinds this adapter can send at all.

## What an entry can demand

A price, or a stop price. A kind whose entry demands one refuses an order without it.

An entry can also forbid: a kind whose entry demands no price refuses an order that carries one. So the table both requires and excludes, and a parameter that is merely unnecessary is treated as an error rather than ignored.

## How the figures are written

A price or a stop price goes out in full decimal rather than as a figure, so no exponent form can reach the venue.

A time in force is filled in from a default where none was chosen. A caller's own name for the order is added only where one was given.

## Reading a kind back

The plain limit kind is weighed first and split by its time in force, before any table is consulted. Every other kind comes from a table, and one the table lacks raises.

So the two directions are not symmetrical: going out, every kind comes from one table; coming back, one kind is special-cased ahead of the table.

## Related

- [What signing a request adds](what-signing-a-request-adds.md)
