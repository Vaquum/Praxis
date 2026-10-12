---
row: P1-13
baseline: 49aa659
created: 2026-10-12 14:30 UTC
modified: 2026-10-12 15:27 UTC
evidence:
  - claim: "A change is deferred for as long as the hold lasts, going back on the line each pass"
    source: "`execution_manager.py` 3913-3920 and 3953-3954"
  - claim: "A reconciling hold is set and unset from outside, a failed pass leaving it on until a later one finishes"
    source: "`execution_manager.py` 3286 from `trading.py` 1406-1407, left on at 1471 or 1480, rather than taken off at 1487-1489 as an undisturbed pass does"
  - claim: "A poisoned hold is only ever set"
    source: "`execution_manager.py` 3254, 3773, 4026 and 7011, started at 601"
  - claim: "A change taken off the line is lost only where the pass is cancelled before the putting back"
    source: "`execution_manager.py` 3920 and 3953-3954, or the raise at 3942-3943 leaving ahead of it, the waits at 3960 and 3970 coming after"
  - claim: "A change the hold let through does nothing where its order went terminal while it waited"
    source: "`execution_manager.py` 8622-8624, the cancellations still run at 3941 marking one terminal at 10582"
  - claim: "A worker still starting empties no line, so a change queued then is not reached at all"
    source: "`execution_manager.py` 3903-3905 ahead of 3910, still queued from 3074"
---
# A change waiting out a hold

A [change to work already sent](changing-work-already-sent.md) that reaches [the priority line](the-priority-line.md) while the account is [reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md) is put back rather than carried out. It comes up again on the next pass, and goes back again, for as long as the hold lasts.

## How long that is

A reconciling hold is put on and taken off from outside the worker. A reconcile pass that finishes undisturbed takes it off; one that fails, or one whose backfill comes back short, leaves it on until a later pass finishes. A change waiting on that hold is taken up again on the first pass that empties the line with the hold off — and does nothing where the order it meant to change has gone terminal in the meantime, which a [cancellation](how-a-trade-is-cancelled.md) on the same line can do while the change is still being put back. A worker still starting, or one whose loop has ended, empties no line at all, so the change sits there untouched.

A poisoned hold is only ever put on. Nothing takes it off for the life of the host, so a change waiting on that one waits until the host is restarted — and the change is not written down anywhere, so the restart does not find it.

## What loses it

Putting the changes back is the last of the line's own work. A pass cancelled while it is still working through the line has already taken them off and has not put them back, so those changes are gone — neither carried out nor reported.

## Related

- [When an account is reconciling or poisoned](when-an-account-is-reconciling-or-poisoned.md)
- [Changing work already sent](changing-work-already-sent.md)
- [The priority line](the-priority-line.md)

---

Created 2026-10-12 14:30 UTC · Last modified 2026-10-12 15:27 UTC
