---
row: P64-02
baseline: 49aa659
created: 2026-11-12 22:30 UTC
modified: 2026-11-12 22:30 UTC
evidence:
  - claim: "The account's name is trimmed first, with nothing at all read as emptiness, and emptiness refused"
    source: "`ledger.py` 282, then 284-285"
  - claim: "Both starting balances are held to being finite in one test, then each to standing at or above nought in a test of its own"
    source: "`ledger.py` 287-291, then 293-294, then 296-297"
  - claim: "Only past those four is the ledger's own lock taken, and a name already registered refused inside it"
    source: "`ledger.py` 299, then 300-301"
  - claim: "A key is then minted, hashed, and the account built around the hash, the key itself going into nothing that is kept"
    source: "`ledger.py` 303-304, into 306-312"
  - claim: "The snapshot is written before the key is handed back, so a caller holding a key holds one the saved state knows"
    source: "`ledger.py` 315, then 317"
  - claim: "Minting draws a fresh key until one is drawn whose hash the index does not already hold"
    source: "`ledger.py` 327-331"
  - claim: "Nothing else in the ledger mints a key, and registering refuses a name it already holds, so an account's key is minted once and never again"
    source: "`ledger.py` 303, the only call reaching 327-331, against the refusal at 300-301"
---
# What registering an account refuses, and the key it mints

Registering an account with [binsim's ledger](binsims-ledger.md) checks four things before it touches the ledger at all, and hands back a key it then has no way to give again.

## The four checks outside the lock

The name is trimmed, with nothing at all read as emptiness, and emptiness refused.

Both starting balances are held to being finite, in one test naming both. Each is then held to standing at or above nought, in a test of its own, so a complaint names which balance was wrong.

## The one inside

Only past those is the ledger's lock taken, and a name it already holds refused there.

## What is kept

A key is minted and hashed. The account is built around the hash, and the key itself goes into nothing that is kept.

The snapshot is written before the key is handed back, so a caller holding a key holds one the saved state already knows.

## Minting

A fresh key is drawn until one is drawn whose hash the index does not already hold. The loop has no limit and no count, which is sound because it ends on the first draw unless two draws give hashes that agree.

## Once and never again

Nothing else in the ledger mints a key, and registering refuses a name it already holds.

So the key an operator is handed is the only one that account will ever have, and registering the name again is refused.

What a lost key costs is reaching the account from outside: the ledger's own readings and changes name an account directly and ask for no key at all, so an operator with the state directory still has the account.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [How a key names an account](how-a-key-names-an-account.md)
- [The lock one writer holds](the-lock-one-writer-holds.md)
