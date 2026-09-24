---
row: P1-08
baseline: 49aa659
created: 2026-09-23 08:19 UTC
modified: 2026-09-24 08:02 UTC
evidence:
  - claim: "The line is emptied every pass once the account has started"
    source: "`execution_manager.py` 3910-3911, unless a still-starting account stops at 3903-3905"
  - claim: "A cancellation taken from it is carried out"
    source: "`execution_manager.py` 3940-3941"
  - claim: "A change taken from it is carried out too"
    source: "`execution_manager.py` 3938-3939"
  - claim: "A held or failed account puts each change back instead"
    source: "`execution_manager.py` 3913-3920, returned at 3953-3954"
  - claim: "Holding is a flag an outside caller sets, not one the worker raises"
    source: "set at `execution_manager.py` 3286"
  - claim: "The worker reads it when deciding whether to defer a change"
    source: "`execution_manager.py` 3914"
  - claim: "It reads it again before taking new work"
    source: "`execution_manager.py` 3969"
  - claim: "The line is emptied before any submitted work is taken"
    source: "`execution_manager.py` 3910-3911 ahead of 3980-3984"
  - claim: "A still-starting account reaches neither"
    source: "`execution_manager.py` 3903-3905"
---
# The priority line

Cancellations and changes wait together in one line, which [the account worker](how-waiting-work-is-drained.md) empties on every pass, once the account has finished starting up, before it takes any [submitted work](how-an-order-is-placed.md).

## What happens to each

A [cancellation](how-a-trade-is-cancelled.md) is carried out. So is a change, unless the account is on hold or has failed: each change is then put back for a later pass, while cancellations still run.

Being on hold is a flag set from outside. The worker only reads it.

## What the ordering means

A cancellation already in the line is carried out before the next piece of submitted work starts. One arriving after the line is emptied waits for the next pass.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [Cancellation](how-a-trade-is-cancelled.md)
