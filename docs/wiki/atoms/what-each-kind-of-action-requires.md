---
row: N67-03
baseline: 49aa659
created: 2026-11-08 20:17 UTC
modified: 2026-11-08 20:17 UTC
evidence:
  - claim: "An entry gathers five missing fields into one complaint naming all of them: the direction, a size or an amount of money, the way of working, the kind of order and the deadline"
    source: "`nexus/strategy/action.py` 176-189"
  - claim: "Past that, an entry carrying both a size and an amount of money is refused"
    source: "`nexus/strategy/action.py` 191-193"
  - claim: "An exit gathers its two into one complaint and then refuses an amount of money outright"
    source: "`nexus/strategy/action.py` 215-222, then 224-226"
  - claim: "A change gathers its three into one complaint: the command's reference, the way of working and the fields to rewrite"
    source: "`nexus/strategy/action.py` 229-238"
  - claim: "An abandonment asks for the command's reference alone, named directly rather than gathered"
    source: "`nexus/strategy/action.py` 241-243"
  - claim: "The four kinds are weighed in turn and nothing weighs a kind that is none of them, the first test having already refused one"
    source: "`nexus/strategy/action.py` 175, or 214, or 228, or 240, with 77-79 standing before"
---
# What each kind of action requires

Past [the checks every field gets](what-a-strategys-action-is-checked-for.md), an action is weighed against what its own kind needs.

## An entry

Five fields are needed: the direction, a size or an amount of money to spend, the way of working, the kind of order and the deadline.

Those five are gathered rather than tested one at a time, so a caller missing three of them is told about all three at once.

Past the gathering, carrying both a size and an amount of money is refused.

The gathering comes first, so giving neither is reported as a missing field, and giving both alongside some other field missing is reported as the missing field. The conflict is heard only where nothing else is wanting.

[An entry carrying an amount of money rather than a size](when-an-entry-may-name-a-sum-instead-of-a-size.md) is held to two more things.

## An exit

Two fields are needed, gathered the same way: the trade's reference and a size.

An amount of money is then refused outright, so an exit says a size and never a sum to receive.

Nothing here asks for a direction. An exit naming a buy, or naming no direction at all, is as acceptable as one naming a sell.

## A change

Three are needed and gathered: the command's reference, the way of working, and the fields to rewrite.

## An abandonment

The command's reference alone, named directly rather than gathered.

## The four in turn

The kinds are weighed one after another. Nothing weighs a kind that is none of the four, because the first check every action gets has already refused one.

## Related

- [What a strategy's action is checked for](what-a-strategys-action-is-checked-for.md)
- [The two mappings an action reseals](the-two-mappings-an-action-reseals.md)
- [When an entry may name a sum instead of a size](when-an-entry-may-name-a-sum-instead-of-a-size.md)
