---
row: N13-05
baseline: 49aa659
created: 2026-11-08 15:40 UTC
modified: 2026-11-08 17:30 UTC
evidence:
  - claim: "A note that leaves the size out is refused where the order reduces a position, and clears that check where it grows one"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 95 into 97-99"
  - claim: "A size that is given must be a finite figure"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 101 into 103-105"
  - claim: "A size that is given must stand above nought"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 107-109"
  - claim: "Neither check on a size that is given reads the flag saying the order grows a position"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 101-109, which names that flag nowhere"
---
# The size a note may leave out

One choice on whether a note carries a size at all decides which of two rules the size is held to.

## When it is absent

A note that leaves the size out is refused where [the order reduces a position](the-flag-saying-an-order-grows-a-position.md). Where the order grows one, an absent size clears that check.

## When it is there

A size that is given must be a finite figure, and must stand above nought. Neither of those two checks reads the flag that decided the first rule, so a size that is there is held to the same pair of tests whichever way the order goes.

## Related

- [What a note for an outcome is checked for](what-a-note-for-an-outcome-is-checked-for.md)
- [The flag saying an order grows a position](the-flag-saying-an-order-grows-a-position.md)
