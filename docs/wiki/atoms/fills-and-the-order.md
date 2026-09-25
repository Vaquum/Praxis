---
row: P2-31
baseline: 49aa659
created: 2026-09-25 19:37 UTC
modified: 2026-09-25 19:37 UTC
evidence:
  - claim: "The amount filled and the running value grow by what the fill brought"
    source: "`trading_state.py` 430-433"
  - claim: "A fill naming an order held neither way adds nothing"
    source: "`trading_state.py` 426-428, holdings following at 403"
  - claim: "An order that named an amount is filled once that amount is reached"
    source: "`trading_state.py` 437-440"
  - claim: "An order that named no amount stays partly filled here"
    source: "`trading_state.py` 434-436"
  - claim: "A separate report closes that one"
    source: "`execution_manager.py` 4343-4354"
  - claim: "A fill for an order already closed is booked, and the status is left alone"
    source: "`trading_state.py` 417-424"
---
# Fills and the order

A [fill](what-a-fill-is.md) that Praxis can match to an order it is holding adds to that order's totals: the amount filled and the running value both grow by what the fill brought.

A fill naming an order held neither as open nor as closed adds nothing at all, and [the holdings](holdings.md) are still changed by that same fill.

## Reaching the end

An order that named an amount to trade is marked filled once the amount reached covers it, and partly filled until then.

An order that named a sum of money instead stays partly filled however much arrives. A separate report is what closes that one.

## A fill after the end

A fill can arrive for an order that has already closed. One way that happens is a leg of a protective pair delivered late, but the only thing tested is whether the order is among the closed ones, so any closed order can take one.

The amount and the value are still added, so totals read later are right. The status it closed at is left alone: it does not go back to partly filled, and it does not close a second time.

## Related

- [What a fill changes](what-a-fill-changes.md)
- [Holdings](holdings.md)
