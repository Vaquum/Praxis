---
row: P10-02
baseline: 49aa659
created: 2026-11-08 13:40 UTC
modified: 2026-11-08 13:40 UTC
evidence:
  - claim: "Weights may be left out, and the checking stops there where they are"
    source: "`praxis/core/domain/ladder_dca_params.py` 59-60"
  - claim: "Weights given must be a tuple of the same length as the prices"
    source: "`praxis/core/domain/ladder_dca_params.py` 62-67"
  - claim: "Each weight must be a positive finite decimal"
    source: "`praxis/core/domain/ladder_dca_params.py` 69 into 70-72"
  - claim: "The weights must come to exactly one"
    source: "`praxis/core/domain/ladder_dca_params.py` 74-76"
---
# What a ladder's weights must come to

Weights are optional, and where they are given three checks hold them, the last reading them together.

## Left out

Where no weights are given the checking stops at that point, and nothing further is asked. The amount is then split evenly instead.

## Given

They must be a tuple of the same length as [the prices](what-a-ladders-prices-must-be.md), so every price has a weight and no weight has no price.

Each must be a positive finite decimal. A weight of nought is refused, so a ladder cannot name a price it means to put nothing at.

## What they must come to

Exactly one. A set coming to a hundredth less is refused, and so is one coming to a hundredth more.

That is the only check reading the weights together, and it is the reason the other two are not enough: every weight can be positive, finite and of the right count while the set still fails to spend the amount or tries to spend more than there is.

## Related

- [What a ladder's prices must be](what-a-ladders-prices-must-be.md)
- [Orders at several prices](orders-at-several-prices.md)
