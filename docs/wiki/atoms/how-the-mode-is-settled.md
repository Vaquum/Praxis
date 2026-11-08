---
row: N15-03
baseline: 49aa659
created: 2026-11-09 14:00 UTC
modified: 2026-11-09 14:00 UTC
evidence:
  - claim: "Five measures are weighed against their halting thresholds in one chain, and the halted mode is answered where any of them reaches its own"
    source: "`nexus/core/health_evaluator.py` 167-174"
  - claim: "Four are then weighed against their acting thresholds in a second chain, and the entries-blocked mode answered where any reaches its own"
    source: "`nexus/core/health_evaluator.py` 176-182, reached rather than 174"
  - claim: "The active mode is answered where neither chain fires"
    source: "`nexus/core/health_evaluator.py` 184, reached rather than 174 or 182"
  - claim: "Each comparison is reached rather than passed, so a measure standing exactly at its threshold fires the chain"
    source: "`nexus/core/health_evaluator.py` 168-172, or 177-180"
  - claim: "The drift from the exchange's clock is weighed in the first chain and named in neither the second nor what follows it"
    source: "`nexus/core/health_evaluator.py` 172, with 176-184 naming it nowhere"
---
# How the mode is settled

Two chains in turn settle whether an account may trade, and the worse answer wins.

## The halting chain

Five measures are weighed against their halting thresholds in one chain: how long requests are taking, the count of failures in a row, the share that failed, the share of the allowance in use, and how far the clock has drifted. Any one of them reaching its own threshold answers halted, and nothing further is weighed.

Each comparison is reached rather than passed, so a measure standing exactly at its threshold fires the chain.

## The acting chain

Four are then weighed against their acting thresholds, the drift left out. Any one reaching its own answers entries blocked.

## Neither

Where neither chain fires, the active mode is answered.

So the answer is the worst of the measures rather than a sum of them: one measure far past its threshold and four at nought gives the same answer as all five past theirs.

## The drift that has one chain only

The drift is weighed in the halting chain and named in neither the acting one nor what follows it. So drift either halts an account or counts for nothing, where every other measure has a step between.

## Related

- [What a health snapshot refuses](what-a-health-snapshot-refuses.md)
- [What the health policy refuses](what-the-health-policy-refuses.md)
- [The thresholds nothing weighs against](the-thresholds-nothing-weighs-against.md)
