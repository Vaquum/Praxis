---
row: N56-02
baseline: 49aa659
created: 2026-11-08 18:01 UTC
modified: 2026-11-08 18:01 UTC
evidence:
  - claim: "An exit must be a sell"
    source: "`nexus/core/validator/intake_stage.py` 238-244"
  - claim: "Past that, it must name a trade the state holds a position for"
    source: "`nexus/core/validator/intake_stage.py` 245-254"
  - claim: "Past that, the position must belong to the strategy asking"
    source: "`nexus/core/validator/intake_stage.py` 255-262"
  - claim: "Past that, a size must be given and must stand above nought"
    source: "`nexus/core/validator/intake_stage.py` 270-276"
  - claim: "Past that, the size must not exceed what the position has left after exits already pending"
    source: "`nexus/core/validator/intake_stage.py` 277-285"
  - claim: "An entry is asked for a buy first, and a size it gives must stand above nought"
    source: "`nexus/core/validator/intake_stage.py` 222-228, or 229-235"
---
# What intake asks of an exit

[The check on references](the-order-the-intake-hooks-stand-in.md) asks five things of an exit, each only once the one before it has passed.

## The five, in order

A sell. These two sides trade one way round — an entry buys and an exit sells — so an exit naming a buy is turned away on direction before anything looks for its trade.

A trade the state holds a position for. An exit naming nothing and one naming a trade with no position are turned away with the same reason.

A position belonging to the strategy asking. One strategy cannot exit another's, and the attempt has a reason of its own.

A size, given and above nought. Unlike an entry's, an exit's size cannot be left out.

A size within what the position has left once exits already pending are taken off. So two exits that each fit the position can still see the second turned away.

## What an entry is asked instead

A buy, first of all. Then, where a size is given, that it stand above nought — a size left out passes this hook, though the direction before it does not care either way.

## Related

- [The order the intake hooks stand in](the-order-the-intake-hooks-stand-in.md)
- [What each check weighs](what-each-check-weighs.md)
- [The roads around the checks](the-roads-around-the-checks.md)
