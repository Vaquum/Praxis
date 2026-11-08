---
row: N57-01
baseline: 49aa659
created: 2026-11-12 14:30 UTC
modified: 2026-11-12 14:30 UTC
evidence:
  - claim: "A set of thresholds for one measure passes over any level left unset"
    source: "`nexus/core/validator/health_stage.py` 53-56"
  - claim: "It then refuses a level that is not a finite figure of the exact kind, and only past that refuses one below nought"
    source: "`nexus/core/validator/health_stage.py` 57-62, then 63-68"
  - claim: "The policy first refuses any of its five fields that is not a set of thresholds"
    source: "`nexus/core/validator/health_stage.py` 86-96"
  - claim: "It then holds the two measured as shares between nought and one, level by level, passing over an unset level"
    source: "`nexus/core/validator/health_stage.py` 98-109"
  - claim: "Only past both does it reach the orderings between a measure's levels"
    source: "`nexus/core/validator/health_stage.py` 111 onwards"
  - claim: "The snapshot holds all five of its figures to being finite figures of the exact kind before any bound is applied"
    source: "`nexus/core/validator/health_stage.py` 147-157"
  - claim: "Its bounds then come one figure at a time, three held at or above nought and two held between nought and one"
    source: "`nexus/core/validator/health_stage.py` 159-161, or 163-165, or 178-180, or 167-169, or 171-176"
---
# The order the health stage's checks stand in

[The stage weighing a health report](what-each-check-weighs.md) is handed three records, and each checks its own fields in an order that decides which complaint a bad figure is given.

## A measure's thresholds

Three levels — alerting, acting, halting — each of which may be left unset and is passed over where it is.

A level that is set is asked to be a finite figure of the exact kind. Only past that is it asked to stand at or above nought. So a level that is no number at all is refused for its kind, and never reaches the question of its sign.

## The policy

Each of its five fields must be a set of thresholds. That comes first, so a field holding a bare figure is refused for its shape before any figure in it is read.

Then the two measures that are shares are held between nought and one, level by level, with an unset level passed over.

Only past both does the policy reach [the orderings between a measure's levels](the-orderings-the-health-stages-policy-insists-on.md). So a policy whose share is above one and whose levels are also out of order is refused for the share.

## The snapshot

All five of its figures are held to being finite figures of the exact kind, in one pass.

Only then come the bounds, one figure at a time: three held at or above nought, and two — the failed share and the share of the allowance used — held between nought and one.

## Related

- [What each check weighs](what-each-check-weighs.md)
- [What the health policy refuses](what-the-health-policy-refuses.md)
- [The orderings the health stage's policy insists on](the-orderings-the-health-stages-policy-insists-on.md)
- [What a health snapshot refuses](what-a-health-snapshot-refuses.md)
