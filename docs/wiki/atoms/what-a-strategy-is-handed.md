---
row: N10-06
baseline: 49aa659
created: 2026-11-07 04:30 UTC
modified: 2026-11-07 06:05 UTC
evidence:
  - claim: "It refuses five things as it is built: holdings that are not a sealed run, anything in that run that is not a holding, an amount that is not a decimal, an amount that is not finite or falls below nought, and a mode that is not one of the named ones"
    source: "`nexus/strategy/context.py` 35-37, or 39-42, or 44-46, or 48-50, or 52-54"
  - claim: "It is sealed against having its own fields rebound"
    source: "`nexus/strategy/context.py` 14"
  - claim: "Outside the tests, the roads that begin a strategy, hand it a prediction, hand it an outcome and turn a timer all build the settings beside it empty on the spot"
    source: "`nexus/startup/sequencer.py` 721, `nexus/strategy/predict_loop.py` 340, `nexus/core/outcome_loop.py` 423 and `nexus/strategy/timer_loop.py` 120"
---
# What a strategy is handed

What a strategy is handed is a sealed thing, checked five ways before a strategy ever sees it.

## What it will not be built from

Holdings that are not a sealed run of them. Anything in that run that is not [a holding](holdings.md). An amount that is not a decimal. An amount that is not finite, or that falls below nought. A mode that is not one of the named ones. Each of the five raises as it is built, so a strategy never sees a half-made one.

## What sealing it covers

Its own fields cannot be rebound once it is built. [What a strategy is handed when it is asked to stop](what-a-strategy-is-handed-when-it-is-asked-to-stop.md) has what it carries, the holdings inside it, and what altering one of those reaches.

## The settings beside it

Outside the tests, the roads that begin a strategy, hand it a prediction, hand it an outcome and turn a timer all build those settings empty on the spot, so the settings a strategy reads on any of them carry nothing.

## Related

- [What a strategy is handed when it is asked to stop](what-a-strategy-is-handed-when-it-is-asked-to-stop.md)
- [Which roads reach a strategy](which-roads-reach-a-strategy.md)
- [What a strategy must provide](what-a-strategy-must-provide.md)
