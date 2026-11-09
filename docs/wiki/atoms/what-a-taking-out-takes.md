---
row: N3-09
baseline: 49aa659
created: 2026-10-22 19:40 UTC
modified: 2026-10-23 07:08 UTC
evidence:
  - claim: "The amount asked for is the position's cost basis times the size sold"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438"
  - claim: "What comes out is the amount asked for, or either figure where that is the smaller"
    source: "`nexus/core/capital_controller/capital_controller.py` 800-806"
  - claim: "An amount above either figure by more than a millionth of a millionth is refused before that, the report failing with it"
    source: "`nexus/core/capital_controller/capital_controller.py` 769-783 and 784-798, the tolerance at `nexus/core/domain/capital_state.py` 16, the failure at `nexus/infrastructure/praxis_connector/outcome_processor.py` 248-253"
  - claim: "A strategy's figure left within that same amount of nought, on either side of it, is dropped from the figures rather than kept"
    source: "`nexus/core/capital_controller/capital_controller.py` 1097-1101"
  - claim: "The same reading drops a figure left further below nought than that and logs it, which a taking-out cannot cause: what comes out is capped at the figure itself"
    source: "`nexus/core/capital_controller/capital_controller.py` 1097-1098 into 1104-1113, against 800-806"
  - claim: "Dropping it removes that strategy from the sum the account's total is weighed against"
    source: "`nexus/core/capital_controller/capital_controller.py` 1100-1101 against 347-350"
  - claim: "The account's own figure is reduced by the same amount, with no such dropping"
    source: "`nexus/core/capital_controller/capital_controller.py` 805-806"
---
# What a taking-out takes

A taking-out is how committed money is released as a position is sold, and what it removes is not always what it was asked for.

## The amount

It is asked for the position's cost basis times the size sold. What comes out is that, or either of the two figures it reduces where one of those is smaller — so an amount a shade above a figure is taken down to it rather than past it.

## The refusal first

An amount above either figure by more than a millionth of a millionth is refused before any of that, and the report it came with fails rather than going on. The clamp is therefore for the shade, and the refusal for the gap.

## The strategy's figure, dropped

The account's figure is reduced by the amount and left at whatever that leaves. A strategy's is read again afterwards: one left within a millionth of a millionth of nought, on either side of it, is dropped from the figures altogether. The same reading drops a figure left further below nought and logs it, which this taking-out cannot cause: what comes out is capped at the figure itself.

Dropping a strategy takes it out of the sum the account's total is weighed against, which is why [two figures out of step](what-the-deployed-figures-out-of-step-refuse.md) can come back into step while the account runs, without waiting for a start.

## Related

- [What a dusted scrap leaves behind](what-a-dusted-scrap-leaves-behind.md)
- [What the deployed figures out of step refuse](what-the-deployed-figures-out-of-step-refuse.md)

---

Created 2026-10-22 19:40 UTC · Last modified 2026-10-23 07:08 UTC
