---
row: N13-04
baseline: 49aa659
created: 2026-11-08 15:40 UTC
modified: 2026-11-08 16:55 UTC
evidence:
  - claim: "A note is refused unless the reference of the command it belongs to and the reference of the strategy that owns it are each text with something left in them once trimmed"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 73-75, or 77-79"
  - claim: "A trade's reference may be left out, and one that is given is held to the same rule, the test for it standing behind a test for its absence"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 81 into 82-85"
  - claim: "Its side must be one of the named ones"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 87-89"
  - claim: "Both its yes-or-no fields must be yes-or-no"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 91-93, or 133-135"
  - claim: "Its worth and the fees expected with it must each be a finite figure"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 111-116, or 122-127"
  - claim: "The worth must stand above nought where the fees need only be at or above it"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 118-120, against 129-131"
---
# What a note for an outcome is checked for

A note is refused for failing any one of a fixed list of checks.

## What must be there

The reference of the command it belongs to, and the reference of the strategy that owns it, each text with something left once the blank space is trimmed off. Its side, which must be one of the named ones. Both its yes-or-no fields, each of which must be a yes-or-no.

## What may be left out and is checked anyway

A trade's reference may be absent. One that is given is held to the same rule as the other two references, the test for it standing behind a test for its absence, so leaving it out is never what these checks turn back.

[The size](the-size-a-note-may-leave-out.md) may be absent too, under a rule of its own.

## The two figures

The worth it carries, and the fees expected with it. Each must be a finite figure.

The worth must stand above nought. The fees need only be at or above it, so nought is allowed for the fee and refused for the worth.

## Related

- [The size a note may leave out](the-size-a-note-may-leave-out.md)
- [The flag saying an order grows a position](the-flag-saying-an-order-grows-a-position.md)
