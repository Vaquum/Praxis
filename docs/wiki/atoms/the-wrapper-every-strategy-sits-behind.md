---
row: N10-01
baseline: 49aa659
created: 2026-11-07 04:30 UTC
modified: 2026-11-07 05:05 UTC
evidence:
  - claim: "Each strategy is wrapped as the start builds it, and the wrapper makes a lock of its own"
    source: "`nexus/startup/sequencer.py` 511-512, the wrapper making that lock at `nexus/strategy/executor.py` 33"
  - claim: "Every one of the eight ways in takes that lock and holds it across the call into the strategy"
    source: "`nexus/strategy/executor.py` 56-57, 76-77, 96-97, 116-117, 134-135, 144-145, 154-155 and 164-165"
  - claim: "The thing that routes to a strategy holds one wrapper per name"
    source: "`nexus/strategy/runner.py` 52, filled per name at 50"
---
# The wrapper every strategy sits behind

Every strategy is wrapped as the start builds it, and the wrapper makes a lock no other strategy's shares.

## What the lock holds out

Each of [the eight ways in](which-roads-reach-a-strategy.md) takes that lock and holds it across the call into the strategy, so a strategy reached through its wrapper is asked one thing at a time.

## What it does not hold out

The lock belongs to the wrapper, and there is a wrapper for each name, so the lock one strategy is held under is not the lock another is held under.

## Related

- [Which roads reach a strategy](which-roads-reach-a-strategy.md)
- [What a strategy must provide](what-a-strategy-must-provide.md)
- [What the router refuses](what-the-router-refuses.md)
