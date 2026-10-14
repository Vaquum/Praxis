---
row: P4-49
baseline: 49aa659
created: 2026-10-14 07:40 UTC
modified: 2026-10-14 07:40 UTC
evidence:
  - claim: "A run frozen for protection or being wound up is turned away, as is one whose ending is still settling"
    source: "`execution_manager.py` 10083-10091 and 10093-10099"
  - claim: "A run with nothing left to buy is a no-op"
    source: "`execution_manager.py` 10105-10109"
  - claim: "A new count that does not pass the slices already sent is refused"
    source: "`execution_manager.py` 10111-10119"
  - claim: "The parts already sent are kept and only the rest are planned again, and only where the count changes"
    source: "`execution_manager.py` 10135 into 10149-10150"
  - claim: "A change to the gap alone leaves every amount standing and moves the timer"
    source: "`execution_manager.py` 10135 against 10152-10154"
  - claim: "A planning failure leaves the schedule as it was"
    source: "`execution_manager.py` 10141-10147"
  - claim: "The next slice is set a full gap from now rather than from the last one"
    source: "`execution_manager.py` 10152-10154, taken at 10171"
  - claim: "The new schedule is written down before the timer is moved"
    source: "`execution_manager.py` 10156-10168 before 10171"
  - claim: "A freeze from a failed slice is lifted by the change"
    source: "`execution_manager.py` 10170"
---
# How a schedule change is carried out

Changing [a run fed out over time](work-fed-out-over-time.md) alters how many parts are left, how long between them, or both. The parts already sent always stand; whether the rest are planned again turns on which of the two changed.

## Turned away

A run frozen because [protection was lost](when-protection-is-lost.md), and one being wound up, are both refused — the change is logged and returned, not raised. So is one whose ending is already settling.

A run with nothing left to buy is answered as a no-op.

A new count of parts that does not pass the number already sent is refused as well. Lowering the count to stop a run is not a way to stop one; abandoning it is.

## Planned again only for a new count

Changing the count of parts spreads the remainder over the parts that are left, keeping the amounts already sent untouched. Where that planning fails, the old schedule stays exactly as it was.

Changing only the gap plans nothing: the amounts stand as they were, a weighted run's curve included, and the timer alone moves.

## The gap starts again

The next part is set a full gap from the moment of the change, not from the last part sent — so shortening the gap can still make the next part wait longer than the old schedule would have.

The new schedule is written down before the timer is moved, so a restart resumes on the schedule the change asked for.

## One hold it lifts

A run frozen because a slice failed comes out of that freeze: the change puts it back to open. The two holds that refused the change outright are untouched, since it never gets that far.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What each change insists on](what-each-change-insists-on.md)
- [What a restart puts back](what-a-restart-puts-back.md)

---

Created 2026-10-14 07:40 UTC · Last modified 2026-10-14 07:40 UTC
