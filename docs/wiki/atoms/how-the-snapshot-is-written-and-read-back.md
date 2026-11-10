---
row: P64-05
baseline: 49aa659
created: 2026-11-08 19:39 UTC
modified: 2026-11-08 19:39 UTC
evidence:
  - claim: "Writing makes the state directory where it is absent, then makes a temporary file beside the saved one"
    source: "`ledger.py` 663, then 665-668"
  - claim: "The payload is written into that temporary file and the file moved over the saved one, which is what makes a torn write impossible"
    source: "`ledger.py` 673, then 674"
  - claim: "A failure at either step tries to remove the temporary file and then hands the failure on, the removing being guarded against nothing"
    source: "`ledger.py` 676, then 677"
  - claim: "Each account is written out as four things: the hash of its key, its two balances, and the order names it has seen"
    source: "`ledger.py` 754-759"
  - claim: "The order names it has seen are put in order as they go out"
    source: "`ledger.py` 758"
---
# How the snapshot is written and read back

[Binsim's ledger](binsims-ledger.md) lives in memory and is written whole to one file, which is what lets balances outlast the service stopping.

## Writing

The state directory is made where it is absent. A temporary file is made beside the saved one, the payload written into it, and that file moved over the saved one.

The move is what makes a torn write impossible: a reader sees either the file as it was or the file as it now is, never a part of each.

A failure at either step tries to remove the temporary file and then hands the failure on. The saved file is untouched either way, so a failed write never leaves a half-written state.

The removing is guarded against nothing. A failure of the removing itself therefore takes the place of the failure being reported, and leaves the temporary file where it was.

## What goes into it

Each account goes out as four things: the hash of its key, its two balances, and the order names it has already seen. Those names are put in order going out, so an account's part of the file is the same each time its contents are.

[Reading the file back](what-reading-the-saved-ledger-requires.md) is its own subject, and [what the file leaves out](what-a-restart-of-the-simulated-venue-loses.md) is an account's fills.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [What an interrupted save does](what-an-interrupted-save-does.md)
- [What reading the saved ledger requires](what-reading-the-saved-ledger-requires.md)
- [What a restart of the simulated venue loses](what-a-restart-of-the-simulated-venue-loses.md)
