---
row: P2-30
baseline: 49aa659
created: 2026-09-26 06:05 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "A buy whose fee asset is BTC delivers the amount less the commission"
    source: "`trading_state.py` 84-85 with the string at 66, subtracted at 459 and used at 483"
  - claim: "Every other fill delivers its full amount"
    source: "`trading_state.py` 87"
  - claim: "The side and the fee asset are tested, never the symbol"
    source: "`trading_state.py` 84"
  - claim: "The money ledger books one symbol only"
    source: "`account_ledger.py` 244-246"
  - claim: "It splits the same way for its lots"
    source: "either `account_ledger.py` 298-302 or 308-312"
  - claim: "Only its BTC branch refuses a commission that is not smaller than the amount"
    source: "`account_ledger.py` 305-307, the alternative branch at 298-302 carrying no such test"
  - claim: "The order's own filled total stays gross"
    source: "`trading_state.py` 430, which adds the fill's own amount"
---
# The commission and the amount

A [fill](what-a-fill-is.md) reports an amount, and [holdings](holdings.md) are sometimes given less than it. A buy whose commission was charged in BTC delivers that amount less the commission. Every other fill delivers the whole of it.

The test looks at the side and at the asset the commission was charged in. It never looks at the symbol.

## What that leaves out

A pair whose coin is still BTC gets the subtraction, whatever the money side of it is.

A buy of some other coin, charged its commission in that coin, delivers its full amount while the wallet receives less — so the record sits above the wallet by the commission, and again on every buy after it. That is recorded in [the register](../register.md) as U-04.

The money ledger books one symbol and splits the same way when it builds its lots: a buy charged in the money asset keeps its whole amount, a buy charged in BTC has the commission taken off.

Only the second of those two checks the size. [A BTC commission that is not smaller than the amount](when-the-commission-swallows-the-fill.md) the ledger refuses outright, where holdings go on and take it. A money-asset commission of any size it books without complaint.

## Why the order's total differs

The amount an order records as filled stays gross — the fill's own amount, commission and all.

Holdings say what is there to sell. An order says whether the amount asked for arrived, and by that reckoning the commission is a cost rather than a shortfall.

## Related

- [When the commission is the whole amount](when-the-commission-swallows-the-fill.md)
- [Holdings](holdings.md)
