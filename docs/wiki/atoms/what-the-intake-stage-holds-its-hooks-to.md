---
row: N82-01
baseline: 49aa659
created: 2026-11-09 04:13 UTC
modified: 2026-11-09 04:13 UTC
evidence:
  - claim: "The mode check runs before any hook, and an answer from it ends the stage there"
    source: "`nexus/core/validator/intake_stage.py` 442, then 443-444"
  - claim: "The hooks are then run in the order they were given, one answer taken from each"
    source: "`nexus/core/validator/intake_stage.py` 446, then 447"
  - claim: "A hook answering with nothing lets the next one run"
    source: "`nexus/core/validator/intake_stage.py` 448-449"
  - claim: "An answer that is not a decision raises"
    source: "`nexus/core/validator/intake_stage.py` 451 into 452-453"
  - claim: "An allowing answer carrying money set aside raises, and one carrying none lets the next hook run"
    source: "`nexus/core/validator/intake_stage.py` 455 into 456 into 457-458, then 459"
  - claim: "A denying answer that names any stage but intake raises"
    source: "`nexus/core/validator/intake_stage.py` 461 into 462-463"
  - claim: "A denying answer that names intake ends the stage and is the stage's own answer"
    source: "`nexus/core/validator/intake_stage.py` 465"
  - claim: "Every hook answering nothing or allowing leaves the stage to answer allowed on its own account"
    source: "`nexus/core/validator/intake_stage.py` 467, reached only by the walk at 446 running out"
---
# What the intake stage holds its hooks to

The first stage of the validator runs a list of hooks, and raises on three things a hook can answer with.

## Before the hooks

The mode check runs first. An answer from it ends the stage there, so a host in the wrong mode never reaches a hook at all.

## The walk

The hooks run in the order they were given, and one answer is taken from each. A hook answering with nothing lets the next one run.

## The three raises

An answer that is not a decision raises. An allowing answer carrying money set aside raises — setting money aside is not intake's to do. A denying answer naming any stage but intake raises.

All three are about the answer's own shape rather than the request being judged, so a hook that breaks them stops the validation outright instead of denying the trade.

## The two endings

A denying answer that names intake ends the stage, and becomes the stage's own answer. Otherwise the walk runs out, and the stage answers allowed on its own account.

So the stage's allowed answer is its own, not any hook's: an allowing hook only declines to stop the walk.

## Related

- [The order the intake hooks stand in](the-order-the-intake-hooks-stand-in.md)
- [What intake asks of an exit](what-intake-asks-of-an-exit.md)
