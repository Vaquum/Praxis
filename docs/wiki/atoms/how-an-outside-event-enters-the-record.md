---
row: P4-59
baseline: 49aa659
created: 2026-10-15 22:20 UTC
modified: 2026-10-15 22:20 UTC
evidence:
  - claim: "A running account's event is queued for its writer, and the caller waits on an answer the writer sets"
    source: "`execution_manager.py` 3210-3214, answered at 3816-3817"
  - claim: "An account still starting has its event written straight through by the one caller allowed to"
    source: "`execution_manager.py` 3194-3202"
  - claim: "That caller is refused where the account is not starting after all"
    source: "`execution_manager.py` 3195-3200"
  - claim: "An unknown account, a poisoned one, and one whose start failed are each refused by a raise"
    source: "`execution_manager.py` 3179-3181, 3183-3185 and 3187-3192"
  - claim: "Poisoning is weighed again after the record is written, so a write can land and still raise"
    source: "`execution_manager.py` 3233 against 3235-3237"
  - claim: "A writer cancelled mid-drain passes that straight on rather than answering the caller"
    source: "`execution_manager.py` 3828"
  - claim: "Any other failure is handed back to the caller as its answer"
    source: "`execution_manager.py` 3831-3832"
  - claim: "An event written down is only then put on the queue the dispatching reads"
    source: "`execution_manager.py` 3204-3205 and 3813-3815"
---
# How an outside event enters the record

News from outside — a fill off the feed, a venue update — is written to [the record](the-event-spine.md) by [the account's own writer](how-waiting-work-is-drained.md) and nobody else. A caller hands the event over and waits to be told how it went.

## Handed over, then waited on

The event goes on a queue of its own with a place for the answer, and the writer is woken. The caller then waits on that place, and the writer fills it in once the event is written and the books are moved.

So the caller is told by what the writer did, rather than by having done it.

## The one caller that writes straight through

An account still starting has no writer taking that queue, so nothing on it would ever drain. The caller doing the starting is therefore allowed to write straight through instead — and only that caller, who is refused where the account turns out not to be starting at all.

## Refused before anything is written

An account the manager has never heard of, one already poisoned, and one whose start failed are each refused by a raise.

Poisoning is weighed a second time after the record is written. A write can therefore land and the caller still be told it failed, which is why [the record is the account](what-the-chain-proves.md) and the answer is not.

## A writer that stops mid-way

A writer called off while draining passes that straight on, leaving the caller waiting on an answer that never comes. Any other failure is handed back as the answer itself.

## Related

- [The event spine](the-event-spine.md)
- [How waiting work is drained](how-waiting-work-is-drained.md)
- [When an update fails](when-an-update-fails.md)

---

Created 2026-10-15 22:20 UTC · Last modified 2026-10-15 22:20 UTC
