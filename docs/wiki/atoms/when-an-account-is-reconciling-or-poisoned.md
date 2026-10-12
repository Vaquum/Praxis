---
row: P1-11
baseline: 49aa659
created: 2026-10-12 04:21 UTC
modified: 2026-10-12 11:35 UTC
evidence:
  - claim: "A reconciling or poisoned account takes no submitted work, and its pass ends on the wait"
    source: "`execution_manager.py` 3969-3971"
  - claim: "All of that is below the startup wait, so no pass reaches it while the account is still starting"
    source: "`execution_manager.py` 3903-3905 ahead of 3907, registered as starting at 831-835 from `trading.py` 522, cleared only at `execution_manager.py` 3672 from `trading.py` 607"
  - claim: "Starting against a live venue sets the account reconciling before it waits on the backfill, so passes taken during that wait are both"
    source: "`trading.py` 590-592 rather than 594-596, into 1455 and 1406-1407, awaited at 1459, the flag off again at 1487-1489"
  - claim: "The pass still takes venue news, empties the priority line and retries a due cancellation"
    source: "`execution_manager.py` 3907 and 3910, with the retry at 3960"
  - claim: "A change is deferred for as long as the hold lasts, going back on the line each pass"
    source: "`execution_manager.py` 3913-3920 and 3953-3954"
  - claim: "A reconciling hold is set and unset from outside, a failed pass leaving it on until a later one finishes"
    source: "`execution_manager.py` 3286 from `trading.py` 1406-1407, left on at 1471 or 1480, rather than taken off at 1487-1489 as an undisturbed pass does"
  - claim: "A poisoned hold is only ever set"
    source: "`execution_manager.py` 3254, 3773, 4026 and 7011, started at 601"
  - claim: "Poisoning while the worker runs comes from projecting an admitted event or a venue update that failed"
    source: "`execution_manager.py` 3249-3254 reached from 3809, or 3768-3780 reached from 3736, handed back at 3830-3832"
  - claim: "A change taken off the line is lost only where the pass is cancelled before the putting back"
    source: "`execution_manager.py` 3920 and 3953-3954, or the raise at 3942-3943 leaving ahead of it, the waits at 3960 and 3970 coming after"
  - claim: "Poisoned, the ordinary queue is emptied and each request in it refused"
    source: "`execution_manager.py` 3962-3967, body at 6988-6999"
  - claim: "A request whose refusal report cannot be built is dropped unreported"
    source: "`execution_manager.py` 7003-7019"
  - claim: "A cancelled worker stops the emptying and leaves the rest queued"
    source: "`execution_manager.py` 7000-7002"
---
# When an account is reconciling or poisoned

An account being brought back into step with the venue is **reconciling**, and one carrying a fault that needs a restart is **poisoned**. [A pass](how-waiting-work-is-drained.md) past startup under either takes no [submitted work](how-an-order-is-placed.md), and ends on the same wait an empty queue brings.

## What the pass still does

It takes the waiting venue news, empties [the priority line](the-priority-line.md) and retries a [cancellation](how-a-trade-is-cancelled.md) that is due. A change on that line is put back rather than carried out, coming up again next pass, so it waits as long as the hold. A reconciling hold lifts once the account is in step, a failed reconcile leaving it on until a later one finishes; a poisoned hold never lifts, so a change there waits for the host's life. Putting them back is the last of the line's own work, so a change is lost only where the pass is cancelled first.

Poisoned, the pass then empties its ordinary queue, refusing each request. Reconciling, that queue stands as it is, its requests waiting for the account to come back.

## What the emptying leaves

A request whose refusal cannot be reported is dropped. A worker cancelled partway through stops there, and what is still queued stays queued.

## Where there is no such pass

An account is poisoned while its worker runs when projecting fails, whether an admitted event or a venue update.

All of it sits below the startup wait, so a pass still starting does none of it. Starting against a live venue sets the account reconciling before waiting on its backfill, so passes taken then are both at once. The two then part: startup can finish with the hold still on, and a boot left not ready keeps taking that wait however the backfill ended.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
- [How a worker stops](how-a-worker-stops.md)
- [Abandoning work outright](abandoning-work-outright.md)

---

Created 2026-10-12 04:21 UTC · Last modified 2026-10-12 11:35 UTC
