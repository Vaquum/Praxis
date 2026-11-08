---
row: N67-04
baseline: 49aa659
created: 2026-11-13 00:30 UTC
modified: 2026-11-13 00:30 UTC
evidence:
  - claim: "An entry must carry a size or a sum to spend, and carrying both is refused"
    source: "`nexus/strategy/action.py` 179-180 into 187-189, then 191-193"
  - claim: "Where the sum is the one carried, the entry must be a buy, refused with a complaint naming the direction that arrived"
    source: "`nexus/strategy/action.py` 195 into 200-205"
  - claim: "It must also be a market order, refused with a complaint naming the kind that arrived"
    source: "`nexus/strategy/action.py` 207-212"
  - claim: "Both tests read the direction and the kind of order as already there, by assertion rather than by a check"
    source: "`nexus/strategy/action.py` 197, and 198"
  - claim: "What makes those assertions hold is the gathering above, which has already refused an entry missing either"
    source: "`nexus/strategy/action.py` 177-178, and 183-184, into 187-189"
  - claim: "An exit is refused for carrying a sum at all, so the sum belongs to one kind of action and one direction within it"
    source: "`nexus/strategy/action.py` 224-226, against 195-212"
---
# When an entry may name a sum instead of a size

[An entry](what-each-kind-of-action-requires.md) says how much to trade either as a size in coin or as a sum of money to spend, and the sum is allowed in one case only.

## One or the other

An entry must carry one of the two. Carrying both is refused.

## The two further rules on a sum

Where the sum is the one carried, the entry must be a buy. A sell naming a sum is refused, with a complaint naming the direction that arrived.

It must also be a market order. Any other kind naming a sum is refused, with a complaint naming the kind that arrived.

So a sum of money is a way of saying "spend this much at whatever the market gives", and the two rules are what keep it to the one case where that means something.

## The assertions behind them

Both tests read the direction and the kind of order as already being there, by assertion rather than by a check.

What makes that hold is the gathering further up, which has already refused an entry missing either. The assertions therefore state what the gathering guarantees rather than guarding against anything.

## Nowhere else

An exit is refused for carrying a sum at all. So a sum belongs to one kind of action, and to one direction and one order type within it.

## Related

- [What each kind of action requires](what-each-kind-of-action-requires.md)
- [What a strategy's action is checked for](what-a-strategys-action-is-checked-for.md)
