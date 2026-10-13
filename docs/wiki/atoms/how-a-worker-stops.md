---
row: P1-12
baseline: 49aa659
created: 2026-10-12 07:10 UTC
modified: 2026-10-12 13:29 UTC
evidence:
  - claim: "A pass that dies poisons the account on its way out, empties its queue and ends the loop"
    source: "`execution_manager.py` 4025-4046, nothing after it taking a pass"
  - claim: "A request whose refusal cannot be reported reaches the decision side with nothing, though the log line names it"
    source: "`execution_manager.py` 7003-7019, the log at 7012-7018, reached from the emptying at 4042"
  - claim: "A cancelled pass loses the request it had in hand, taken off the queue and neither carried out nor refused"
    source: "`execution_manager.py` 3984 taking it, 4010-4011 leaving, 4020-4021 counting it done"
  - claim: "A new order is turned away on the way in afterwards, while a change is still taken and queued"
    source: "`execution_manager.py` 3434-3436 against 3060-3074, reached from `trading.py` 1910-1917"
  - claim: "A worker cancelled instead stops with nothing poisoned and its queue as it stands"
    source: "`execution_manager.py` 4022-4024, cancelled from 2966-2969"
  - claim: "A boot that runs through and ends not ready leaves the account starting for good, and its queue is emptied from outside any pass"
    source: "`trading.py` 606-623 reaching `execution_manager.py` 3643 and 3658-3661 instead of the finish at 3672, the pass then taking 3903-3905"
  - claim: "A boot that raises instead takes every started account's worker down with it, and no later account starts"
    source: "`trading.py` 525-528 into 813-818, leaving the loop at 521-524"
---
# How a worker stops taking work

[An account's worker](how-waiting-work-is-drained.md) goes round until something stops it taking the work on its queues, and three things do: its loop ends on a pass that died, its loop is cancelled, or the loop goes on turning while every pass stops short of that work. Each leaves the account in a different state.

## A pass that dies

Where a pass raises something nothing inside it caught, the account is marked failed, the requests still queued are refused one by one, and the loop ends there. Where a refusal cannot be reported, the decision side hears nothing and the log names what was dropped. Nothing takes a pass after that: an order arriving later is turned away on the way in, while a change to work already sent is still taken and queued, with no pass left to carry it out.

## A worker cancelled

Cancelling the work is how [unregistering an account](what-stopping-leaves-undone.md) ends its worker. The pass stops where it was, the account is not marked failed, and the queue stands bar one request: any the pass had taken is gone, neither carried out nor refused.

## A boot that never finishes

A boot that runs through and ends not ready leaves the account starting for good: the loop is still turning, but every pass takes the startup wait and nothing below it, and the failing startup empties the queue itself. The host carries on, that boot logged and parked while the other accounts start.

A boot that raises instead is a cancelling: every account started so far is unregistered, which cancels its worker, so one that had finished starting stops mid-pass, losing whatever that pass had in hand. No later account starts, and the raise [carries out of the host's starting](what-a-failure-at-startup-does.md).

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
- [What stopping leaves undone](what-stopping-leaves-undone.md)

---

Created 2026-10-12 07:10 UTC · Last modified 2026-10-12 13:29 UTC
