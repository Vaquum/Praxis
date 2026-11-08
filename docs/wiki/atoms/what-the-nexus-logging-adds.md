---
row: P7-05
baseline: 49aa659
created: 2026-11-09 07:30 UTC
modified: 2026-11-09 07:30 UTC
evidence:
  - claim: "The Nexus arrangement binds context for the length of a block and puts the keys it was given back as they stood, on the way out through a raise as much as the way out through the end"
    source: "`nexus/infrastructure/observability.py` 121-122"
  - claim: "The Praxis arrangement binds context with nothing to put anything back at"
    source: "`praxis/infrastructure/observability.py` 98"
  - claim: "The level is looked up the same way on both sides, and the root is emptied of its handlers the same way"
    source: "`nexus/infrastructure/observability.py` 45, the same statement at `praxis/infrastructure/observability.py` 45, and `nexus/infrastructure/observability.py` 81-82, the same at `praxis/infrastructure/observability.py` 81-82"
---
# What the Nexus logging adds

Nexus binds context for the length of a block, putting back whatever stood before once the block is done.

## The scoped binding

Entering the block binds what it was given; leaving it puts those same keys back as they stood. That holds on the way out through a raise as much as on the way out through the end. It reaches the keys it was given and no others. One of those bound again inside the block is put back as it stood on the way out; a different key bound inside stays bound after it.

## What it sits beside

The plain binding either side has puts nothing back of its own accord. The Praxis arrangement has that one and no other.

## What the two arrangements share

[The level looked up by name](what-a-host-writes-about-itself.md) and [the root emptied of its handlers](what-the-logging-arrangement-misses.md) are the same statements on both sides, so what those two articles say about the level and about the root holds of Nexus too.

## Related

- [What a host writes about itself](what-a-host-writes-about-itself.md)
- [What the logging arrangement misses](what-the-logging-arrangement-misses.md)
