---
row: P188-01
baseline: 49aa659
created: 2026-11-16 14:30 UTC
modified: 2026-11-16 14:30 UTC
evidence:
  - claim: "A fill's commission is taken out of the holdings it adds only where the fill is a buy and the fee was charged in one named asset"
    source: "`trading_state.py` 84, then 85, the name fixed at 66"
  - claim: "Any other fee asset leaves nothing to take out"
    source: "`trading_state.py` 87"
  - claim: "What a fill adds to holdings is its size less whatever that reading gave"
    source: "`trading_state.py` 459, read at 483"
  - claim: "So a buy whose commission is charged in a base asset of any other name is credited at its gross size"
    source: "`trading_state.py` 84, against 459"
  - claim: "The money record refuses a fill of any symbol but one outright"
    source: "`account_ledger.py` 244, then 245-246, the symbol fixed at 46"
  - claim: "That refusal is swallowed where the money record is written to"
    source: "`execution_manager.py` 2091, then 2093"
---
# The one asset a commission is netted in

A buy pays its commission in the asset it receives, so the holdings a buy adds are short by that commission — and Praxis takes it out only when the fee was charged in one named asset.

## The reading

A fill is read for a base-asset commission on two conditions: that it is a buy, and that the asset the fee was charged in carries one fixed name. Any other fee asset leaves nothing to take out.

What the fill then adds to holdings is its size less whatever that reading gave.

## What follows for a second symbol

A buy of another symbol, whose commission is charged in that symbol's own base asset, is read as having no base commission at all and credited at its gross size. The holdings would then sit above the wallet by the commission on every such buy — which is the compounding gap the netting exists to close.

## What stands in the way of reaching it

The money record refuses a fill of any symbol but one, outright. That refusal is raised where a fill is booked into it, and swallowed there, so a second symbol would leave the holdings gross and the money record silent rather than either of them stopping.

## Related

- [Holdings, and how a fill changes them](holdings.md)
- [Which record an event is booked into](which-record-an-event-is-booked-into.md)
- [What an account is](what-an-account-is.md)
