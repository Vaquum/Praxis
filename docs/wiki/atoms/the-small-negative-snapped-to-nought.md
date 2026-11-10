---
row: N63-06
baseline: 49aa659
created: 2026-11-08 19:26 UTC
modified: 2026-11-08 19:26 UTC
evidence:
  - claim: "Reading a capital record passes five of its six figures, and every per-strategy figure, through a snap that turns a small negative into nought"
    source: "`nexus/infrastructure/wal_codec.py` 199-203, and 205, with the pool read at 198 untouched"
  - claim: "The snap turns a figure into nought where it stands below nought and no further below than the tolerance, and hands any other figure it can compare back as it is"
    source: "`nexus/infrastructure/wal_codec.py` 52-53, then 55"
  - claim: "A figure that is no number cannot be compared there, so it raises inside the snap"
    source: "`nexus/infrastructure/wal_codec.py` 52, comparing the figure twice"
  - claim: "The tolerance is declared in the capital record's own module, and the record applies it nowhere"
    source: "`nexus/infrastructure/wal_codec.py` 16, against `nexus/core/domain/capital_state.py` 56, and 90"
  - claim: "A negative beyond the tolerance is handed through, and the capital record refuses any figure below nought as it is built"
    source: "`nexus/infrastructure/wal_codec.py` 55 into the build at 197"
  - claim: "The writer writes what the record holds, so a residue in the record goes into the snapshot and is snapped on each reading rather than once"
    source: "`nexus/infrastructure/wal_codec.py` 173-182"
---
# The small negative snapped to nought

Reading the record of an account's money passes most of its figures through a snap, which exists so that a reading cannot be refused for a figure too small to mean anything.

## What the snap does

A figure standing below nought, and no further below than a tolerance, comes back as nought. Any other figure it can compare comes back as it was, and a figure that is no number cannot be compared at all, so it raises inside the snap.

The tolerance is declared in the capital record's own module. The record applies it nowhere — its own checks refuse any figure below nought — so the snap is the only thing in either file that treats a small negative as nothing.

## What goes through it

Five of the capital record's six figures, and every per-strategy figure.

The pool is the one left alone — it is read straight, so a pool standing below nought reaches the record as it was written.

## Why it is there

The capital record refuses any figure below nought as it is built. Arithmetic that reserves and releases money can leave a residue below nought too small to be a quantity, and a snapshot holding one would be refused on every attempt to read it.

A negative beyond the tolerance is handed through untouched, so the record still refuses a figure that is wrong rather than merely tiny.

## Where the residue lives

The writer writes what the record holds. A residue therefore goes into the snapshot and is snapped on each reading, rather than cleared once.

## Related

- [The figures a risk record falls back to](the-figures-a-risk-record-falls-back-to.md)
- [What a malformed saved record is refused as](what-a-malformed-saved-record-is-refused-as.md)
