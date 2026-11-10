---
row: P64-07
baseline: 49aa659
created: 2026-11-08 19:39 UTC
modified: 2026-11-08 19:39 UTC
evidence:
  - claim: "Every failure the asking for the lock can report becomes one refusal, with nothing read off the failure to tell one from another"
    source: "`ledger.py` 77, catching one kind and reading no more of it than the raising needs"
  - claim: "The refusal reads the lock file and names the state directory and whatever holder it found"
    source: "`ledger.py` 78 into 79-84"
  - claim: "That reading answers with nothing where the file cannot be read, and with nothing where the file holds nothing"
    source: "`ledger.py` 111-114, then 116"
  - claim: "The holder's number is written only once the lock is held, so between the taking and the writing the file still holds the number before it"
    source: "`ledger.py` 76 ahead of 86-89"
  - claim: "Nothing clears the number when the lock is let go, so the file names a holder after the holding is over"
    source: "`ledger.py` 91-94"
---
# What a refused writer is told

Asking for [the lock on the state directory](the-lock-one-writer-holds.md) either gives it or gives one refusal, and that refusal is assembled from two readings that can each come up short.

## One refusal for every ground

Every failure the asking can report becomes that refusal. Nothing is read off the failure to tell one kind from another.

So a filesystem that cannot lock at all, and a handle that is wrong, are both reported as another process holding the ledger — a message naming a cause the caller cannot check.

## The holder it names

The refusal reads the lock file and names the state directory together with whatever it found there.

The reading is best effort. A file it cannot read gives nothing, and a file holding nothing gives nothing, and in either case the message still names the directory.

## When the number is wrong

The holder's number is written only once the lock is held. Between the taking and the writing, the file still holds the number before it.

Nothing clears the number when the lock is let go either. So the file names a holder after the holding is over, and a refusal arriving in the wrong moment names a process that has finished or names none at all.

## Related

- [The lock one writer holds](the-lock-one-writer-holds.md)
- [Binsim's ledger](binsims-ledger.md)
