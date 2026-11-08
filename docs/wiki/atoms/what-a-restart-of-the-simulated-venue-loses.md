---
row: P64-06
baseline: 49aa659
created: 2026-11-12 22:30 UTC
modified: 2026-11-12 22:30 UTC
evidence:
  - claim: "Writing an account out names the hash of its key, its two balances and the order names it has seen, and names its fills nowhere"
    source: "`ledger.py` 754-759"
  - claim: "Reading an account back builds it with an empty run of fills, whatever the file held"
    source: "`ledger.py` 771"
  - claim: "A fill is appended to that run as it is applied, so the run is the only record of one"
    source: "`ledger.py` 446, read out at 613"
  - claim: "The numbering a trade is given carries on from the file, so a fill after a restart is numbered past the ones that are gone"
    source: "`ledger.py` 251, the number taken at 435 and 562 and carried on at 447 and 571, written out at 625"
  - claim: "The order names an account has seen do survive, and the test that turns a repeated one away reads them"
    source: "`ledger.py` 758, read back at 764 into 772, read by the test at 534"
---
# What a restart of the simulated venue loses

[Binsim's ledger](binsims-ledger.md) writes four things per account, and its fills are not among them.

## What is written

The hash of the account's key, its two balances, and the order names it has already seen.

## What happens to the fills

Reading an account back builds it with an empty run of fills, whatever the file held — and the file holds none, since writing never names them.

A fill is appended to that run as it is applied, and the run is the only record of one. So the balances outlast a restart and the account of how they came to be does not.

## What a reader sees afterwards

Asking a restarted ledger for an account's fills gives nothing back, for an account whose balances show plainly that it has traded.

## The numbering carries on

The number the next trade will take is written and read back, so a fill made after a restart is numbered past the fills that are gone.

A reader of the numbers therefore sees a run beginning partway up, with nothing to say where the missing part went.

## What else survives

The order names an account has seen. A repeated order name is turned away after a restart as before it, so the one guard built on remembering survives while the record it would be checked against does not.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [How the snapshot is written and read back](how-the-snapshot-is-written-and-read-back.md)
