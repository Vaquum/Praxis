---
row: P65-05
baseline: 49aa659
created: 2026-11-08 19:50 UTC
modified: 2026-11-08 19:50 UTC
evidence:
  - claim: "The three readings the ledger offers each take its lock, so none of them can see a settling halfway through"
    source: "`ledger.py` 593, and 609, and 619"
  - claim: "Asking for a balance or for fills refuses an account the ledger does not hold, by the same wording"
    source: "`ledger.py` 594-595, and 610-611"
  - claim: "Asking for the account names answers with a copy of them and refuses nothing"
    source: "`ledger.py` 620"
  - claim: "A balance comes back as a sealed pair of the figures themselves, so neither the pair nor a figure in it can be altered"
    source: "`ledger.py` 599"
  - claim: "Fills come back as a copy of the run, and each record in it is sealed against being altered"
    source: "`ledger.py` 613, the record sealed at 161"
  - claim: "So a caller holding the answer can add to its own copy and reach nothing the ledger holds"
    source: "`ledger.py` 613 copying the run, with 161 sealing what the run holds"
---
# The three readings the ledger offers

[Binsim's ledger](binsims-ledger.md) answers three questions about an account, and each of them is taken under its lock.

## Under the lock

All three take the lock before reading anything. So no reading can catch a settling halfway through: a caller sees the balances as they stood before a fill or as they stand after it.

## What each refuses

Asking for a balance, and asking for fills, each refuses an account the ledger does not hold, in the same words.

Asking for the names of the accounts refuses nothing. There is no account it could fail to find, so an empty ledger answers with an empty run.

## What a caller is given

A balance comes back as the pair of figures themselves, and a figure cannot be altered.

Fills come back as a copy of the run, and [each record in it](binsims-ledger.md) is sealed against being altered.

The names come back as a copy as well.

## Why that matters

A caller handed the fills or the names can add to its own copy, drop from it, or sort it, and reach nothing the ledger holds. A balance is handed over sealed, so there is nothing to do to it at all.

The sealing of each fill record is what makes the copy of the run enough — a copy alone would hand out the records themselves.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [What a restart of the simulated venue loses](what-a-restart-of-the-simulated-venue-loses.md)
