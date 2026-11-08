---
row: P64-03
baseline: 49aa659
created: 2026-11-12 22:30 UTC
modified: 2026-11-12 22:30 UTC
evidence:
  - claim: "A key is answered with nothing unless it is text, and nothing is raised for one that is not"
    source: "`ledger.py` 353-354"
  - claim: "A key is trimmed, and one holding nothing once trimmed names no account either"
    source: "`ledger.py` 356, then 358-359"
  - claim: "A key that survives both is hashed and the hash looked up, so a key padded with spaces names the account its trimmed form does"
    source: "`ledger.py` 361"
  - claim: "The lookup answers with nothing where the hash is unknown, by the same means as the two checks above"
    source: "`ledger.py` 361, reading the index with a default"
  - claim: "The hashing is a single pass of one hash over the key's bytes, and the ledger keeps only its result"
    source: "`ledger.py` 788, kept at 755 and read back at 768"
  - claim: "Resolving a key takes no lock, the index being changed only where the ledger's lock is held"
    source: "`ledger.py` 353-361 taking none, against 299-313"
---
# How a key names an account

A request to [the simulated venue](binsim.md) carries a key, and [the ledger](binsims-ledger.md) turns that key into an account's name or into nothing.

## Three ways of getting nothing

A key of any kind other than text answers with nothing. A key holding nothing once trimmed answers with nothing. A key whose hash is a stranger to the index answers with nothing.

All three answer alike, and none of them raises. What a caller makes of the nothing is the caller's own business.

## What a key that survives is put through

It is trimmed, hashed, and the hash looked up.

Trimming before hashing means a key padded with spaces names the account its trimmed form names. Padding is therefore not a way to be turned away.

## What the ledger keeps

One pass of one hash over the key's bytes, and the result of that pass is all the ledger holds. The key itself is in the saved state nowhere, which is why resolving has to go through the hash.

## No lock

Resolving takes no lock. The index it reads is changed only where the ledger's own lock is held, and resolving is a single reading of it.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [What registering an account refuses, and the key it mints](what-registering-an-account-refuses-and-the-key-it-mints.md)
