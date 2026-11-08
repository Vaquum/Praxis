---
row: N19-02
baseline: 49aa659
created: 2026-11-10 22:00 UTC
modified: 2026-11-10 23:00 UTC
evidence:
  - claim: "The walk answers with a breach where a figure is over its limit, and with nothing where none is"
    source: "`nexus/core/validator/risk_stage.py` 115-119, or else 121"
  - claim: "Four levels exist to answer with"
    source: "`nexus/core/domain/enums.py` 41-44"
  - claim: "The test the answer meets turns a breach or a halt into a refusal, and a halt cannot arrive from this walk"
    source: "`nexus/core/validator/risk_stage.py` 133-139, against 115-119, or else 121, as the only answers"
  - claim: "An answer of nothing allows the decision"
    source: "`nexus/core/validator/risk_stage.py` 141"
  - claim: "The health stage, under the same test, does produce a halt"
    source: "`nexus/core/validator/health_stage.py` 257, tested at 359"
  - claim: "The figures weighed are taken from the account's own risk record as the stage begins"
    source: "`nexus/core/validator/risk_stage.py` 130-131"
---
# The levels the risk stage never reaches

The walk over [the account's losses](what-each-check-weighs.md) answers with a breach where a figure is over its limit, and with nothing where none is. Two of the four levels it could answer with it never does.

## The four, and the two

A warning, a breach, a halt, and nothing. The walk produces a breach or nothing.

The test its answer then meets turns a breach or a halt into a refusal. Half of that test is dead: no halt can arrive from this walk, so a refusal always comes from the breach arm. An answer of nothing allows the decision.

## Where that test is alive

[The health stage](what-the-health-policy-refuses.md) is written the same way and does produce a halt, so the identical test there has both arms live.

So the same line means different things in the two places, and reading it in the risk stage tells you what that stage could have answered rather than what it does.

## What it reads

The figures come from the account's own record of how far down it is, converted as the stage begins. The stage holds none of its own.

## Related

- [What a risk limit must be](what-a-risk-limit-must-be.md)
- [What each check weighs](what-each-check-weighs.md)
- [How far down the account is](how-far-down-the-account-is.md)
