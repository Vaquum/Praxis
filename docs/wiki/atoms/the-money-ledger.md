---
row: P3-11
baseline: 49aa659
created: 2026-09-28 12:14 UTC
modified: 2026-09-28 18:31 UTC
evidence:
  - claim: "There are five accounts and no others"
    source: "`chart_of_accounts.py` 20-24"
  - claim: "A line cannot carry a positive amount on both sides"
    source: "`journal_entry.py` 46-48"
  - claim: "Neither side of a line may be below zero"
    source: "`journal_entry.py` 42-44"
  - claim: "Neither may be a figure without end"
    source: "`journal_entry.py` 38-40"
  - claim: "An entry with no lines is refused"
    source: "`journal_entry.py` 77-79"
  - claim: "An entry whose two sides differ is refused"
    source: "`journal_entry.py` 84-86, summed at 81-82"
  - claim: "It books one trading pair and refuses any other"
    source: "`account_ledger.py` 244-246"
  - claim: "A buy's fee is taken in one of two assets, and refused otherwise"
    source: "`account_ledger.py` 298-314"
  - claim: "A sell's fee is taken in one asset only"
    source: "`account_ledger.py` 336-338"
  - claim: "What a sell brought in, and what it cost, are posted apart from the fee"
    source: "`account_ledger.py` 340-354"
  - claim: "The fee is posted on lines of its own"
    source: "`account_ledger.py` 384-389"
  - claim: "Profit is gathered per trade, and the fee taken off at the end"
    source: "gathered at `account_ledger.py` 415-417, taken off at `trade_pnl.py` 40"
  - claim: "One account holds what was put in less what was taken out"
    source: "`account_ledger.py` 264-288"
---
# The money ledger

The **money ledger** is Praxis's own account of what a [trade](what-a-trade-is.md) did to the money. It sits beside [the holdings](holdings.md), which say what is held; this says what it cost and what it made.

Five accounts hold everything: the money, the coin, the profit realised, the fees paid, and what has been put in less what has been taken out.

## Entries that must balance

Every fill it accepts becomes one entry made of lines, each posting to one account. A line cannot carry a positive amount on both sides, neither side may be below zero, and neither may be a figure without end.

An entry with no lines is refused, and so is one whose two sides do not come to the same total. That keeps each entry internally square — it does not keep the ledger level with anything else, since [a failure here is logged and passed over](what-a-fill-changes.md) while trading goes on.

## What it will take

It books one trading pair and refuses any other. A buy's fee must be in one of two assets and a sell's in one, and anything else is refused.

How a buy is remembered, and how a sell is costed against it, is set out in [lots](lots-and-what-a-sell-costs.md).

## What a trade made

What a sell brought in, less what its lots cost, is the profit before fees. The fee is never folded into that: it gets lines of its own.

Both are gathered per trade as the run goes, and the fee is taken off only when the figure is asked for — so what is kept along the way is before fees, and what is reported is after.

## Related

- [Lots, and what a sell costs](lots-and-what-a-sell-costs.md)
- [Holdings](holdings.md)
- [What a fill changes](what-a-fill-changes.md)
