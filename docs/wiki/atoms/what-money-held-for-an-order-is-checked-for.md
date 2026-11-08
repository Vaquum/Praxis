---
row: N13-01
baseline: 49aa659
created: 2026-11-08 15:40 UTC
modified: 2026-11-08 16:55 UTC
evidence:
  - claim: "A capital lock is refused unless its own reference and the reference of the strategy that asked for it are each text with something left in them once trimmed"
    source: "`nexus/core/capital_controller/reservation.py` 42-44, or 46-48"
  - claim: "The two sums it holds must each be a finite figure at or above nought"
    source: "`nexus/core/capital_controller/reservation.py` 50-56, or 58-64"
  - claim: "Each of those two checks refuses a figure below nought and not one standing at it"
    source: "`nexus/core/capital_controller/reservation.py` 53, or 61"
---
# What money held for an order is checked for

A capital lock is refused for failing any one of a fixed list of checks.

## The two references

Its own reference, and the reference of the strategy that asked for it, each text with something left once the blank space is trimmed off.

## The two sums

The worth held for the order, and the fees expected with it. Each must be a finite figure at or above nought.

Each of the two checks refuses a figure below nought rather than one standing at it, so nought at both is not what turns a lock back.

## Related

- [The two moments a hold carries](the-two-moments-a-hold-carries.md)
- [What a hold is asked after it exists](what-a-hold-is-asked-after-it-exists.md)
- [What the record of an attempt must carry](what-the-record-of-an-attempt-must-carry.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
