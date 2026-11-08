---
row: N56-01
baseline: 49aa659
created: 2026-11-12 13:30 UTC
modified: 2026-11-12 14:00 UTC
evidence:
  - claim: "The default hooks are built as the duplicate window first and the references second"
    source: "`nexus/core/validator/intake_stage.py` 63-72"
  - claim: "A rate cap, where one is resolved, is put in front of both"
    source: "`nexus/core/validator/intake_stage.py` 77-78, returned at 80"
  - claim: "The cap passed to the building stands in place of the one the configuration carries"
    source: "`nexus/core/validator/intake_stage.py` 74-76"
  - claim: "The rate hook refuses a cap that is not a whole number, with a true-or-false refused outright, and one at or below nought"
    source: "`nexus/core/validator/intake_stage.py` 89-91, or 93-95"
  - claim: "The duplicate hook refuses its window the same way"
    source: "`nexus/core/validator/intake_stage.py` 132-137, or 139-141"
  - claim: "Each hook answers nothing at all for anything but an entry"
    source: "`nexus/core/validator/intake_stage.py` 102-103, or 150-151"
  - claim: "A check on the account's mode runs before any hook does"
    source: "`nexus/core/validator/intake_stage.py` 442-446"
---
# The order the intake hooks stand in

The hooks an entry meets are built in an order, and the order decides which refusal an entry that breaks two rules is given.

## What comes before all of them

A check on the account's mode. It runs before the first hook, so what a halted or restricted account is told has nothing to do with the order below.

## The order

The window that turns a repeated entry away is built first, and the check on references second.

A cap on how fast entries may go in is then put in front of both. So where a cap is set and an entry is the one that reaches it, that entry is turned away for the rate before anything asks whether it is a repeat.

Where no cap is resolved, the window is first and the references second.

## Where the cap comes from

The cap handed to the building stands in place of the one the account's configuration carries. Where neither gives one, no rate hook is built at all.

## What each refuses before it runs

The rate hook refuses a cap that is not a whole number — a true-or-false refused outright by a test of its own — and one at or below nought. The duplicate hook refuses its window the same way.

Both refusals happen as the hook is built, so a bad figure stops the stage being assembled rather than turning an entry away.

## What they pass over

Each answers nothing at all for anything but an entry. So an exit, a change and an abort reach [the references hook](what-intake-asks-of-an-exit.md) with neither of the other two having looked at them — unless the mode check turned them away first.

## Related

- [The cap on how fast entries may go in](the-cap-on-how-fast-entries-may-go-in.md)
- [The window that turns a repeated entry away](the-window-that-turns-a-repeated-entry-away.md)
- [What intake asks of an exit](what-intake-asks-of-an-exit.md)
