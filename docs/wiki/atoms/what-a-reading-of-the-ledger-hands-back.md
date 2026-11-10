---
row: P87-03
baseline: 49aa659
created: 2026-11-09 05:30 UTC
modified: 2026-11-09 05:30 UTC
evidence:
  - claim: "The ledger is built holding a lock of its own"
    source: "`account_ledger.py` 81"
  - claim: "A reading of the balances takes that lock and hands back a copy of them"
    source: "`account_ledger.py` 154, then 155"
  - claim: "A reading of the trade records takes it and hands back a fresh copy of each record"
    source: "`account_ledger.py` 187, then 188"
  - claim: "A reading of what is held sums the open lots under that same lock"
    source: "`account_ledger.py` 172, then 173-174"
  - claim: "The whole state is built under it too"
    source: "`account_ledger.py` 130, then 131"
  - claim: "Registering sets the cost-basis method from the event and marks the ledger registered"
    source: "`account_ledger.py` 239, then 240"
---
# What a reading of the ledger hands back

Every way of reading the ledger takes its lock and hands back something freshly made, so a reader never holds a view that changes underneath them.

## The lock

The ledger is built holding a lock of its own. Each reading takes it for the whole of the reading.

## The balances

A reading of the balances hands back a copy of them. A reader can keep it, change it, or hold it as long as they like, and the ledger's own balances move on without it.

## The trade records

A reading of them hands back a fresh copy of each record, one per record rather than one of the mapping around them. So the figures inside each record are the reader's own too.

## What is held

A reading of what is held sums the open lots under that same lock, rather than copying them. The reader gets the total and no way to see the lots behind it.

## The whole state

Built under the lock too, so a state and the balances read beside it cannot disagree with each other.

## Registering

Setting the cost-basis method from the event and marking the ledger registered are the one pair of writes outside a posting.

## Related

- [How a journal entry moves the balances](how-a-journal-entry-moves-the-balances.md)
- [What the ledger refuses](what-the-ledger-refuses.md)
