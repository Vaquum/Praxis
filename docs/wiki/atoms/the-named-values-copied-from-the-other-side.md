---
row: N16-06
baseline: 49aa659
created: 2026-11-08 10:26 UTC
modified: 2026-11-08 10:26 UTC
evidence:
  - claim: "The three sets hold the same words as the trading side's own, at these commits"
    source: "`nexus/core/domain/order_types.py` 18-24, 30-37 and 43-45, against `praxis/core/domain/enums.py` 119-125, 66-73 and 147-149"
  - claim: "Seven ways of working an order are named"
    source: "`nexus/core/domain/order_types.py` 18-24"
  - claim: "Eight kinds of order are named"
    source: "`nexus/core/domain/order_types.py` 30-37"
  - claim: "Three preferences for who takes the other side are named"
    source: "`nexus/core/domain/order_types.py` 43-45"
  - claim: "The record carrying outcomes in asks nothing of the queue or the wait it is given"
    source: "`nexus/infrastructure/praxis_connector/praxis_inbound.py` 32-33, with 27-33 weighing neither"
  - claim: "That wait has a default of a tenth of a second"
    source: "`nexus/infrastructure/praxis_connector/praxis_inbound.py` 16, taken as the default at 33"
---
# The named values copied from the other side

Three sets of named values let the strategy layer say what it wants without reaching into the trading side's own package.

## The three sets

Seven ways of working an order, eight kinds of order, and three preferences for who takes the other side.

Each is a copy rather than the thing itself: at these commits the words are the same on both sides, declared twice. Each list agrees with its counterpart only so long as both are kept so, and nothing in either checks that they are.

## The queue beside them

The record outcomes come back through is the other place on this side that asks nothing of what it is handed. It takes a queue and a wait, weighs neither, and keeps both. The wait has a default of a tenth of a second.

[What it answers with when that wait runs out](what-a-stopping-host-waits-for.md) is written elsewhere.

## Related

- [What a command is checked for](what-a-command-is-checked-for.md)
- [What a stopping host waits for](what-a-stopping-host-waits-for.md)
