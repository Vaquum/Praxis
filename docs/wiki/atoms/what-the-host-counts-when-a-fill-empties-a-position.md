---
row: N4-04
baseline: 49aa659
created: 2026-10-23 11:30 UTC
modified: 2026-10-23 13:00 UTC
evidence:
  - claim: "A reducing fill that leaves a position at nought removes it and raises a count kept against that trade"
    source: "`praxis/core/trading_state.py` 516-521"
  - claim: "A size that would go below nought is logged and taken as nought, which reaches that same removal"
    source: "`praxis/core/trading_state.py` 507-516 into 517-521"
  - claim: "A close takes the position out of the book, and then reads the count: one above one is lowered, and anything else is dropped"
    source: "`praxis/core/trading_state.py` 572-579"
  - claim: "Both happen before it looks at whether a position was there to take out"
    source: "`praxis/core/trading_state.py` 572-579 ahead of 580"
  - claim: "A close finding none logs at debug and does nothing else"
    source: "`praxis/core/trading_state.py` 580-587"
  - claim: "Something else reads the count without spending it, and is answered yes or no"
    source: "`praxis/core/trading_state.py` 561-564"
  - claim: "What asks is the question of whether a fill already recorded closed the trade's position, asked where the book holds no position for that trade"
    source: "`praxis/core/execution_manager.py` 10878-10881 into 10887-10889"
  - claim: "A yes is what lets the close be written to the record"
    source: "`praxis/core/execution_manager.py` 10806-10816"
---
# What the host counts when a fill empties a position

The host keeps a count, per trade, of the times a fill has left that trade's position at nought, and it is there because the position is gone before the message saying so arrives.

## Raising it

A reducing fill that leaves a position at nought removes the position and raises the count. A fill that would take it below nought is logged and taken as nought, which reaches that same removal.

## Reading it down

A close takes the position out of the book and then reads the count: one standing above one is lowered, anything else is dropped — including a count that was never raised. Both happen before it looks at whether a position was there to take out at all — and one finding none logs at debug and does nothing else.

## Reading it without spending it

One reader asks a different question and is answered yes or no: whether a fill already recorded closed the trade's position. A yes is what lets the close be written to the record. It asks only where the book holds no position for that trade — which is what a fill that has already emptied one leaves behind, and also what a trade that never held one looks like. The count is what separates them.

## Related

- [Fills and the order](fills-and-the-order.md)
- [What a fill changes](what-a-fill-changes.md)

---

Created 2026-10-23 11:30 UTC · Last modified 2026-10-23 13:00 UTC
