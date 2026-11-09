---
row: N19-01
baseline: 49aa659
created: 2026-11-08 15:24 UTC
modified: 2026-11-08 15:24 UTC
evidence:
  - claim: "A limit given must be a figure of the exact kind, finite, and at or above nought"
    source: "`nexus/core/validator/risk_stage.py` 36-48 into 49-53"
  - claim: "Where a limit is left out, the comparison for that figure is skipped, and nothing reads the missing limit as nought"
    source: "`nexus/core/validator/risk_stage.py` 112-113"
  - claim: "All seven figures are read whether or not a limit is set for them, each paired with its limit before the walk begins"
    source: "`nexus/core/validator/risk_stage.py` 66-109, the seven worked out together at `nexus/core/domain/risk_state.py` 315-324"
  - claim: "The comparison is strictly above, so a figure standing exactly at its limit passes"
    source: "`nexus/core/validator/risk_stage.py` 114"
  - claim: "A limit of nought is allowed, and turns back any figure of that measure above nought"
    source: "`nexus/core/validator/risk_stage.py` 48 admitting it, against 114"
---
# What a risk limit must be

Each of the seven limits [the risk stage weighs against](what-each-check-weighs.md) may be left out; one that is given must be a figure of the exact kind, finite, and at or above nought.

## Left out, and set to nought

Where a limit is left out, the comparison for its figure is skipped. Nothing reads the missing limit as nought.

The figure itself is still read. All seven are worked out from the account's record and paired with their limits before the walk begins, so leaving a limit out saves the comparison and nothing else.

A limit of nought is a different thing, and allowed. It turns back any figure of that measure above nought.

## Where the edge falls

The comparison is strictly above. A figure standing exactly at its limit passes.

So a limit is the largest figure still allowed rather than the smallest refused, and a limit of nought lets a figure of nought through.

## Related

- [What each check weighs](what-each-check-weighs.md)
- [How far down the account is](how-far-down-the-account-is.md)
- [The levels the risk stage never reaches](the-levels-the-risk-stage-never-reaches.md)
