---
row: P96-02
baseline: 49aa659
created: 2026-11-14 01:30 UTC
modified: 2026-11-14 01:30 UTC
evidence:
  - claim: "A rollback stands inside a guard whose catch names any failure, and lets the rollback's own failure go no further"
    source: "`event_spine.py` 901-902 into 903, which raises nothing on"
  - claim: "A commit stands inside its own guard, which rolls back and raises the commit's failure on"
    source: "`event_spine.py` 921-922 into 923, then 924, then 926"
  - claim: "The rollback a failed commit asks for is the same guarded one, so its failure cannot hide the commit's"
    source: "`event_spine.py` 924, into 901-904"
---
# How the spine closes a write

Every write to the spine ends one of two ways, and the difference between them is what happens to a failure.

## The rollback

It stands inside a guard whose catch names any failure. A rollback that itself fails goes no further: the guard raises nothing on, and the caller carries on unaware, which is all a caller could do about it anyway.

## The commit

It stands inside its own guard. A commit that fails rolls back and raises on, so the caller sees the cause rather than a rollback's symptom.

## Why one raises and the other does not

A failed commit is something the caller must know: the write did not happen, and whatever was supposed to follow it should stop. A failed rollback is already past that point — the write did not happen either way, and the connection is in whatever state it is in.

So the pair is asymmetric on purpose. The rollback a failed commit asks for is the same guarded one, which is what keeps a rollback's failure from standing in for the commit's.

## What it costs

A rollback that fails leaves the connection in a state nothing here corrects, and nothing above this is told. The log is the whole of the trace, so a later write failing strangely has its explanation only there.

## Related

- [What opening the spine does to its schema](what-opening-the-spine-does-to-its-schema.md)
- [What the spine's four readings insist on](what-the-spines-four-readings-insist-on.md)
