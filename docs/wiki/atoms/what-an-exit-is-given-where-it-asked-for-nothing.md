---
row: N16-03
baseline: 49aa659
created: 2026-11-08 10:26 UTC
modified: 2026-11-08 14:58 UTC
evidence:
  - claim: "An exit that left out its way of working is given one, and one that left out its kind of order is given that"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 99 into 100-101, or 102-103"
  - claim: "An exit that left out its deadline is given sixty seconds"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 104-105, the figure at 29"
  - claim: "A command carries the name of the money set aside for it, where any was set aside"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 87-89"
  - claim: "An action that is not a new order carries none of the three, each set aside instead"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 91 into 92-94, or else 96-98"
  - claim: "A new order naming a spend carries no size, and one naming no spend carries the size the request asked for, one statement settling both"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 107 into 108"
---
# What an exit is given where it asked for nothing

Three fields of an exit are filled in where the strategy left them out, and an entry gets none of that treatment.

## The three stood in

A way of working the order, a kind of order, and a deadline. Each is taken from the action where the action named one, and stood in for where it did not: the way of working becomes a single shot, the kind becomes a market order, and the deadline becomes sixty seconds.

So an exit leaving this road carries all three named, whatever the strategy said.

## Only an exit

An entry is given none of them: what it named is what it carries, and a field it left out stays out. An action of any other kind has all three set aside, before the exit's filling-in is reached.

## The name of the money

Where money was set aside for the decision, the command carries that holding's name. Where none was, it carries none, whatever the action.

## The fourth field the same choice decides

A new order naming a spend carries no size; one naming no spend carries the size the request asked for. One statement settles both, so the two can never both be there.

## Related

- [What the translation refuses](what-the-translation-refuses.md)
- [What weighs a shutdown sale](what-weighs-a-shutdown-sale.md)
- [What each kind of command must carry](what-each-kind-of-command-must-carry.md)
