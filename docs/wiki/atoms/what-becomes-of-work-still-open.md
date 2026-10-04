---
row: P4-22
baseline: 49aa659
created: 2026-10-01 17:54 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "The reconciliation loop is called off before anything else"
    source: "`trading.py` 657-661"
  - claim: "Every command still in flight is sent an abandonment marked as a shutdown"
    source: "`trading.py` 665-677, queued at `execution_manager.py` 3027 and taken up at 3937-3941"
  - claim: "An abandonment refused on the way in has its command struck from the skip list"
    source: "`trading.py` 678-683"
  - claim: "An order belonging to a command still in flight is passed over by the second pass"
    source: "`trading.py` 700-702"
  - claim: "A working protective flatten is passed over too, known by the ids this account recorded when it posted one"
    source: "`trading.py` 704 and 721, against the ids read at 695-699 and recorded at `execution_manager.py` 7696-7705"
  - claim: "The rest are cancelled where they stand, a pair through the call meant for pairs"
    source: "`trading.py` 722-734"
---
# What becomes of work still open

Stopping trading is where a [host](stopping-a-host.md) deals with whatever is still open: [commands](what-a-trade-is.md) part-way through, and orders resting at the venue.

## Two passes

First the reconciliation loop is called off. Then every command still in flight is sent [an abandonment](where-an-abandonment-lands.md), marked as a shutdown, onto the queue the [account's worker](how-waiting-work-is-drained.md) takes priority work from.

An abandonment refused on the way in — where no worker is left to drain it, among other grounds — has its command struck from the skip list so the second pass picks its orders up.

That second pass takes the open orders left and cancels them where they stand, a [protective pair](protection.md) through the call meant for pairs. Orders belonging to a command still in flight are passed over, since the abandonment covers them.

## The one left standing

A [flatten put up to close a position](when-protection-is-put-up-again.md) is passed over, known by the ids this account recorded when it posted one. Cancelling it would hand back a position this host can no longer watch.

## Related

- [Where an abandonment lands](where-an-abandonment-lands.md)
- [What stopping leaves undone](what-stopping-leaves-undone.md)
- [Stopping a host](stopping-a-host.md)
