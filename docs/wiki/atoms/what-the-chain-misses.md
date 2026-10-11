---
row: P2-37
baseline: 49aa659
created: 2026-09-25 20:52 UTC
modified: 2026-10-11 20:49 UTC
evidence:
  - claim: "A walk holds no expected row count and no mark for which row should be last"
    source: "`event_spine.py` 1254-1291, with the kept values at 100-102 written at 593-595"
  - claim: "Rows carrying no mark are passed over while the opening run of them lasts"
    source: "`event_spine.py` 1261-1269"
  - claim: "The passing-over starts switched on and is only turned off by the first marked row"
    source: "`event_spine.py` 1255, turned off at 1271"
  - claim: "A marked row is checked against the one before it"
    source: "`event_spine.py` 1272-1277"
  - claim: "A marked row surviving that is checked against its own fields"
    source: "`event_spine.py` 1279-1287"
  - claim: "One carrying no mark after a marked row refuses the walk instead"
    source: "`event_spine.py` 1262-1268"
---
# What the chain misses

[The codes](the-chain.md) on a row catch a change made to that row alone. The check does not notice some other changes. These are some of them, and most need no code worked out again.

## Rows that never had codes

A row with no code is skipped rather than refused, while the opening run of such rows lasts. Anything done inside that run — changing one, or taking one out — is skipped with it, and the rows after it still pass their checks. One standing after a row that has a code refuses the walk instead, so the skipping covers the start of the record alone.

## Rows taken off the end

The check tests the rows it finds, and counts them only to say how many it saw. Nothing tells it how many there should have been, or which row should have been last.

So a spine cut short passes the check. Every surviving row still points properly at the one before it, and the check reaches the new final row and reports nothing wrong.

## Every code removed

The skipping of rows without codes starts switched on, and only the first row with one turns it off.

A spine whose codes have all been cleared therefore has no first row with one, so the skipping never turns off and every row goes untested. The check finishes having tested nothing, and the contents can say anything.

## Everything rewritten

Someone able to write the codes as well as the rows can alter a row, work out its code again, and redo every row after it. The chain then agrees with itself.

This is the costly one: every row after the altered one needs its codes worked out again. The others need no arithmetic at all.

## Related

- [The chain](the-chain.md)
- [What the chain proves](what-the-chain-proves.md)
