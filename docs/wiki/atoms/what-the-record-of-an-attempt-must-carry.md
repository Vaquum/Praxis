---
row: N13-03
baseline: 49aa659
created: 2026-11-08 05:22 UTC
modified: 2026-11-08 05:22 UTC
evidence:
  - claim: "A granted record must have something in its lock field"
    source: "`nexus/core/capital_controller/reservation.py` 123-125"
  - claim: "A granted record must leave its reason field empty"
    source: "`nexus/core/capital_controller/reservation.py` 135-137"
  - claim: "A refused record must have something in its reason field"
    source: "`nexus/core/capital_controller/reservation.py` 131-133"
  - claim: "A refused record must leave its lock field empty"
    source: "`nexus/core/capital_controller/reservation.py` 127-129"
  - claim: "No check asks the type of any of its three fields"
    source: "`nexus/core/capital_controller/reservation.py` 120-137, which names no type for any of them"
  - claim: "The lock beside it asks the type of each of its six fields"
    source: "`nexus/core/capital_controller/reservation.py` 42, 46, 51, 59, 66 and 74"
---
# What the record of an attempt must carry

A record of an attempt to hold money says whether the hold was granted, and four checks tie that answer to what comes with it.

## The four

A granted record must have something in its lock field, and must leave its reason field empty. A refused record must have something in its reason field, and must leave its lock field empty.

Each of the four stands on its own, so a record saying the hold was granted with both fields filled is turned back by the fourth of them rather than by the first.

## The fields no type is asked of

The answer all four turn on is read as a yes-or-no, and no check asks whether it is one. Neither of the other two fields has its type asked either: each is weighed only for being there or not.

[The lock beside it](what-money-held-for-an-order-is-checked-for.md) asks the type of each of its six fields.

## Related

- [What money held for an order is checked for](what-money-held-for-an-order-is-checked-for.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
