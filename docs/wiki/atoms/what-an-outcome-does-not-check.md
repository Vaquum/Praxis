---
row: P2-42
baseline: 49aa659
created: 2026-09-26 20:29 UTC
modified: 2026-09-27 07:08 UTC
evidence:
  - claim: "No rule ties the value to the amount times the price"
    source: "`trade_outcome.py` 111-164, which multiplies nothing"
  - claim: "Only the target amount is required to be a finite figure"
    source: "`trade_outcome.py` 111-164, which tests for one at 120 and nowhere else"
  - claim: "The status is read nowhere among the rules"
    source: "`trade_outcome.py` 111-164, which names it nowhere"
  - claim: "The slice counts are compared but never required to be whole"
    source: "`trade_outcome.py` 142-152"
  - claim: "The two slippage figures are not examined"
    source: "`trade_outcome.py` 111-164, which names neither"
---
# What an outcome does not check

[The rules an outcome must satisfy](the-figures-an-outcome-carries.md) each weigh one figure, or two against each other. What follows is what none of them looks at.

## The arithmetic

Nothing multiplies. A fill may be reported with a value and with no average price, and no rule asks whether the value equals the amount times the price.

So the three can each be allowed and together impossible.

## Figures without end

Only the target amount is required to be a real figure. An average price without end passes, and so does a value without end.

## The status

The status is read nowhere among the rules. An [outcome](what-an-outcome-is.md) may therefore call itself filled while reporting that nothing filled and that no slice of the work was done.

Nothing here ties what an outcome says about itself to what its figures say.

## Slices and slippage

The slice counts are compared with each other, and with zero, but never required to be whole. A third of a slice out of two is allowed.

The two slippage figures are not examined in any way. Whatever is put in them is kept.

## Related

- [The figures an outcome carries](the-figures-an-outcome-carries.md)
- [Outcomes](what-an-outcome-is.md)
