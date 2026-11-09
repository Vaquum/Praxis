---
row: P94-01
baseline: 49aa659
created: 2026-11-09 07:30 UTC
modified: 2026-11-09 07:30 UTC
evidence:
  - claim: "The version the file carries is read first, and one newer than the build knows refuses to open at all"
    source: "`event_spine.py` 493, then 494 into 495-499"
  - claim: "A file whose version already carries the chain identity has that identity demanded before any table is touched"
    source: "`event_spine.py` 502 into 503, ahead of 505"
  - claim: "Six tables and indexes are then made, each in a statement of its own"
    source: "`event_spine.py` 505-506, and 507-508, and 509-510, and 511-512, and 513-514, and 515-516"
  - claim: "A file older than the identity version is migrated and only then has the identity demanded"
    source: "`event_spine.py` 518 into 519, then 520"
  - claim: "Two further migrations each run only where the version stands below their own"
    source: "`event_spine.py` 522 into 523, or 525 into 526"
  - claim: "The version is stamped only where it stood below the build's, so an equal version writes nothing"
    source: "`event_spine.py` 528 into 529-530"
  - claim: "All of it is committed at the end, and any failure rolls back and raises on"
    source: "`event_spine.py` 501 into 532, against 533 into 534, then 536"
---
# What opening the spine does to its schema

Opening the spine's file reads the version it carries, brings it up to the build's, and does the whole of that in one go.

## The version that refuses

Read first. A version newer than the build knows refuses to open at all, so a file written by a later build is left alone rather than read with the wrong idea of its shape.

## Where the identity is demanded

A file whose version already carries the chain identity has that identity demanded before any table is touched. A file older than that version is migrated first and has the identity demanded after.

So the demand sits on both sides of the migration, and which side depends on the version the file arrived with.

## The making and the migrating

Six tables and indexes are made, each in a statement of its own. Two further migrations each run only where the version stands below their own, so a file is carried forward through whichever steps it has yet to take.

## The stamp

The version is stamped only where it stood below the build's. An equal version writes nothing at all, so opening an up-to-date file leaves the version untouched.

## One go

All of it is committed at the end. Any failure rolls back and raises on, so a half-migrated file is never left behind by a failure the rollback could undo.

## Related

- [What the spine asks of its own identity](what-the-spine-asks-of-its-own-identity.md)
