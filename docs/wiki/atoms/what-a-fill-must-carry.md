---
row: N12-02
baseline: 49aa659
created: 2026-11-08 02:08 UTC
modified: 2026-11-08 02:08 UTC
evidence:
  - claim: "One test on the kind sends an outcome to the list for a fill or the list for anything else, so it is held to one of the two and never to both"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 114 into 115, or else 117"
  - claim: "A fill must carry four things, each refused where it is absent: a size, a price, an amount, and the fees paid"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 183-185, or 195-197, or 207-209, or 222-224"
  - claim: "Each of the four must be a finite figure"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 187-189, or 199-201, or 211-216, or 226-231"
  - claim: "The first three must stand above nought where the fees need only be at or above it"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 191-193, or 203-205, or 218-220, against 233-235"
  - claim: "An outcome carrying no fill must carry none of those four, each refused on its own"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 117 into 240-242, or 244-246, or 248-250, or 252-254"
---
# What a fill must carry

Four things are required of an outcome that reports something filled, and forbidden to every other kind.

## The choice

A single test on the kind sends the record either to the list for a fill or to the list for anything else. One of the two runs, so a record is held to one list and never to both.

## The four it must carry

A fill must carry a size, a price, an amount, and the fees paid. Each is refused where it is absent, and refused again where it is not a finite figure.

Three of them must stand above nought. The fees need only be at or above it, so nought is allowed for the fees and refused for the other three.

## The far side

An outcome carrying no fill must carry none of the four, each one refused on its own. The same four figures are required by one list and turned back by the other.


## Related

- [What an outcome is checked for](what-an-outcome-is-checked-for.md)
- [The reason an outcome may carry](the-reason-an-outcome-may-carry.md)
- [The two measures an outcome reports](the-two-measures-an-outcome-reports.md)
