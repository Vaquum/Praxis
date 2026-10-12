---
row: P1-11
baseline: 49aa659
created: 2026-10-12 04:21 UTC
modified: 2026-10-12 04:21 UTC
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
---
# When an account is reconciling or poisoned

An account being brought back into step with the venue is **reconciling**, and one carrying a fault that needs a restart is **poisoned**. [A pass](how-waiting-work-is-drained.md) under either takes no [submitted work](how-an-order-is-placed.md), and ends on the same wait an empty queue brings.

## What the pass still does

It takes the waiting venue news, empties [the priority line](the-priority-line.md) and retries a [cancellation](how-a-trade-is-cancelled.md) that is due. Changes put back in the line are left until the next pass.

Poisoned, the pass then empties its ordinary queue, refusing each request in it. Reconciling, that queue is left as it stands, so the requests in it go on waiting for the account to come back.

## What the emptying leaves

A request whose refusal report cannot be built is dropped with nothing reported at all. Where the worker is cancelled partway through the emptying, it stops where it was and whatever is still queued stays queued.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
- [Abandoning work outright](abandoning-work-outright.md)

---

Created 2026-10-12 04:21 UTC · Last modified 2026-10-12 04:21 UTC
