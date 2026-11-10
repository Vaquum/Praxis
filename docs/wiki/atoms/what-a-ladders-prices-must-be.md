---
row: P10-01
baseline: 49aa659
created: 2026-11-08 13:40 UTC
modified: 2026-11-08 13:40 UTC
evidence:
  - claim: "Each of a ladder's prices must be a positive finite decimal"
    source: "`praxis/core/domain/ladder_dca_params.py` 47 into 48-50"
  - claim: "The prices must rise throughout or fall throughout"
    source: "`praxis/core/domain/ladder_dca_params.py` 52-54 into 55-57"
  - claim: "A repeat among them is refused by that same test"
    source: "`praxis/core/domain/ladder_dca_params.py` 53 and 54, both of which a repeated pair fails, into 55-57"
  - claim: "A ladder may descend as well as rise, either answer satisfying the test"
    source: "`praxis/core/domain/ladder_dca_params.py` 53, or 54, either satisfying 55"
---
# What a ladder's prices must be

The prices an amount is spread across are held to two rules, and the second of them does two jobs.

## Each on its own

A positive finite decimal. A price of nought, a negative one, or an infinity is refused.

## All of them together

The prices must rise throughout or fall throughout. Each neighbouring pair is compared, and the ladder passes where every pair rises or every pair falls.

A ladder may descend as well as rise — buying down a falling market and selling up a rising one are both allowed, and the test does not say which direction suits which side.

## Why that forbids a repeat

A repeated price makes a pair that neither rises nor falls. That pair fails the rising test and the falling test alike, so the ladder is refused without any check looking for duplicates.

So the rule that puts the prices in order is the same rule that keeps them distinct, and [the article on orders at several prices](orders-at-several-prices.md) has the count they must reach.

## Related

- [Orders at several prices](orders-at-several-prices.md)
- [What a ladder's weights must come to](what-a-ladders-weights-must-come-to.md)
