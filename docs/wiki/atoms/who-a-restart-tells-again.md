---
row: P2-44
baseline: 49aa659
created: 2026-09-27 07:39 UTC
modified: 2026-09-27 13:51 UTC
evidence:
  - claim: "Where a host supplies its own receiver, Praxis's reports are sent before that receiver is awaited"
    source: "`launcher.py` 3001-3003"
  - claim: "A startup hands each unsent report to the sending call alone"
    source: "`launcher.py` 4534-4539, reached from 1814-1816"
  - claim: "Being finished with is judged on those reports' own names"
    source: "`launcher.py` 1735-1736 gathering them, applied at 1773-1776"
---
# Who a restart tells again

Praxis can have two receivers for one [outcome](how-an-outcome-is-delivered.md). Where the host was handed a receiver of its own to include, Praxis sends its own reports first and waits on that second receiver afterwards.

That order decides what a startup can put right.

## What is sent again

The reports Praxis sends itself are the ones a startup sends again. Each carries a name, those names are what [the records](how-an-undelivered-outcome-is-replayed.md) mark as finished with, and anything unmarked goes back on the list — including a report the receiver did take, where the confirming record never landed.

## What is not

The second receiver is never sent anything twice. A startup hands each report not yet accounted for to Praxis's own sending, and to that alone.

So the two can come apart. Praxis's own reports may be through and marked finished while the second receiver's attempts run out, because its turn comes last. The records then show the outcome produced and its reports received, with the second receiver never having held it.

Nothing puts that right afterwards. A host that supplies its own receiver and needs delivery to it guaranteed has to guarantee that itself.

## Related

- [How an outcome is delivered](how-an-outcome-is-delivered.md)
- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
