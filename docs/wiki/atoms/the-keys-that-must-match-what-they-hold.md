---
row: N40-01
baseline: 49aa659
created: 2026-11-08 16:54 UTC
modified: 2026-11-08 16:54 UTC
evidence:
  - claim: "The mapping of positions refuses a value that is not a position, and refuses a key differing from the trade name inside its value"
    source: "`nexus/core/domain/instance_state.py` 87-92, or 93-95"
  - claim: "The mapping of per-strategy modes refuses the same two things, against the strategy name inside its value"
    source: "`nexus/core/domain/instance_state.py` 97-100, or 101-103"
  - claim: "The mapping of dust refuses a key that is not text with something left once trimmed, and a figure that is not finite, of the exact kind, and at or above nought"
    source: "`nexus/core/domain/instance_state.py` 106-108, or 109-118"
  - claim: "Both sets of names already worked through refuse an entry that is not text with something left once trimmed"
    source: "`nexus/core/domain/instance_state.py` 120-123, or 125-128"
  - claim: "Five of the eleven fields are walked, the other six taken as they arrive"
    source: "`nexus/core/domain/instance_state.py` 87, 97, 105, 120 and 125, against the fields declared at 72-82"
---
# The keys that must match what they hold

Two of the mappings [the state a host holds](what-a-checkpoint-holds.md) carries are filed under a name that also sits inside the thing filed. Each refuses a key that disagrees with it.

## The two that must agree

The positions, filed under the name of the trade. The per-strategy modes, filed under the name of the strategy.

For each, a value of the wrong kind is refused, and a key differing from the name inside its own value is refused — so the filing cannot say one thing while the record says another.

## The three checked for shape alone

The dust kept per trading pair refuses a key that is not text with something left once trimmed, and a figure that is not finite, of the exact kind, and at or above nought.

The two sets of names already worked through — one of outcomes, one of dust closings — each refuse an entry that is not text with something left once trimmed.

None of these three carries a name inside its value, so none has anything to agree with.

## What is taken as it arrives

Five of the eleven fields are walked. The money, the risk figures, the mode, the two kinds of hold, and the mode a reading last gave are taken as they come — each being a record that [checks itself](what-the-capital-record-refuses.md) as it is built.

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [What the capital record refuses](what-the-capital-record-refuses.md)
- [What a tracked order must be](what-a-tracked-order-must-be.md)
