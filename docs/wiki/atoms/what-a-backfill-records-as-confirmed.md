---
row: P102-02
baseline: 49aa659
created: 2026-11-14 04:30 UTC
modified: 2026-11-14 18:00 UTC
evidence:
  - claim: "A trade whose venue name will not read as a number is reported and skipped"
    source: "`praxis/trading.py` 1551 into 1552 into 1553-1558, then 1559"
  - claim: "A leg's name is turned into its parent's, falling back to the name itself"
    source: "`praxis/trading.py` 1561-1562"
  - claim: "The highest venue name seen is tracked as the walk goes, along with the trade that carried it"
    source: "`praxis/trading.py` 1572 into 1573-1574"
  - claim: "The cursor is moved only where the symbol's pages finished and some trade was seen"
    source: "`praxis/trading.py` 1576"
  - claim: "What is written is that highest name, that trade's own moment, the epoch and the clock at the time of writing"
    source: "`praxis/trading.py` 1577, then 1578-1585"
---
# What a backfill records as confirmed

A backfill moves a symbol's cursor forward only when it is sure it saw everything, and what it writes is the highest trade it saw.

## The trade it cannot use

One whose venue name will not read as a number is reported and skipped. The walk carries on, so an unreadable name costs that one trade and nothing else.

It also costs the cursor: a skipped trade cannot be the highest seen, so the cursor stops short of it and the next backfill asks from before it again.

## Finding the order

A leg's name is turned into its parent's, falling back to the name itself — the same lookup [a socket report makes](the-five-reasons-a-report-is-discarded.md).

## What is tracked

The highest venue name seen as the walk goes, along with the trade that carried it. So the cursor's new position is a trade the backfill actually read, rather than a count or a boundary it worked out.

## When the cursor moves

Only where the symbol's pages finished and some trade was seen. A truncated symbol leaves its cursor where it was, so the next backfill asks the same question again rather than skipping what it never read.

What is written is that highest name, that trade's own moment, the epoch, and the clock at the time of writing — the venue's moment for the trade, and this side's for the record.

## Related

- [What a backfill asks the venue for](what-a-backfill-asks-the-venue-for.md)
