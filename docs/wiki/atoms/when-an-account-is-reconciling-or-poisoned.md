---
row: P1-11
baseline: 49aa659
created: 2026-10-12 04:21 UTC
modified: 2026-10-12 14:26 UTC
evidence:
  - claim: "A reconciling or poisoned account takes no submitted work, and its pass ends on the wait"
    source: "`execution_manager.py` 3969-3971"
  - claim: "All of that is below the startup wait, so no pass reaches it while the account is still starting"
    source: "`execution_manager.py` 3903-3905 ahead of 3907, registered as starting at 831-835 from `trading.py` 522, cleared only at `execution_manager.py` 3672 from `trading.py` 607"
  - claim: "Starting against a live venue sets the account reconciling before it waits on the backfill, so passes taken during that wait are both"
    source: "`trading.py` 590-592 rather than 594-596, into 1455 and 1406-1407, awaited at 1459, the flag off again at 1487-1489"
  - claim: "The pass still takes venue news, empties the priority line and retries a due cancellation"
    source: "`execution_manager.py` 3907 and 3910, with the retry at 3960"
  - claim: "Poisoning while the worker runs comes from projecting an admitted event or a venue update that failed"
    source: "`execution_manager.py` 3249-3254 reached from 3809, or 3768-3780 reached from 3736, handed back at 3830-3832"
  - claim: "Poisoned, the ordinary queue is emptied and each request in it refused"
    source: "`execution_manager.py` 3962-3967, body at 6988-6999"
  - claim: "A request whose refusal report cannot be built reaches the decision side with nothing, though the log line names it"
    source: "`execution_manager.py` 7003-7019, the log at 7012-7018"
  - claim: "A cancelled worker stops the emptying and leaves the rest queued"
    source: "`execution_manager.py` 7000-7002"
---
# When an account is reconciling or poisoned

An account being brought back into step with the venue is **reconciling**, and one carrying a fault that needs a restart is **poisoned**. [A pass](how-waiting-work-is-drained.md) past startup under either takes no [submitted work](how-an-order-is-placed.md), and ends on the same wait an empty queue brings.

## What the pass still does

It takes the venue news, empties [the priority line](the-priority-line.md) and retries a due [cancellation](how-a-trade-is-cancelled.md). A change on that line is put back rather than carried out, and [waits out the hold](a-change-waiting-out-a-hold.md).

Poisoned, the pass then empties its ordinary queue, refusing each request. Reconciling, that queue stands as it is, its requests waiting for the account to come back.

## What the emptying leaves

A refusal that cannot be reported leaves the decision side with nothing, the log line naming it. A worker cancelled partway stops there, what is still queued staying queued.

## Where there is no such pass

An account is poisoned while its worker runs when projecting fails, whether an admitted event or a venue update.

All of it sits below the startup wait, so a pass still starting does none. Starting against a live venue sets the account reconciling before waiting on its backfill, so passes taken then are both. The two need not end together: startup can finish with the hold on, and a boot left not ready keeps that wait for good, its hold standing or lifted as its own reconcile ended, with nothing reconnecting to change either.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
- [A change waiting out a hold](a-change-waiting-out-a-hold.md)
- [How a worker stops](how-a-worker-stops.md)
- [Abandoning work outright](abandoning-work-outright.md)

---

Created 2026-10-12 04:21 UTC · Last modified 2026-10-12 14:26 UTC
