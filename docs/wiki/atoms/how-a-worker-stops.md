---
row: P1-12
baseline: 49aa659
created: 2026-10-12 07:10 UTC
modified: 2026-10-12 07:10 UTC
evidence:
  - claim: "A pass that dies poisons the account on its way out, empties its queue and ends the loop"
    source: "`execution_manager.py` 4025-4046, nothing after it taking a pass"
  - claim: "A worker cancelled instead stops with nothing poisoned and its queue as it stands"
    source: "`execution_manager.py` 4022-4024, cancelled from 2966-2969"
  - claim: "A boot that ends failed leaves the account starting for good, and its queue is emptied from outside any pass"
    source: "`trading.py` 606-623 reaching `execution_manager.py` 3643 and 3658-3661 instead of the finish at 3672, the pass then taking 3903-3905"
---
# How a worker stops

[An account's worker](how-waiting-work-is-drained.md) goes round until something ends it, and three things do. Each leaves the account in a different state.

## A pass that dies

Where a pass raises something nothing inside it caught, the account is marked failed, every request still queued is refused, and the loop ends there. Nothing takes a pass after that, so what arrives later is turned away on the way in rather than queued.

## A worker cancelled

Cancelling the work is how [unregistering an account](what-stopping-leaves-undone.md) ends its worker. The pass stops where it was, the account is not marked failed, and the ordinary queue is left as it stands.

## A boot that never finishes

An account whose [startup](what-a-failure-at-startup-does.md) ends failed never finishes starting. Its worker keeps going round, but every pass takes the startup wait and does nothing else, so none of the work below that wait is ever reached. The failing startup empties the queue itself, rather than leaving it to a pass.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
- [What stopping leaves undone](what-stopping-leaves-undone.md)

---

Created 2026-10-12 07:10 UTC · Last modified 2026-10-12 07:10 UTC
