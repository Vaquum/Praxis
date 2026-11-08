---
row: N14-04
baseline: 49aa659
created: 2026-11-08 23:20 UTC
modified: 2026-11-08 23:20 UTC
evidence:
  - claim: "A signal copies the mapping it was handed and seals the copy over the field it arrived in"
    source: "`nexus/strategy/signal.py` 61"
  - claim: "The settings a strategy is configured with are sealed by the same line"
    source: "`nexus/strategy/params.py` 31"
  - claim: "The settings on the instruction Nexus sends are sealed by the same line again"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 187-191"
  - claim: "Each of the three copies the mapping's entries and not the objects those entries hold, so a caller reaching into one of those objects and altering it alters what the record holds"
    source: "`nexus/strategy/signal.py` 61, or `nexus/strategy/params.py` 31, or `nexus/infrastructure/praxis_connector/trade_command.py` 187-191, each copying the mapping alone"
  - claim: "A signal shipped across a process boundary is rebuilt from three parts with its values handed over unsealed"
    source: "`nexus/strategy/signal.py` 78-81"
  - claim: "The rebuilding runs every one of the signal's checks again and seals the values afresh"
    source: "`nexus/strategy/signal.py` 78-79 reaching 29-59, sealed again at 61"
---
# The sealing three records do

Three records on the Nexus side copy a mapping they were handed and seal the copy over the field it arrived in, by one statement each.

## What the sealing reaches

A caller that keeps the mapping it handed over can still add to it, take from it, or put something else in place of what a key held. None of that reaches the record: the record holds a copy, and the copy is sealed, so neither the caller's changes nor anything done through the record itself can alter which entries it has.

## What it leaves alone

The copy is of the mapping, not of what the mapping holds. Each entry still points at the object the caller handed in. So a caller that reaches into one of those objects and alters it alters what the record holds, and the sealing does not stand in the way.

This is true of all three the same way, [the settings on the instruction Nexus sends](the-settings-a-command-rewrites.md) among them.

## What crossing a process boundary does

A signal cannot be shipped as it stands, because a sealed mapping cannot be. Shipping it hands over three parts with the values unsealed, and the record built on the far side runs every one of [the signal's checks](what-a-predictors-signal-is-checked-for.md) again and seals the values afresh.

So what crosses is the sealing undone and then done again, and a signal that arrives has been checked twice.

## Related

- [What a predictor's signal is checked for](what-a-predictors-signal-is-checked-for.md)
- [What a strategy's settings ask and answer](what-a-strategys-settings-ask-and-answer.md)
- [The settings a command rewrites](the-settings-a-command-rewrites.md)
