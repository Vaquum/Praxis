---
row: P141-01
baseline: 49aa659
created: 2026-11-15 15:00 UTC
modified: 2026-11-15 15:00 UTC
evidence:
  - claim: "A bracket's protection counts as active where it is placed, carries a name, and reports itself active — three things tested together"
    source: "`execution_manager.py` 1057-1061"
  - claim: "The same three are tested again where a change is weighed, to gather the brackets a change may name"
    source: "`execution_manager.py` 3052-3058"
  - claim: "In the one place the three settle whether a bracket entry is amendable at all"
    source: "`execution_manager.py` 1062 into 1063, or 1064 into 1065"
  - claim: "In the other they settle which brackets the weighing of a change is given to work from"
    source: "`execution_manager.py` 3060-3065"
  - claim: "A change for an account that is not registered is refused before either is reached"
    source: "`execution_manager.py` 3047, then 3048 into 3049-3050"
  - claim: "A weighing that answers against queueing reports it and returns, leaving the request nowhere"
    source: "`execution_manager.py` 3067 into 3072"
---
# The active-protection test written twice

A bracket's protection counts as active when three things hold together — it is placed, it carries a name, and it reports itself active — and that test is written in two places.

## What each one decides

In the first, the three settle whether a bracket entry is [amendable at all](which-commands-count-as-amendable.md): an entry passing them is added to the amendable set and one failing them is discarded from it.

In the second, they settle which brackets the weighing of [a change](changing-work-already-sent.md) is given to work from. A bracket failing them is simply absent from what the weighing sees.

## Why the two agree

A change may name a bracket entry only if that entry is amendable, and both sides decide that by the same three conditions — so a bracket cannot be amendable on one road and invisible on the other.

The two are forty lines and two thousand apart, and neither mentions the other.

## What the change's road does first

A change for an account that is not registered is refused before either test is reached.

And a weighing that answers against queueing reports it and returns, leaving the request nowhere at all — neither queued nor refused to its caller.

## Related

- [Which commands count as amendable](which-commands-count-as-amendable.md)
- [Changing work already sent](changing-work-already-sent.md)
- [Protection](protection.md)
