---
row: P18-02
baseline: 49aa659
created: 2026-11-10 20:00 UTC
modified: 2026-11-10 21:00 UTC
evidence:
  - claim: "The weighted split makes the same two checks as the even one, its count being the number of weights"
    source: "`praxis/core/plan_weighted_slices.py` 50-52, or 54-56"
  - claim: "It asks nothing of the weights themselves, using each of them without testing it"
    source: "`praxis/core/plan_weighted_slices.py` 50-56 testing only how many there are, the values used at 59 or at 66"
  - claim: "The two records that carry weights into it demand positive finite figures of the exact kind, adding to one"
    source: "`praxis/core/domain/scheduled_vwap_params.py` 54-60 and 62-64, or `praxis/core/domain/ladder_dca_params.py` 69-72 and 74-76, handed over at `praxis/core/execution_manager.py` 489 or 516"
  - claim: "The last weight is never read: the last child is what the others left of the total"
    source: "`praxis/core/plan_weighted_slices.py` 59-60, or 65 and 76, each walking every weight but the last"
---
# What a weighted split asks of its weights

Splitting a quantity across [children of differing size](when-a-weight-curve-plans-nothing.md) refuses the same two things [the even split](what-an-even-split-refuses.md) does: a total that is not a finite exact figure above nought, and fewer than two children — counted here as the number of weights given.

## Of the weights, nothing

The weights are used without being tested. Nothing here asks whether one is of the exact kind, whether it stands above nought, or what they add to.

Those demands are made by the records that carry the weights in. Both of them — the one for work spread over a schedule, and the one for a ladder — require every weight to be a finite figure of the exact kind above nought, and require the weights to add to one. So nothing arriving by either road carries a weight the split would have to cope with.

## The last weight is never read

Each child but the last is its own weight against the total. The last is what the others left of the total, on both roads: it is never the last weight against anything.

The weights adding to one is what makes those two the same thing. Take that rule away and the last child would answer to the total rather than to the share its weight asked for — which is why the rule sits in the records rather than here.

## Related

- [What an even split refuses](what-an-even-split-refuses.md)
- [When a weight curve plans nothing](when-a-weight-curve-plans-nothing.md)
- [Work fed out over time](work-fed-out-over-time.md)
