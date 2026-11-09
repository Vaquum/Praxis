---
row: N57-02
baseline: 49aa659
created: 2026-11-08 18:12 UTC
modified: 2026-11-08 18:12 UTC
evidence:
  - claim: "Four of the five measures are held to levels that rise: alerting no higher than acting, acting no higher than halting"
    source: "`nexus/core/validator/health_stage.py` 111-115, 116-120, 121-125 and 131-135 into 323-328, and 337-342"
  - claim: "The share of the allowance used is held to levels that fall instead, a lower figure being the worse for it"
    source: "`nexus/core/validator/health_stage.py` 126-130 into 329-334, and 343-348"
  - claim: "Each comparison is made only where both the levels it names are set"
    source: "`nexus/core/validator/health_stage.py` 322, and 336"
  - claim: "So a middle level left out leaves the outer two never compared with each other"
    source: "`nexus/core/validator/health_stage.py` 322 and 336, neither comparing the outer pair"
---
# The orderings the health stage's policy insists on

The policy [the health stage](the-order-the-health-stages-checks-stand-in.md) weighs a report against requires each measure's three levels to run one way, and which way depends on the measure.

## The four that rise

For four of the five, a higher figure is the worse one. Their levels must rise: the alerting level no higher than the acting one, and the acting no higher than the halting one.

## The one that falls

The share of the venue's allowance already used runs the other way here — this stage treats a lower figure as the worse — so its levels must fall instead: alerting no lower than acting, acting no lower than halting.

A policy written for the four and applied to this one is therefore refused, with a complaint naming the measure.

## The comparison that is not made

Each comparison names two levels and is made only where both are set.

So a policy giving an alerting level and a halting one, and leaving the acting level out, has those two never compared with each other — and a pair in the wrong order passes.

## Related

- [The order the health stage's checks stand in](the-order-the-health-stages-checks-stand-in.md)
- [What the health policy refuses](what-the-health-policy-refuses.md) — the orderings the separate weigher insists on, over thresholds of its own
- [What each check weighs](what-each-check-weighs.md)
