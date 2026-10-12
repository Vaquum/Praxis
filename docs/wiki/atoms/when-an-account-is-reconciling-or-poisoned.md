---
row: P1-11
baseline: 49aa659
created: 2026-10-12 04:21 UTC
modified: 2026-10-12 06:40 UTC
evidence:
  - claim: "A reconciling or poisoned account takes no submitted work, and its pass ends on the wait"
    source: "`execution_manager.py` 3969-3971"
  - claim: "The pass still takes venue news, empties the priority line and retries a due cancellation"
    source: "`execution_manager.py` 3907 and 3910, with the retry at 3960"
  - claim: "Poisoned, the ordinary queue is emptied and each request in it refused"
    source: "`execution_manager.py` 3962-3967, body at 6988-6999"
  - claim: "A request whose refusal report cannot be built is dropped unreported"
    source: "`execution_manager.py` 7003-7019"
  - claim: "A cancelled worker stops the emptying and leaves the rest queued"
    source: "`execution_manager.py` 7000-7002"
  - claim: "Poisoning while the worker runs comes from projecting an admitted event that failed, the failure being handed back to whoever admitted it"
    source: "`execution_manager.py` 3249-3254, reached from the pass at 3809, handed back at 3830-3832"
  - claim: "A pass that dies poisons the account on its way out, empties its queue and ends the loop"
    source: "`execution_manager.py` 4025-4046, nothing after it taking a pass"
  - claim: "A worker cancelled instead stops with nothing poisoned and its queue as it stands"
    source: "`execution_manager.py` 4022-4024, cancelled from 2966-2969"
  - claim: "A boot that ends failed leaves the account starting for good, and its queue is emptied from outside any pass"
    source: "`trading.py` 606-623 reaching `execution_manager.py` 3643 and 3658-3661 instead of the finish at 3672, the pass then taking 3903-3905"
---
# When an account is reconciling or poisoned

An account being brought back into step with the venue is **reconciling**, and one carrying a fault that needs a restart is **poisoned**. [A pass](how-waiting-work-is-drained.md) under either takes no [submitted work](how-an-order-is-placed.md), and ends on the same wait an empty queue brings.

## What the pass still does

It takes the waiting venue news, empties [the priority line](the-priority-line.md) and retries a [cancellation](how-a-trade-is-cancelled.md) that is due. Changes put back in the line are left until the next pass.

Poisoned, the pass then empties its ordinary queue, refusing each request in it. Reconciling, that queue is left as it stands, so the requests in it go on waiting for the account to come back.

## What the emptying leaves

A request whose refusal report cannot be built is dropped with nothing reported at all. Where the worker is cancelled partway through the emptying, it stops where it was and whatever is still queued stays queued.

## Where there is no such pass

An account is poisoned while its worker runs when projecting an admitted event fails; the pass hands that failure back to whoever admitted the event and carries on. Three other endings leave no pass to describe. A pass that dies otherwise poisons the account on its way out, empties the queue and ends the loop, so the worker is gone rather than going round. A worker cancelled, which is how [stopping](what-stopping-leaves-undone.md) ends one, stops with nothing poisoned and the queue as it stands. And an account whose [startup](what-a-failure-at-startup-does.md) ends failed never finishes starting: every pass takes the startup wait and does nothing else, its queue being emptied by the failing startup rather than by a pass.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
- [Abandoning work outright](abandoning-work-outright.md)

---

Created 2026-10-12 04:21 UTC · Last modified 2026-10-12 06:40 UTC
