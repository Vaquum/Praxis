---
row: P95-01
baseline: 49aa659
created: 2026-11-09 07:34 UTC
modified: 2026-11-09 07:34 UTC
evidence:
  - claim: "Each of the two seal columns is added only where it is absent, so a file made with them already skips the altering"
    source: "`event_spine.py` 586 into 587-588, and 589 into 590-591"
  - claim: "The two identity facts are then written, whatever the file held before"
    source: "`event_spine.py` 593-594, and 595-596"
  - claim: "Nothing in the routine fills a seal in for a record that lacks one"
    source: "`event_spine.py` 586-596, the whole of it"
  - claim: "The later migration makes the old deduplication table before it reads anything"
    source: "`event_spine.py` 621-622, ahead of 624"
  - claim: "A legacy row with no matching fill refuses the whole migration, naming how many there were"
    source: "`event_spine.py` 627 into 628-633"
  - claim: "A file spanning more than one symbol refuses too, naming how many"
    source: "`event_spine.py` 635 into 636-640"
  - claim: "The one symbol found is recorded, and an empty one is recorded where none was found at all"
    source: "`event_spine.py` 642, then 643-644"
---
# What the first migrations add and prove

Two migrations bring an older file forward: one adds the columns a seal needs, and one proves what the old deduplication table holds.

## The columns

Each of the two seal columns is added only where it is absent, so a file made with them already skips the altering. The two identity facts are then written, whatever the file held before.

Nothing in the routine fills a seal in for a record that lacks one. So records written before the seals existed keep none, and the chain begins at the first record that has one.

## What the next migration refuses

It makes the old deduplication table before it reads anything, so what follows reads a table that is certainly there.

Then two refusals. A legacy row with no matching fill refuses the whole migration, naming how many there were. A file spanning more than one symbol refuses too, naming how many.

Both refusals ask for the work to be done elsewhere rather than guessing. A row it cannot attribute and a file it cannot attribute to one symbol are both things a migration could paper over, and this one declines to.

## What it records

The one symbol found. Where none was found at all, an empty one is recorded — so the fact is written either way, and [what reads it later](what-the-last-migration-drops.md) can tell nothing-found from not-yet-looked.

## Related

- [What the last migration drops](what-the-last-migration-drops.md)
- [What opening the spine does to its schema](what-opening-the-spine-does-to-its-schema.md)
