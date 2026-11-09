---
row: P107-02
baseline: 49aa659
created: 2026-11-09 08:20 UTC
modified: 2026-11-09 08:20 UTC
evidence:
  - claim: "An account the manager holds no state for is passed over, and so is one whose state the terminal pass cannot find"
    source: "`praxis/trading.py` 856 into 857-858, and 1656 into 1657-1658, and 1495"
  - claim: "The live orders are walked over a copy of the mapping, so a change to it during the walk disturbs nothing"
    source: "`praxis/trading.py` 860"
  - claim: "An order already at its end is passed over before the venue is asked anything"
    source: "`praxis/trading.py` 861 into 862"
  - claim: "Each remaining order is asked after by its own name, under its own symbol"
    source: "`praxis/trading.py` 864-869"
  - claim: "The terminal pass reads one moment and starts with no event in hand"
    source: "`praxis/trading.py` 1660, and 1661"
  - claim: "Where it built one, it is admitted marked as owned by a recovery or otherwise, as the caller said"
    source: "`praxis/trading.py` 1687 into 1688-1690"
  - claim: "A fill pass over an account the manager has lost does nothing, and each fill it admits is noted only where the manager found it new"
    source: "`praxis/trading.py` 1016 into 1017-1018, and 1072"
---
# Which orders a reconcile asks about

A reconcile asks the venue about the orders this side still thinks are live, one at a time, and skips the rest before asking anything.

## The accounts it does nothing for

One the manager holds no state for. The pass that settles an order's ending skips the same way, and so does the one that reconciles fills.

So every one of these passes begins by asking the manager for the account's state and answering where there is none. An account that has gone costs each pass one lookup.

## The copy

The live orders are walked over a copy of the mapping, so a change to it during the walk disturbs nothing. The walk can therefore admit events that close orders without disturbing its own iteration.

## What is skipped

An order already at its end, passed over before the venue is asked anything. So the asking is only ever about orders this side believes are still open.

## What is asked

Each remaining order, after by its own name and under its own symbol. One question per order rather than one per symbol.

## What the ending pass carries

One moment, read once, and no event in hand to begin with. Where it built one, it is admitted marked as owned by a recovery or otherwise, as the caller said.

## Related

- [What a submitting road refuses first](what-a-submitting-road-refuses-first.md)
