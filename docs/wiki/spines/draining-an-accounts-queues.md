---
row: S-02
baseline: 49aa659
created: 2026-10-15 08:10 UTC
modified: 2026-10-23 09:00 UTC
evidence:
  - claim: "A starting account's pass does nothing and waits"
    source: "`execution_manager.py` 3903-3905"
  - claim: "The venue's news is taken before the priority line, and that before the ordinary queue"
    source: "`execution_manager.py` 3907 before 3910 before 3984"
  - claim: "The priority line is emptied in one loop, and a held change is put back only past it"
    source: "`execution_manager.py` 3910-3929 against 3954"
  - claim: "An ordinary raise inside that loop is logged and the loop carries on"
    source: "`execution_manager.py` 3944-3951"
  - claim: "A pass called off is passed straight on instead of logged"
    source: "`execution_manager.py` 3942-3943"
  - claim: "Cancellations left part done are driven before anything new starts"
    source: "`execution_manager.py` 3960 before 3973"
  - claim: "A poisoned account refuses what is queued, and either hold ends the pass"
    source: "`execution_manager.py` 3962-3967 and 3969-3971"
  - claim: "Work already running is moved along, and protection put up, before a new request is taken"
    source: "`execution_manager.py` 3973-3974 before 3984"
  - claim: "Protection goes up only for a bracket whose opening order has ended with something filled"
    source: "`execution_manager.py` 4743-4744 and 4748-4749"
  - claim: "A scan the squaring tick asked for runs on the worker, after that and before a new request"
    source: "`execution_manager.py` 3976-3978, its jobs at 7290-7300"
  - claim: "At most one request is taken off the ordinary queue, an empty one ending the pass"
    source: "`execution_manager.py` 3980-3982 against 3984"
  - claim: "The deadline is weighed for a run and a ladder, and starting is the other branch"
    source: "`execution_manager.py` 3994-3998 and 4004-4007"
---
# Draining an account's queues

One pass of [an account's worker](../atoms/how-waiting-work-is-drained.md), from what it looks at first to what it does when there is nothing left. Each sentence hands off to the article owning the behaviour it names, and the order they happen in is proved below rather than borrowed.

**Starts from** a worker running on an account, with work possibly waiting in either of its queues.

**Ends** with the pass going round again, having started at most one piece of new work — or with the account poisoned and its loop over.

## Before the lines a caller writes to

1. A worker whose account is still starting does nothing at all: it waits a tenth of a second and begins again — [How waiting work is drained](../atoms/how-waiting-work-is-drained.md).

2. The venue's own news is taken first, ahead of anything a caller asked for — [How waiting work is drained](../atoms/how-waiting-work-is-drained.md).

## The priority line, in one loop

3. [The priority line](../atoms/the-priority-line.md) is then emptied completely, before any new work is begun.

4. Each thing on it is carried out as it comes off: a cancellation takes [its own route](cancelling-a-trade.md) — [Cancellation](../atoms/how-a-trade-is-cancelled.md) — and a change takes [the route for changes](changing-work-already-sent.md) — [Changing work already sent](../atoms/changing-work-already-sent.md).

5. A change met while the account is catching up with the venue or poisoned is set aside as the loop runs, and put back only once the loop is done — [A change waiting out a hold](../atoms/a-change-waiting-out-a-hold.md). One set aside on a pass that is then cancelled is lost with it — [A change waiting out a hold](../atoms/a-change-waiting-out-a-hold.md).

6. One that raises is logged and the loop carries on, leaving that instruction answered by nothing — [When an update fails](../atoms/when-an-update-fails.md). A pass being called off is passed straight on instead, and ends the loop — [How a worker stops](../atoms/how-a-worker-stops.md).

## Work already under way

7. A cancellation whose children never finished is driven again, where its retry is due or its deadline has come — [Work already under way](../atoms/work-already-under-way.md).

8. A poisoned account then refuses everything waiting in its ordinary queue — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

9. An account poisoned or catching up goes no further on this pass: it waits for something to happen and begins again — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

10. Otherwise work already running is moved along: a slice now due is sent, a run out of time is wound up, and one with nothing left to send is finished — [Work fed out over time](../atoms/work-fed-out-over-time.md), [Deadlines](../atoms/deadlines.md).

11. Protection is then put up for a bracket whose opening order has ended with something filled — [Protection](../atoms/protection.md).

12. A scan the squaring tick asked for runs here rather than on that tick, and it carries more than protection: drains, ladder and ordinary changes, and failed closes — [Work already under way](../atoms/work-already-under-way.md). Its protection watches are the part that can take a pair as lost — [When protection is lost](../atoms/when-protection-is-lost.md).

## At most one new thing

13. With the ordinary queue empty, the pass waits up to a tenth of a second and begins again — [How waiting work is drained](../atoms/how-waiting-work-is-drained.md).

14. Otherwise exactly one request is taken off it, and the pass goes straight round afterwards rather than waiting — [How waiting work is drained](../atoms/how-waiting-work-is-drained.md).

15. A run or a ladder found past its deadline is reported expired rather than started — [Deadlines](../atoms/deadlines.md). Anything else, and anything not past it, is started by the way of working it named: a plain order is [placed](../atoms/how-an-order-is-placed.md), a run begins [feeding out](../atoms/work-fed-out-over-time.md), a ladder [rests its rungs](../atoms/orders-at-several-prices.md), a part-shown order [shows less than it is](../atoms/part-shown-orders.md), and a bracket [sends its opening order](../atoms/protection.md).

16. Starting it can raise, which is logged against that one request — [When an update fails](../atoms/when-an-update-fails.md). A failure escaping the pass itself poisons the account, refuses what is queued, and ends the loop — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

## Where this route is not taken

- A worker cancelled mid-pass leaves what is still queued queued, and only what it had taken off is lost — [How a worker stops](../atoms/how-a-worker-stops.md).
- A worker that has already exited takes nothing more — [How a worker stops](../atoms/how-a-worker-stops.md).

---

Created 2026-10-15 08:10 UTC · Last modified 2026-10-23 09:00 UTC
