---
row: P90-03
baseline: 49aa659
created: 2026-11-09 07:12 UTC
modified: 2026-11-09 07:12 UTC
evidence:
  - claim: "Snapping an amount floors it onto the step and multiplies back, so the answer is the largest multiple of the step at or below what was asked"
    source: "`praxis/binsim/server.py` 564"
  - claim: "The check against the smallest worth answers at once where the book gave no price to weigh against"
    source: "`praxis/binsim/server.py` 683 into 684"
  - claim: "Where a price was given, the worth is that price times the amount"
    source: "`praxis/binsim/server.py` 686"
  - claim: "Reading a figure from a parameter answers the figure itself once it has passed"
    source: "`praxis/binsim/server.py` 725"
---
# What an order's figures are put through

Three small readings stand between what a caller sent and what binsim books, and each either answers a figure or refuses.

## The snapping

Snapping an amount floors it onto the step and multiplies back. The answer is therefore the largest multiple of the step at or below what was asked, so snapping only ever lowers an amount.

## The check that can be skipped

The check against the smallest worth answers at once where the book gave no price to weigh against. Where a price was given, the worth is that price times the amount.

So an order arriving while the book holds no price passes this check without being weighed, and [the refusal it would otherwise meet](when-binsim-turns-an-order-away.md) is never reached. Whether that order is stopped elsewhere is settled before this check, not here.

## The reading of a parameter

Reading a figure from a parameter answers the figure itself once it has passed. The reading is where a bad parameter is caught, and what reaches the rest of the submitting is always a figure.

## Related

- [When binsim turns an order away](when-binsim-turns-an-order-away.md)
- [What binsim's read endpoints answer](what-binsims-read-endpoints-answer.md)
