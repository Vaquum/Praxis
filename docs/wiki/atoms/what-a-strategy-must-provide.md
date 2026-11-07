---
row: N10-03
baseline: 49aa659
created: 2026-11-07 04:30 UTC
modified: 2026-11-07 04:30 UTC
evidence:
  - claim: "Seven of the eight things a strategy can be asked must be supplied by it"
    source: "`nexus/strategy/base.py` 51-52, 64-65, 77-78, 98-99, 120-121, 142-143 and 164-165"
  - claim: "The eighth is supplied already, with a body that discards what it is handed"
    source: "`nexus/strategy/base.py` 196, the whole body of it"
---
# What a strategy must provide

A strategy must supply seven of the eight things it can be asked for, and may leave the eighth alone.

## The seven

Beginning, [a prediction](what-the-prediction-loops-stop-leaves-running.md), [an outcome](which-fills-come-back-with-a-result.md), [a timer](what-a-turn-of-a-timer-does.md), [stopping](what-a-strategy-is-handed-when-it-is-asked-to-stop.md), [handing over its state to keep](what-a-stopping-host-saves-of-its-strategies.md), and [taking that state back](what-a-start-does-with-a-strategys-saved-state.md). A strategy that leaves any of them out cannot be built at all.

## The eighth

[Being replayed an event](which-roads-reach-a-strategy.md) is supplied already. The body that is there takes the record it is handed and discards it.

## Related

- [The wrapper every strategy sits behind](the-wrapper-every-strategy-sits-behind.md)
- [Which roads reach a strategy](which-roads-reach-a-strategy.md)
- [What a strategy is handed](what-a-strategy-is-handed.md)
