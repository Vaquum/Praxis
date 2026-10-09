---
row: P4-12
baseline: 49aa659
created: 2026-10-03 17:42 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A position is kept against a trade and an account together"
    source: "`trading_state.py` 482, the record made at 489-497"
  - claim: "It carries the account, the trade, the pair, a side, an amount and an average price"
    source: "`praxis/core/domain/position.py` 37-42, filled at `trading_state.py` 490-495"
  - claim: "Three of its names must each be something rather than nothing"
    source: "`praxis/core/domain/position.py` 49-50 into `_require_str.py` 28-30"
  - claim: "Neither the amount nor the average price may be below nought, at the making or on assignment"
    source: "`praxis/core/domain/position.py` 52-58 and 63-69"
  - claim: "It also carries the strategy the trade was recorded against, which may be absent"
    source: "`praxis/core/domain/position.py` 43, filled from `trading_state.py` 496, recorded at 392-396"
  - claim: "A fill on the same side adds to the amount and reworks the average"
    source: "`trading_state.py` 500-505"
  - claim: "The average weights the old amount at the old price against the fill at its own"
    source: "`trading_state.py` 502-504"
  - claim: "A fill on the other side takes away, the average left alone"
    source: "`trading_state.py` 506-519"
  - claim: "What a fill adds or takes is the amount reported, less a fee only where a buy's was charged in Bitcoin by name"
    source: "`trading_state.py` 459 called at 483, the test at 66 and 84-87"
  - claim: "A sell's reported amount is used unchanged, whatever its fee was charged in"
    source: "`trading_state.py` 84-87"
  - claim: "The money ledger nets a Bitcoin buy fee off its lots the same way"
    source: "`account_ledger.py` 298-316"
  - claim: "That ledger takes one pair only, and refuses a Bitcoin buy fee as large as the amount it is charged on"
    source: "`account_ledger.py` 244-246, the pair at 44-46, the fee refused at 303-306"
  - claim: "The position keeps none of those restrictions"
    source: "`praxis/core/domain/position.py` 45-71"
  - claim: "An order's own totals are added gross"
    source: "`trading_state.py` 430-432"
  - claim: "A command's are gathered gross too"
    source: "`execution_manager.py` 2671-2683"
  - claim: "A subtraction that would go below nought is logged as a warning and made nought"
    source: "`trading_state.py` 508-515"
  - claim: "Nought there removes the position and forgets its strategy"
    source: "`trading_state.py` 517-519"
  - claim: "A first buy whose Bitcoin fee equals its amount makes a position of nought and leaves it standing"
    source: "`trading_state.py` 483 and 488-498, the fee allowed to equal the amount at `events.py` 585-595"
---
# The position Praxis keeps

A **position** is what Praxis records of the coin, kept against one [trade](what-a-trade-is.md) and one [account](what-an-account-is.md) together.

## What it carries

The account, the trade, the pair, a side, an amount, and an average price paid. Three of those names must each be something rather than nothing, and neither the amount nor the average price may be below nought — at the making and on every assignment.

It also carries the strategy the trade was recorded against, which may be absent.

## How a fill moves it

A [fill](what-a-fill-is.md) on the same side adds to the amount and reworks the average, weighting what was held at the old price against what arrived at the fill's own. One on the other side takes away, the average left alone.

What a fill adds or takes is the amount the venue reported — less a fee, but only where a buy's was charged in Bitcoin, tested by name. A sell's reported amount is used unchanged, whatever its fee was in.

[The money ledger](the-money-ledger.md) nets a Bitcoin buy fee off its lots the same way, so for that one case the two agree. The ledger takes one pair only, and refuses a Bitcoin buy fee as large as the amount it is charged on; the position keeps neither restriction. An order's totals, and a command's, are gathered gross throughout.

## Reaching nothing

A subtraction that would take the amount below nought is logged as a warning and made nought. That changes the record alone: no fill is undone, and the venue holds what it holds.

Nought reached that way removes the position, and forgets the strategy with it. Nought reached another way does not: a first buy whose Bitcoin fee equals its amount makes a position of nothing and leaves it standing.

## Related

- [Holdings](holdings.md)
- [The commission and the amount](the-commission-and-the-amount.md)
