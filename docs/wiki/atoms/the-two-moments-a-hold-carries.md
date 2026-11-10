---
row: N13-02
baseline: 49aa659
created: 2026-11-08 05:22 UTC
modified: 2026-11-08 05:22 UTC
evidence:
  - claim: "A capital lock carries the moment it was made at and the moment it runs out at, and they are the only pair of its fields it weighs against each other"
    source: "`nexus/core/capital_controller/reservation.py` 42-84, which puts two of its fields side by side at 82 and nowhere else"
  - claim: "Each must be a moment, and each must carry the UTC marker itself"
    source: "`nexus/core/capital_controller/reservation.py` 66-68, or 70-72, or 74-76, or 78-80"
  - claim: "The moment it runs out at must stand strictly after the moment it was made at, so two moments at one instant are refused"
    source: "`nexus/core/capital_controller/reservation.py` 82-84, which refuses them equal"
---
# The two moments a hold carries

A capital lock carries the moment it was made at and the moment it runs out at, and they are the only pair of its fields it weighs against each other.

## The marker each must carry

Each must be a moment, and each must carry [the universal-time marker itself](the-marker-a-commands-moment-must-carry.md) rather than a zone standing at that offset.

## The order they must stand in

The moment it runs out at must stand strictly after the moment it was made at. Two moments at one instant are refused, so a lock cannot run out at the instant it was made.

## Related

- [What money held for an order is checked for](what-money-held-for-an-order-is-checked-for.md)
- [What a hold is asked after it exists](what-a-hold-is-asked-after-it-exists.md)
- [When a reservation times out](when-a-reservation-times-out.md)
