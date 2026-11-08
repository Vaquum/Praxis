---
row: P64-01
baseline: 49aa659
created: 2026-11-12 22:30 UTC
modified: 2026-11-12 22:30 UTC
evidence:
  - claim: "Taking the lock makes the state directory where it is absent, then resolves it so the path named in a refusal is a full one"
    source: "`ledger.py` 65, then 69"
  - claim: "The lock file is opened for appending rather than writing, which leaves whatever it held in place"
    source: "`ledger.py` 74"
  - claim: "The lock is asked for without waiting, so a second caller is refused rather than held up"
    source: "`ledger.py` 76"
  - claim: "Only once the lock is held is the file emptied and the holder's own number written into it"
    source: "`ledger.py` 86-89"
  - claim: "The lock is let go however the work inside ends, and the number in the file is left standing"
    source: "`ledger.py` 91-94, with nothing written there on the way out"
---
# The lock one writer holds

[Binsim's ledger](binsims-ledger.md) is held whole in memory by whichever process has it, and written out whole. One lock on the state directory is what keeps two processes from each writing over the other.

## Taking it

The directory is made where it is absent. Its path is then resolved, so the path a refusal names is a full one rather than however the caller spelled it.

The lock file is opened for appending. Writing would empty it first, and emptying it would erase the holder's number before the lock is even asked for — from the very caller that needs to report it.

The lock is asked for without waiting. A second caller is refused there and then rather than held up behind the first, and [what that refusal says](what-a-refused-writer-is-told.md) is a subject of its own.

## Holding it

Only once the lock is held is the file emptied and the holder's own number written in, and the writing is pushed out to the file there and then rather than left to be flushed later.

## Letting it go

The lock is let go however the work inside ends.

The number is left in the file. Nothing clears it, so the file names a holder after the holding is over.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [Binsim](binsim.md)
