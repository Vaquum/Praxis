---
row: S-01
baseline: 49aa659
created: 2026-10-14 14:00 UTC
modified: 2026-10-14 15:30 UTC
---
# Cancelling a trade

The route a cancellation takes from the moment a caller asks for it to the moment that caller is told what happened. Each step hands off to the article that owns it: this page sequences them and asserts nothing of its own.

**Starts from** a caller asking Praxis to stop a request it has already submitted.

**Ends** with the request reported cancelled, reported expired, or — on several of the forks below — with no report reaching the caller.

## Before anything is queued

1. The host refuses outright while it is shutting down, before it has been started, and while the named account is not ready — so the route below begins only on a running account — [What the host refuses first](../atoms/what-the-host-refuses-first.md).

2. The asking is then checked: an unknown account or request, one belonging to another account, an account whose start failed, and a worker that has exited are each refused here — [Cancellation](../atoms/how-a-trade-is-cancelled.md).

3. A request already finished is answered as doing nothing, before it is queued at all — [Cancellation](../atoms/how-a-trade-is-cancelled.md).

4. Anything still live joins [the priority line](../atoms/the-priority-line.md).

5. [The account's worker](../atoms/how-waiting-work-is-drained.md) takes the venue's own news first, then that line, and only then its ordinary queue — [The priority line](../atoms/the-priority-line.md).

## One arm of three, never two

6. A request that finished while it waited is answered as doing nothing — [Cancellation](../atoms/how-a-trade-is-cancelled.md).

7. **Arm one — work being fed out.** A run or a ladder the account is working is wound up, and nothing below applies to it: [winding up](../atoms/abandoning-work-outright.md) cancels its children and waits for them rather than answering at once — [Work fed out over time](../atoms/work-fed-out-over-time.md), [Work already under way](../atoms/work-already-under-way.md).

8. **Arm two — no order was ever sent.** The request is marked, and the mark is read when its turn to start comes: it is then dropped unsent and reported cancelled with nothing filled — [Cancellation](../atoms/how-a-trade-is-cancelled.md). A ladder marked before its first rung is the case whose report will not build, and the caller hears a rejection only after the next start — [Cancellation](../atoms/how-a-trade-is-cancelled.md), [What startup does with orphaned work](../atoms/what-startup-does-with-orphaned-work.md). A run or a ladder found past its deadline is reported expired instead — [Deadlines](../atoms/deadlines.md). An account poisoned meanwhile refuses the marked work outright when its turn comes, so the mark is not always what answers it — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).

9. **Arm three — an order is resting.** The venue is asked to cancel it — [What a venue must be able to do](../atoms/what-a-venue-must-be-able-to-do.md). Unlike sending an order, cancelling one is repeatable, so a failure the adapter counts as temporary is tried again before it is reported at all — [When Praxis retries a venue call](../atoms/when-praxis-retries-a-venue-call.md).

## What that one call comes back as

10. **The venue cancels it, or has no such order.** Both count as confirmed, and a cancellation is written down — [Cancellation](../atoms/how-a-trade-is-cancelled.md), [What a refusal says](../atoms/what-a-refusal-says.md).

11. **The venue refuses it.** The order's record is left untouched and the reason carries the failure — [Cancellation](../atoms/how-a-trade-is-cancelled.md). The request is still reported cancelled, with the order still resting there — [Cancellation](../atoms/how-a-trade-is-cancelled.md).

12. **The reply cannot be read.** A missing id, or a status the adapter has no name for, leaves this route before anything is written: the worker logs it and no report is built — [A reply that cannot be read](../atoms/a-reply-that-cannot-be-read.md), [When an update fails](../atoms/when-an-update-fails.md).

## What the caller is told

13. On the two results that stay on the route, whatever had already been counted as filled is reported with the cancellation, and no fresh count is fetched — [Cancellation](../atoms/how-a-trade-is-cancelled.md), [The figures an outcome carries](../atoms/the-figures-an-outcome-carries.md).

14. A report that will not build leaves the caller with nothing, after the venue was asked — [The figures an outcome carries](../atoms/the-figures-an-outcome-carries.md), [Outcomes that never come back](../atoms/outcomes-that-never-come-back.md).

15. Otherwise the report is handed over, and handing it over can fail in its own right — [How an outcome crosses back](../atoms/how-an-outcome-crosses-back.md), [How an outcome is delivered](../atoms/how-an-outcome-is-delivered.md).

## Where this route is not taken

- A host stopping sends its own abandonment for every command in flight, which joins the same line and takes the same three arms from step 6 on. What it skips is the caller-facing refusals of step 1 — [Where an abandonment lands](../atoms/where-an-abandonment-lands.md), [What becomes of work still open](../atoms/what-becomes-of-work-still-open.md).
- An order found past its deadline is cancelled by a route that settles its report first — [The expiry cancel](../atoms/the-expiry-cancel.md).
- A price change cancels the resting order as one step of replacing it — [How a price change is carried out](../atoms/how-a-price-change-is-carried-out.md).
- A lost protection closes the position rather than cancelling the request — [When protection is lost](../atoms/when-protection-is-lost.md).

---

Created 2026-10-14 14:00 UTC · Last modified 2026-10-14 15:30 UTC
