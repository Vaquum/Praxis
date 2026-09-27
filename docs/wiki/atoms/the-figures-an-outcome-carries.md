---
row: P2-40
baseline: 49aa659
created: 2026-09-26 20:21 UTC
modified: 2026-09-27 07:10 UTC
evidence:
  - claim: "A target amount given must be a finite figure above zero"
    source: "`trade_outcome.py` 118-124"
  - claim: "The amount filled cannot be below zero"
    source: "`trade_outcome.py` 126-128"
  - claim: "It cannot be above the target"
    source: "`trade_outcome.py` 130-132"
  - claim: "An average price, where one is given, must be above zero"
    source: "`trade_outcome.py` 134-136"
  - claim: "Nothing filled must carry no average price at all"
    source: "`trade_outcome.py` 138-140"
  - claim: "A value below zero is refused"
    source: "`trade_outcome.py` 154-156"
  - claim: "Nothing filled must carry a value of nought"
    source: "`trade_outcome.py` 158-160"
  - claim: "Something filled is refused with a value of nought"
    source: "`trade_outcome.py` 162-164"
  - claim: "The slices done cannot be below zero"
    source: "`trade_outcome.py` 142-144"
  - claim: "The total must be above zero"
    source: "`trade_outcome.py` 146-148"
  - claim: "The slices done cannot exceed the total"
    source: "`trade_outcome.py` 150-152"
---
# The figures an outcome carries

An [outcome](what-an-outcome-is.md) is refused as it is made unless its figures hold together. The rules come in pairs, each pair closing one way of reporting something that cannot have happened.

## The amounts

A target amount, where one is given, must be a real figure above zero. The amount filled cannot be below zero, and cannot be above that target.

The slices done cannot be below zero, the total must be above zero, and the slices done cannot exceed the total. There is no work made of no slices.

## The price and the value

An average price, where one is given, must be above zero. Nothing filled must carry no average price at all, so a price for a fill that never happened is refused.

The value is a figure rather than a blank, and the rules run three ways. It cannot be below nought. Nothing filled must leave it at nought exactly. Something filled must put it above nought.

Each rule weighs one figure, or two against each other. [A good deal is left alone](what-an-outcome-does-not-check.md).

## Related

- [What an outcome does not check](what-an-outcome-does-not-check.md)
- [Outcomes](what-an-outcome-is.md)
