---
row: P2-44
baseline: 49aa659
created: 2026-09-27 07:39 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "Where a host supplies its own receiver, Praxis's reports are sent before that receiver is awaited"
    source: "`launcher.py` 3001-3003"
  - claim: "A startup hands each unsent report to the sending call alone"
    source: "`launcher.py` 4534-4539, reached from 1814-1816"
  - claim: "Being finished with is judged on those reports' own names"
    source: "`launcher.py` 1735-1736 gathering them, applied at 1773-1776"
  - claim: "Praxis's own sending and that receiver are called as one, and a failed attempt calls the pair again"
    source: "the pair at `launcher.py` 3001-3003, set at 3005, called under the attempts at `execution_manager.py` 760-794"
  - claim: "The confirming record is written where the handing on succeeded and the change was stored, by the worker that takes the queue"
    source: "`launcher.py` 4464-4465, the queue fed at 2992"
  - claim: "A startup's replay calls that same handing on, and nothing else"
    source: "`launcher.py` 4533-4539"
---
# Who a restart tells again

Praxis can have two receivers for one [outcome](how-an-outcome-is-delivered.md). Where the host was handed a receiver of its own to include, Praxis sends its own reports first and waits on that second receiver afterwards.

That order decides what a startup can put right.

## What is sent again

The reports Praxis sends itself are the ones a startup sends again. Each carries a name, those names are what [the records](how-an-undelivered-outcome-is-replayed.md) mark as finished with, and anything unmarked goes back on the list — including a report the handing on did take, where the confirming record never landed.

## What is not

A startup hands each report not yet accounted for to Praxis's own sending, and to that alone, so nothing a startup sends again reaches the second receiver.

Within one run it can be sent the same outcome more than once. Praxis's own sending and that receiver are called as one, and a failed attempt calls the pair again, so a receiver that acts before it fails acts twice.

So the two can come apart. The confirming record is written by the worker that takes Praxis's own queue, where the handing on succeeded and the change was stored; the second receiver is not consulted for it. Its attempts can all run out while the records show the outcome produced and its reports received, with that receiver never having held it.

Nothing puts that right afterwards. A host that supplies its own receiver and needs delivery to it guaranteed has to guarantee that itself.

## Related

- [How an outcome is delivered](how-an-outcome-is-delivered.md)
- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
