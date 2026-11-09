---
row: P2-49
baseline: 49aa659
created: 2026-10-13 11:10 UTC
modified: 2026-11-16 11:30 UTC
evidence:
  - claim: "The whole fill goes into the order first, the part that counts is worked out next, and the money record is written after that"
    source: "`execution_manager.py` 2081 before 2084 before 2087"
  - claim: "A buy charged its commission in the coin has that off the holding and never off what the command counted"
    source: "`praxis/core/trading_state.py` 84-85, against `execution_manager.py` 2505-2518"
  - claim: "A running total of what has counted is kept against the command's name"
    source: "`execution_manager.py` 2474-2476, written at 2561-2563"
  - claim: "An amount-sized command counts a fill up to what is left of its amount"
    source: "`execution_manager.py` 2505-2507"
  - claim: "A money-sized one counts up to what is left of its money, the amount being that room over this fill's price"
    source: "`execution_manager.py` 2509-2518"
  - claim: "A fill whose command recorded no budget counts for nothing"
    source: "`execution_manager.py` 2477 and 2479 into 2499, then 2503"
  - claim: "The running total is capped and the part counted worked back out of it, so rounding cannot carry the total past the budget"
    source: "`execution_manager.py` 2525-2533"
  - claim: "A fill that leaves nothing to count leaves the running total as it was"
    source: "`execution_manager.py` 2554-2559"
  - claim: "Counting less than arrived is logged against what was discarded"
    source: "`execution_manager.py` 2536-2549"
---
# The part of a fill a command counts

[A fill](what-a-fill-is.md) goes into [the order](fills-and-the-order.md) and [the money record](the-money-ledger.md) whole. Only the part of it fitting the command's own budget counts towards [the figures Praxis reports back](the-figures-carried-back-on-a-fill.md), so the two can part company over the same fill.

## What the budget is

[A command](what-a-command-must-carry.md) names an amount of coin or an amount of money, never both, and that is its budget. A running total of what has counted so far is kept against the command's name.

A command sized in coin counts a fill up to what is left of its amount. One sized in money counts up to what is left of its money, and the amount it counts is that remaining room over the price this fill got.

## A fill with nothing to count against

A fill whose command recorded no budget counts for nothing: counting it would report an amount nobody ordered. A fill arriving on a budget already full leaves the running total exactly as it was.

## Where the rounding goes

Dividing money by a price rounds, so bounding each fill's part would not bound the total. The total is capped instead, and the part this fill counted is worked back out of the capped total — so what the fill is recorded as counting and what the totals moved by are one number.

## What goes unreported

Where less is counted than arrived, the difference is logged as discarded. The order still holds the whole fill, so what Praxis records and what Nexus hears part company. They part company for a second reason too: a buy charged its commission in the coin has that taken off the holding, and never off what the command counted.

## Related

- [The figures carried back on a fill](the-figures-carried-back-on-a-fill.md)
- [Fills and the order](fills-and-the-order.md)
- [What a fill changes](what-a-fill-changes.md)

---

Created 2026-10-13 11:10 UTC · Last modified 2026-10-14 08:05 UTC
