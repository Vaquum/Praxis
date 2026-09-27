---
row: P2-44
baseline: 49aa659
created: 2026-09-27 07:39 UTC
modified: 2026-09-27 07:39 UTC
evidence:
  - claim: "Where a host wraps the caller, the pieces it routes onward are handled before the wrapped one is awaited"
    source: "`launcher.py` 3001-3003"
  - claim: "A restart hands each owed piece to the routing call alone"
    source: "`launcher.py` 4534-4539, reached from 1814-1816"
  - claim: "Settling is judged on the routed pieces' own ids"
    source: "`launcher.py` 1735-1736 gathering them, applied at 1773-1776"
---
# Who a restart tells again

A [caller told of an outcome](how-an-outcome-is-delivered.md) may be two callers. Where the host was given one to wrap, it routes its own pieces onward first and awaits the wrapped one after.

That order decides what a restart can put right.

## What comes back

The pieces the host routes itself are the ones a restart offers again. They carry ids, those ids are what settling is judged on, and [the record says which are owed](how-an-undelivered-outcome-is-replayed.md).

## What does not

A wrapped caller is offered nothing a second time. The restart hands each owed piece to the routing call, and that call alone.

So the two can part company. The routed pieces may be through and settled while the wrapped caller's own tries run out, because its turn comes last. The record then shows the outcome produced and its pieces taken, with the wrapped caller never having held it.

Nothing reconciles that afterwards. A host that wraps the caller and needs its own delivery guaranteed has to keep that guarantee itself.

## Related

- [How an outcome is delivered](how-an-outcome-is-delivered.md)
- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
