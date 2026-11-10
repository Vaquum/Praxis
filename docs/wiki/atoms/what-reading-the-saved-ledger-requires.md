---
row: P64-08
baseline: 49aa659
created: 2026-11-08 19:39 UTC
modified: 2026-11-08 19:39 UTC
evidence:
  - claim: "Reading takes the ledger's own lock before it looks at anything"
    source: "`ledger.py` 244"
  - claim: "A saved file that is absent leaves the ledger as it was and the reading answers"
    source: "`ledger.py` 245-246"
  - claim: "A file that is there is read and parsed with nothing catching a failure of either, so a damaged file stops the reading"
    source: "`ledger.py` 248, then 249"
  - claim: "The next trade's number is required outright and the next order's number falls back to one"
    source: "`ledger.py` 251, then 252"
  - claim: "The accounts are required and rebuilt one by one, and the key index is then rebuilt from those accounts rather than read from the file"
    source: "`ledger.py` 253-256, then 257-260"
  - claim: "An account's run of order names falls back to nothing, and each account comes back with an empty run of fills"
    source: "`ledger.py` 764, and 771"
---
# What reading the saved ledger requires

Reading [the saved ledger](how-the-snapshot-is-written-and-read-back.md) back into memory happens once, under the ledger's own lock, before anything else touches it.

## A missing file is an answer

A saved file that is absent leaves the ledger as it was and the reading simply answers. That is how a service with nothing saved starts empty rather than failing.

## A damaged file is not

A file that is there is read and parsed with nothing catching a failure of either step. A file that is not readable text, or not well-formed, therefore stops the reading — and the service does not come up on top of state it could not understand.

## What the file must name

The next trade's number, and the accounts. Either missing stops the reading.

The next order's number falls back to one, so a file written before that number was kept still reads.

## What is rebuilt rather than read

The key index. It is built from the accounts just rebuilt rather than read out of the file, so it cannot disagree with the accounts it indexes, whatever the file said.

An account's run of order names falls back to nothing where the file has none, and every account comes back with an empty run of fills.

## Related

- [How the snapshot is written and read back](how-the-snapshot-is-written-and-read-back.md)
- [What a restart of the simulated venue loses](what-a-restart-of-the-simulated-venue-loses.md)
