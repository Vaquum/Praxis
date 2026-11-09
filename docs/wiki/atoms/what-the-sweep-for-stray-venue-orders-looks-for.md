---
row: P106-01
baseline: 49aa659
created: 2026-11-14 06:30 UTC
modified: 2026-11-14 18:00 UTC
evidence:
  - claim: "An account the manager holds no state for is answered as safe without the venue being asked"
    source: "`praxis/trading.py` 928 into 929-930"
  - claim: "What counts as known is every live order together with every closed one"
    source: "`praxis/trading.py` 932"
  - claim: "The command fragments this host owns are taken before the asking begins"
    source: "`praxis/trading.py` 933"
  - claim: "The symbols asked about are the account's active ones together with the ones a bootstrap filters on, walked in sorted order"
    source: "`praxis/trading.py` 934-937, then 940"
  - claim: "A venue that refuses one symbol marks the whole sweep unsafe and the walk goes on to the next"
    source: "`praxis/trading.py` 938, then 941-942 into 943, then 950, then 951"
  - claim: "A venue order whose name the host already knows is passed over"
    source: "`praxis/trading.py` 953 into 954-955"
  - claim: "A name carrying no fragment of this host's, or one this host does not own, is noted rather than acted on"
    source: "`praxis/trading.py` 957 into 958-959"
---
# What the sweep for stray venue orders looks for

The sweep asks the venue what it has open and looks for anything the host does not know about.

## The account it skips

One the manager holds no state for is answered as safe, without the venue being asked at all.

## What counts as known

Every live order together with every closed one. So an order the host closed long ago is still recognised, and the sweep does not mistake its own finished work for a stray.

## What is gathered first

The command fragments this host owns, taken before the asking begins. So the ownership question is answered against a snapshot from before the venue replied, rather than against whatever has changed since.

## The symbols

The account's active ones together with the ones a bootstrap filters on, walked in sorted order — the same union [the backfill uses](what-a-backfill-asks-the-venue-for.md).

## The refusal that does not stop it

A venue that refuses one symbol marks the whole sweep unsafe and the walk goes on to the next. So one symbol's failure costs the sweep's verdict but not the other symbols' asking.

## What is looked at and let be

A venue order whose name the host already knows is passed over. A name carrying no fragment of this host's, or one this host does not own, is noted rather than acted on — it belongs to somebody else.

## Related

- [What a backfill asks the venue for](what-a-backfill-asks-the-venue-for.md)
