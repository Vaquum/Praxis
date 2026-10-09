---
row: P2-44
baseline: 49aa659
created: 2026-09-27 07:39 UTC
modified: 2026-10-09 07:59 UTC
evidence:
  - claim: "Where a host supplies its own receiver, the outcome is queued for handling before that receiver is awaited"
    source: "`launcher.py` 3001-3003, the queue fed at 2992"
  - claim: "The queueing and that receiver are called as one, and a failed attempt calls the pair again"
    source: "the pair at `launcher.py` 3001-3003, set at 3005, called under the attempts at `execution_manager.py` 760-794"
  - claim: "The confirming record is written by the handling itself, where it succeeded and nothing failed to store"
    source: "`launcher.py` 4464-4465, the mark set at 4403 and cleared only where a store raises"
  - claim: "A startup calls that handling for each report it plans, and writes off the ones the handling refuses"
    source: "`launcher.py` 4533-4539, each one called at 1814-1816, written off at 1824-1828"
  - claim: "A produced report with no record of where it was going is left unaccounted for rather than planned"
    source: "`launcher.py` 1755-1763"
  - claim: "Being finished with is judged on those reports' own names"
    source: "`launcher.py` 1735-1736 gathering them, applied at 1773-1776"
  - claim: "A startup runs that replay before the queue has a taker"
    source: "`launcher.py` 4547, ahead of 4571 and 4573"
---
# Who a restart tells again

Praxis can have two receivers for one [outcome](how-an-outcome-is-delivered.md). Where the host was handed a receiver of its own to include, the outcome is put on a queue to be handled first, and that second receiver is awaited afterwards.

That order decides what a startup can put right.

## What is sent again

A startup sends again what the handling never confirmed. Each report carries a name, those names are what [the records](how-an-undelivered-outcome-is-replayed.md) mark as finished with, and anything unmarked goes back on the list — including a report the handling did take, where the confirming record never landed. One whose record of where it was going is missing is left alone instead, for a person to look at.

## What is not

A startup calls the handling for each report it plans, and writes off any the handling refuses, so what a startup sends again stops there and the second receiver is left out. The replay runs before the queue has a taker at all.

Within one run that receiver can be sent the same outcome more than once. The queueing and the receiver are called as one, and a failed attempt calls the pair again, so a receiver that acts before it fails acts twice.

So the two can come apart. The confirming record is written by the handling itself, where it succeeded and nothing failed to store; the second receiver is not consulted for it. Its attempts can all run out while the records show the outcome produced and its reports received, with that receiver never having held it.

Nothing puts that right afterwards. A host that supplies its own receiver and needs delivery to it guaranteed has to guarantee that itself.

## Related

- [How an outcome is delivered](how-an-outcome-is-delivered.md)
- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)

---

Created 2026-09-27 07:39 UTC · Last modified 2026-10-09 07:59 UTC
