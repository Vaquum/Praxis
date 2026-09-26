---
row: P2-37
baseline: 49aa659
created: 2026-09-25 20:52 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "A walk holds no expected row count and no mark for which row should be last"
    source: "`event_spine.py` 1254-1291, with the kept values at 100-102 written at 593-595"
  - claim: "Rows carrying no mark are passed over while the run of them lasts"
    source: "`event_spine.py` 1261-1269"
  - claim: "The passing-over starts switched on and is only turned off by the first marked row"
    source: "`event_spine.py` 1255, turned off at 1271"
  - claim: "A marked row is checked against the one before it"
    source: "`event_spine.py` 1272-1277"
  - claim: "A marked row surviving that is checked against its own fields"
    source: "`event_spine.py` 1279-1287"
  - claim: "A row inside a run of unmarked rows is passed over the same way"
    source: "`event_spine.py` 1261-1269"
---
# What the chain misses

[The marks](the-chain.md) on a row catch a change made to that row alone. Other changes go through them untouched. These are some of them, and most need no mark worked out afresh.

## Rows that were never marked

A row with no mark on it is passed over rather than refused, to allow for rows written before the sealing began. Anything done inside such a run of rows — changing one, or taking one out — is passed over with it, while the marked rows after it stay sound.

## Rows taken off the end

A walk checks the rows it finds, and counts them only to say how many it saw. Nothing tells it how many there should have been, or which row should have been last.

So a spine cut short verifies. Every surviving row still points properly at the one before it, and the walk reaches the new final row and reports the chain sound.

## Every mark cleared

The passing-over starts switched on, and only the first marked row turns it off.

A spine whose marks have all been cleared therefore has no first marked row, so the passing-over never turns off and every row is skipped. The walk finishes having checked nothing, and the contents can say anything.

## Everything rewritten

Someone able to write the marks as well as the rows can alter a row, work out its mark afresh, and redo every row after it. The chain then agrees with itself.

This is the dear one: it needs the whole marked tail redone. The others need no arithmetic at all.

## Related

- [The chain](the-chain.md)
- [What the chain proves](what-the-chain-proves.md)
