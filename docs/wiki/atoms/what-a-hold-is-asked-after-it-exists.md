---
row: N13-07
baseline: 49aa659
created: 2026-11-08 05:22 UTC
modified: 2026-11-08 05:22 UTC
evidence:
  - claim: "The sum a capital lock holds altogether is its two sums added, worked out on each reading rather than read from a field"
    source: "`nexus/core/capital_controller/reservation.py` 90, which adds the two"
  - claim: "None of the checks the lock makes on itself names that sum"
    source: "`nexus/core/capital_controller/reservation.py` 42-84, which names it nowhere"
  - claim: "Asking whether a lock has run out refuses a moment that does not carry the UTC marker"
    source: "`nexus/core/capital_controller/reservation.py` 99-101"
  - claim: "That refusal weighs a moment handed in from outside rather than either of the lock's own"
    source: "`nexus/core/capital_controller/reservation.py` 99, which tests the moment it is given, against 70 and 78, which test its own two"
  - claim: "The answer is yes at the moment the lock runs out as well as past it"
    source: "`nexus/core/capital_controller/reservation.py` 103, reached rather than 101"
---
# What a hold is asked after it exists

A capital lock answers two questions once it has been built, and neither is part of building it.

## The sum it holds altogether

Its two sums added. The figure is worked out each time it is asked for rather than read from a field, and none of [the checks the lock makes on itself](what-money-held-for-an-order-is-checked-for.md) names it, so no check of the record’s own turns on it.

## Whether it has run out

Asking takes a moment and refuses one that does not carry the universal-time marker. That refusal weighs a moment handed in from outside, where every other refusal of the lock weighs a field the lock itself holds, [its own two moments](the-two-moments-a-hold-carries.md) among them.

The answer is yes at the moment the lock runs out as well as past it.

## Related

- [What money held for an order is checked for](what-money-held-for-an-order-is-checked-for.md)
- [The two moments a hold carries](the-two-moments-a-hold-carries.md)
- [When a reservation times out](when-a-reservation-times-out.md)
