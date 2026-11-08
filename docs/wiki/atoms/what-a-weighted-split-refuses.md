---
row: P18-02
baseline: 49aa659
created: 2026-11-10 20:00 UTC
modified: 2026-11-10 20:00 UTC
evidence:
  - claim: "The weighted split makes the same two checks as the even one, its count being the number of weights"
    source: "`praxis/core/plan_weighted_slices.py` 50-52, or 54-56"
  - claim: "The weights themselves are asked nothing"
    source: "`praxis/core/plan_weighted_slices.py` 50-56, which names them at 54 and tests only how many there are"
  - claim: "Where the venue's lot size is known, a child coming to nought or below is refused as the plan is made"
    source: "`praxis/core/plan_weighted_slices.py` 66-72"
  - claim: "Where it is not known, the children are each weight against the total and the last is the remainder, neither tested"
    source: "`praxis/core/plan_weighted_slices.py` 58-62"
---
# What a weighted split refuses

Splitting a quantity across [children of differing size](when-a-weight-curve-plans-nothing.md) refuses the same two things [the even split](what-an-even-split-refuses.md) does: a total that is not a finite exact figure above nought, and fewer than two children — counted here as the number of weights given.

## What the weights are not asked

Anything. The weights are read for how many there are and for nothing else: not for being above nought, not for adding to one, not for their kind.

Those demands are made where the settings a run was asked for are checked, before the split is reached. The split itself takes what it is handed.

## What that lets through

Where the venue's lot size is known, each child but the last is rounded down to it, and a child coming to nought or below is refused there and then. A weight below nought is caught by that same test.

Take the lot size away and that test goes with it. A weight below nought then gives a child below nought, and the split hands it back — to be refused later, as the order's own instruction is built, in the same place [a child of nothing](when-a-weight-curve-plans-nothing.md) is caught.

## Related

- [What an even split refuses](what-an-even-split-refuses.md)
- [When a weight curve plans nothing](when-a-weight-curve-plans-nothing.md)
- [Work fed out over time](work-fed-out-over-time.md)
