---
row: N13-06
baseline: 49aa659
created: 2026-11-08 15:40 UTC
modified: 2026-11-08 16:55 UTC
evidence:
  - claim: "A note is refused unless the flag saying the order grows a position is a yes-or-no"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 91-93"
  - claim: "The side is checked separately, and nothing weighs the flag against it"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 87-89, with 70-139 comparing the two nowhere"
  - claim: "Whether the order reduces a position is that same flag turned round, worked out on each reading rather than read from a field"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 145, which negates it"
  - claim: "The note carries a second yes-or-no, and a note is refused where it stands true and the growing flag stands true as well"
    source: "`nexus/infrastructure/praxis_connector/order_context.py` 137-139"
---
# The flag saying an order grows a position

A note carries a flag saying whether the order grows a position, and it is refused unless that flag is a yes-or-no.

## What is never asked

Whether it agrees with the side. The side is checked separately, and the two are compared nowhere, so a buy may be marked as growing a position or as reducing one, and a sell either way too.

## Read the other way round

Whether the order reduces a position is the same flag turned round. That answer is worked out on each reading rather than read from a field of its own.

## The flag it cannot stand with

The note carries a second yes-or-no. The two cannot both stand true: a note is refused where this one says yes and the growing flag says yes as well. Either one standing false clears that check.

## Related

- [What a note for an outcome is checked for](what-a-note-for-an-outcome-is-checked-for.md)
- [The size a note may leave out](the-size-a-note-may-leave-out.md)
- [When an entry's position grows](when-an-entrys-position-grows.md)
- [What Praxis works out for an exit](what-praxis-works-out-for-an-exit.md)
