---
row: P54-02
baseline: 49aa659
created: 2026-11-12 11:30 UTC
modified: 2026-11-12 12:00 UTC
evidence:
  - claim: "The state a ledger can be rebuilt from holds the account's name, whether it was registered, the way of costing, the balances, the per-trade figures and the open lots"
    source: "`account_ledger.py` 131-135 and the fields following it"
  - claim: "The journal is not among them"
    source: "`account_ledger.py` 131-135, which names no journal"
  - claim: "Rebuilding restores the way of costing, the balances, the per-trade figures and the lots"
    source: "`account_ledger.py` 213-215, or 219-220, or 222-225, or 226-229"
  - claim: "The lots come back in the order the snapshot listed them"
    source: "`account_ledger.py` 226-229"
  - claim: "Under average costing there is one lot per trade to come back, purchases having been merged into it as they were booked"
    source: "`account_ledger.py` 324-330"
  - claim: "Whether it was registered is taken from the snapshot, falling back to whether a way of costing was recorded"
    source: "`account_ledger.py` 217"
---
# What a rebuilt ledger carries

A ledger can be rebuilt from a snapshot of its state: the balances, what each trade has made, and the lots still open.

## What is left behind

The journal. Every entry the ledger posted is its account of why the balances are what they are, and none of it is in the state.

So a rebuilt ledger agrees with the old one about the money, and about what each trade realized and paid in fees, while the posting that produced each figure is gone.

## What the rebuilding restores

The way of costing a sell, where one was recorded. The balances, read back one account at a time. What each trade has made and paid, and whether it is closed. The open lots, each with its size and its unit cost, in the order the snapshot listed them.

How many lots there are to restore depends on the way of costing: under average costing each purchase was merged into one lot per trade as it was booked, so one lot comes back however many purchases there were.

## The field with a fallback

Whether the ledger was registered. The snapshot carries it, and where it does not, the rebuilding falls back to whether a way of costing was recorded.

## Related

- [The money ledger](the-money-ledger.md)
- [What the ledger refuses to apply](what-the-ledger-refuses-to-apply.md)
- [Lots and what a sell costs](lots-and-what-a-sell-costs.md)
