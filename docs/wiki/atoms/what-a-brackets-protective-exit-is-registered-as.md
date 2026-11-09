---
row: P121-01
baseline: 49aa659
created: 2026-11-15 05:00 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "The protective exit's record is written as the entry is registered, before any protection has been placed"
    source: "`launcher.py` 2194-2197 into 2198-2200, reaching 1578-1588"
  - claim: "Its side is the opposite of the entry's, settled by testing the entry for a buy, so an entry that is anything else is protected by a buy"
    source: "`launcher.py` 1575-1577"
  - claim: "Its size, its sum and its fees are the entry's planned figures"
    source: "`launcher.py` 1583-1585"
  - claim: "It is marked as not an entry, and as meaning the whole remainder whatever the entry was"
    source: "`launcher.py` 1586, then 1587"
  - claim: "It is written durably and then in memory under the registry's lock, and its name handed back"
    source: "`launcher.py` 1589, then 1590 into 1591-1593, then 1596"
  - claim: "The in-memory write replaces whatever stood under that name, where the entry's own write only fills a gap"
    source: "`launcher.py` 1591, against 2083 into 2085-2087"
  - claim: "A rollback drops the entry's registration only where it put one in, and the exit's wherever a bracket name was recorded"
    source: "`launcher.py` 2006 into 2007, against 2008 into 2009"
  - claim: "An entry that ends leaving no position has the exit's registration dropped by name, a drop that does nothing where no bracket registered one"
    source: "`launcher.py` 4393 into 4394-4398, reaching 1620, then 1621 into 1622"
---
# What a bracket's protective exit is registered as

A bracket entry has a record written for its protective exit at the moment the entry is registered, long before any protection has been placed.

## What the record says

Its side is the opposite of the entry's, settled by testing the entry for a buy — so an entry that is anything other than a buy is protected by a buy.

Its size, its sum and its fees are the entry's planned figures, not what the entry turned out to fill. It is marked as not an entry, and as meaning the whole remainder whatever the entry was.

## Where it is written

Durably first, and then in memory under the registry's lock, which is how the entry's own record is written too. So the exit inherits whatever the entry's record survives.

## Where the two writes differ

The exit's in-memory write replaces whatever stood under [its name](the-name-a-brackets-exit-is-given.md). The entry's own fills a gap and leaves anything already there alone.

The undoing differs the same way round. A rollback drops the entry's registration only where that same pass put one in, and drops the exit's wherever a bracket name was recorded at all.

## When it is dropped

An entry that ends leaving no position has the exit's registration dropped by name. The drop asks nothing about brackets, so it does nothing at all for an entry that registered no exit.

So a bracket whose entry never left a position behind costs one write and one drop, and a bracket that did leaves the record standing for the protection to fill against.

## Related

- [The name a bracket's exit is given](the-name-a-brackets-exit-is-given.md)
- [What rebuilding an order's record is given](what-rebuilding-an-orders-record-is-given.md)
- [Protection](protection.md)
