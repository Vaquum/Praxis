---
row: N15-04
baseline: 49aa659
created: 2026-11-08 10:13 UTC
modified: 2026-11-08 10:13 UTC
evidence:
  - claim: "Four of the policy's thirteen thresholds are the alerting ones, and the two chains that settle the mode name none of the four"
    source: "`nexus/core/health_evaluator.py` 165-184, which names none of them, the four declared at 81, 84, 87 and 90"
  - claim: "Each of the four is checked as the policy is built, by the walks over single fields"
    source: "`nexus/core/health_evaluator.py` 98-103 into 105-107, or 109-111 into 112-113"
  - claim: "Each of the four is read again by the ordering that holds its measure's three thresholds in line"
    source: "`nexus/core/health_evaluator.py` 115, or 119, or 123, or 127"
---
# The thresholds nothing weighs against

Four of the policy's thirteen thresholds are checked as it is built, read by an ordering, and weighed against no measure at all.

## Which four

The alerting threshold of each measure that has three: how long requests are taking, the count of failures in a row, the share that failed, and the share of the allowance in use.

## What checks them

Each is held to the same rules as its neighbours as the policy is built, and each is read again by the ordering that keeps its measure's three thresholds in line — so an alerting threshold above the acting one is refused.

## What does not

[Neither chain that settles the mode](how-the-mode-is-settled.md) names any of the four. A reader setting one of them changes what the policy will accept and nothing about what it decides.

## Related

- [How the mode is settled](how-the-mode-is-settled.md)
- [What the health policy refuses](what-the-health-policy-refuses.md)
