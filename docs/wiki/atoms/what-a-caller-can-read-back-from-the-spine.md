---
row: P97-03
baseline: 49aa659
created: 2026-11-14 02:00 UTC
modified: 2026-11-14 02:00 UTC
evidence:
  - claim: "A read takes every row of an epoch past a given sequence and rebuilds each into an event beside its own number"
    source: "`event_spine.py` 1214-1215, then 1216"
  - claim: "The whole answer is gathered before any of it is handed back"
    source: "`event_spine.py` 1215, ahead of 1216"
  - claim: "A read of the highest sequence answers that number, or nothing where the epoch holds no rows"
    source: "`event_spine.py` 1230-1231, then 1232"
  - claim: "Writing the reconciliation cursor takes the same lock an append takes"
    source: "`event_spine.py` 1347"
  - claim: "The cursor is written as one statement that inserts or replaces, and committed under that lock"
    source: "`event_spine.py` 1348-1359, then 1360"
  - claim: "Each row of the scan over stored fills is taken one at a time rather than gathered"
    source: "`event_spine.py` 766"
---
# What a caller can read back from the spine

A caller can read an epoch's events, ask how far it got, and move the reconciliation cursor. The three differ in how much they hold at once.

## Reading an epoch

Every row past a given sequence is taken and rebuilt into an event beside its own number. The whole answer is gathered before any of it is handed back, so a caller reading a long epoch waits for all of it and holds all of it.

The scan the migrations use takes its rows one at a time instead. So the spine has both shapes in it, and the caller-facing read is the one that gathers.

## Asking how far

A read of the highest sequence answers that number, or nothing where the epoch holds no rows. The absence is the answer, which is what lets a caller tell an epoch that has yet to begin from one at sequence nought.

## Moving the cursor

Writing the reconciliation cursor takes the same lock an append takes. The write is one statement that inserts or replaces, and it is committed under that lock.

So a cursor write and an event append cannot overlap, and the cursor cannot be written while an append is mid-transaction. The lock is doing more than guarding the cursor's own row: it is what keeps the commit from landing inside somebody else's transaction.

## Related

- [What an append does in one transaction](what-an-append-does-in-one-transaction.md)
- [How the spine closes a write](how-the-spine-closes-a-write.md)
