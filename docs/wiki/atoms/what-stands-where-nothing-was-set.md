---
row: N18-04
baseline: 49aa659
created: 2026-11-08 10:55 UTC
modified: 2026-11-08 10:55 UTC
evidence:
  - claim: "Asking a signal for a value it does not hold answers with whatever the asking named as its default"
    source: "`nexus/strategy/signal.py` 94"
  - claim: "All three limits that trip the breakers are absent unless set"
    source: "`nexus/core/domain/risk_breaker_thresholds.py` 25-27"
  - claim: "An absent limit is passed over before that limit's own figure is looked at"
    source: "`nexus/core/domain/risk_breaker_thresholds.py` 35 into 36"
---
# What stands where nothing was set

Two records on this side give an answer for something nobody set, and each puts the choice in a different place.

## The signal's answer

Asking a signal for a value it does not hold gives back whatever the asking named as its default. The record takes no view: a caller decides for itself what a missing value means, and two callers asking for the same missing key may get different answers.

## The policy's answer

All three limits that trip the breakers are absent unless set. A policy built with none given has every limit absent, and [an absent limit is passed over](the-limits-that-may-be-left-out.md) before its own figure is looked at.

So a policy nobody configured turns every breaker off, and it does that without a line saying so — the absence is the whole of the instruction.

## The difference

One record hands the choice to the caller at the moment of asking. The other fixes it at the moment of building, by leaving the field empty. Neither records anywhere that a default was taken, so a reader of either cannot tell a value that was set from one that was never given.

## Related

- [What a predictor's signal is checked for](what-a-predictors-signal-is-checked-for.md)
- [The limits that may be left out](the-limits-that-may-be-left-out.md)
