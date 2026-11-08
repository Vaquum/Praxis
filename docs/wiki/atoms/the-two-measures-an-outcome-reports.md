---
row: N12-04
baseline: 49aa659
created: 2026-11-08 06:30 UTC
modified: 2026-11-08 08:20 UTC
evidence:
  - claim: "Two measures are taken by name in one loop and read"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 166-167"
  - claim: "An absent measure is passed over before any figure is looked at, and a measure of nought goes on to the checks instead"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 169 into 170, or else 169 falling through to 172"
  - claim: "A measure given on an outcome carrying no fill is refused"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 172-174"
  - claim: "A measure given on an outcome carrying a fill must be a finite figure"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 176-178, reached rather than 172-174"
  - claim: "Neither measure is compared with nought"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 166-178, which compares neither with it"
---
# The two measures an outcome reports

An outcome may carry two measures, and one loop checks both of them by the same rule.

## An absent measure

The loop takes each measure by name and reads it. An absent one is passed over before any figure is looked at, so either may be left out and both may be.

A measure of nought is not passed over. It is a figure, and it goes on to the checks below.

## Where a measure is there

A measure given on an outcome carrying no fill is refused. So on such an outcome, leaving a measure out passes where putting nought in does not.

A measure given on an outcome [carrying a fill](what-a-fill-must-carry.md) must be a finite figure. Neither measure is compared with nought, so a measure of nought meets that requirement as readily as one either side of it.

## Related

- [What an outcome is checked for](what-an-outcome-is-checked-for.md)
- [What a fill must carry](what-a-fill-must-carry.md)
- [The reason an outcome may carry](the-reason-an-outcome-may-carry.md)
