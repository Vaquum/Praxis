---
row: N14-07
baseline: 49aa659
created: 2026-11-08 06:15 UTC
modified: 2026-11-08 06:15 UTC
evidence:
  - claim: "Three limits are walked by name, and a limit left out is passed over before that limit's own figure is looked at"
    source: "`nexus/core/domain/risk_breaker_thresholds.py` 32 over the three names, with 35 into 36"
  - claim: "A limit that is given must be a finite decimal figure above nought"
    source: "`nexus/core/domain/risk_breaker_thresholds.py` 38-40"
  - claim: "A limit of nought is refused by that same line rather than let in"
    source: "`nexus/core/domain/risk_breaker_thresholds.py` 38, which refuses a figure at nought as well as below it"
---
# The limits that may be left out

Three configured limits are each allowed to be absent, and one loop decides what is asked of the ones that are there.

## Absent

The loop takes the three by name. A limit left out is passed over before that limit's own figure is looked at, so leaving one out is never what turns the record back.

The passing over is per limit, not for the record: a limit given and wrong is refused whatever the other two do.

## Given

A limit that is there must be a finite decimal figure above nought.

Nought is refused by that same line. So a limit cannot be set to nought as a way of standing down: the only way to leave a limit unset is to leave it out.

## Related

- [Which accounts are refused](which-accounts-are-refused.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
