---
row: P1-12
baseline: 49aa659
created: 2026-10-12 07:10 UTC
modified: 2026-10-12 10:29 UTC
evidence:
  - claim: "A pass that dies poisons the account on its way out, empties its queue and ends the loop"
    source: "`execution_manager.py` 4025-4046, nothing after it taking a pass"
  - claim: "A request whose refusal cannot be reported is dropped rather than refused"
    source: "`execution_manager.py` 7003-7019, reached from the emptying at 4042"
  - claim: "A new order is turned away on the way in afterwards, while a change is still taken and queued"
    source: "`execution_manager.py` 3434-3436 against 3060-3074, reached from `trading.py` 1910-1917"
  - claim: "A worker cancelled instead stops with nothing poisoned and its queue as it stands"
    source: "`execution_manager.py` 4022-4024, cancelled from 2966-2969"
  - claim: "A boot that ends failed leaves the account starting for good, and its queue is emptied from outside any pass"
    source: "`trading.py` 606-623 reaching `execution_manager.py` 3643 and 3658-3661 instead of the finish at 3672, the pass then taking 3903-3905"
---
# How a worker stops taking work

[An account's worker](how-waiting-work-is-drained.md) goes round until something stops it taking the work on its queues, and three things do: its loop ends on a pass that died, its loop is cancelled, or the loop goes on turning while every pass stops short of that work. Each leaves the account in a different state.

## A pass that dies

Where a pass raises something nothing inside it caught, the account is marked failed, the requests still queued are refused one by one — bar any whose refusal cannot be reported, which is dropped with nothing said — and the loop ends there. Nothing takes a pass after that: an order arriving later is turned away on the way in, while a change to work already sent is still taken and queued, with no pass left to carry it out.

## A worker cancelled

Cancelling the work is how [unregistering an account](what-stopping-leaves-undone.md) ends its worker. The pass stops where it was, the account is not marked failed, and the ordinary queue is left as it stands.

## A boot that never finishes

A boot that fails leaves the account starting for good, and this is the ending where the loop is still turning. The host carries on: the failed boot is logged and parked, and the other accounts start. Every pass takes the startup wait and does nothing else, so none of the work below that wait is ever reached. The failing startup empties the queue itself, rather than leaving it to a pass.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
- [What stopping leaves undone](what-stopping-leaves-undone.md)

---

Created 2026-10-12 07:10 UTC · Last modified 2026-10-12 10:29 UTC
