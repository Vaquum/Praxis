---
row: P5-07
baseline: 49aa659
created: 2026-11-05 16:22 UTC
modified: 2026-11-06 06:59 UTC
evidence:
  - claim: "A checkpoint and a record of a state change enter the same guard before taking the log lock"
    source: "`nexus/infrastructure/state_store.py` 178 and 198, each entering 219 before the log lock"
  - claim: "The strategy-event write enters no guard before taking its lock"
    source: "`nexus/infrastructure/state_store.py` 236, with no guard entered before it"
  - claim: "The object standing as the pair's first half is set on the risk state as the build runs, and a check refuses to carry on where the pair would hold another"
    source: "`praxis/launcher.py` 4128 setting it, 2569-2576 refusing where it is another, or else 2579 putting it in the pair"
---
# Which of the store's writes take which locks

Of the store's three writes, two enter a guard before taking the log lock and one goes straight to it.

## The two that share a set

[The checkpoint](what-a-checkpoint-holds.md) and [the record of a state change](which-of-a-hosts-changes-reach-the-log.md) enter the same guard before taking the log lock — the same two steps in the same order.

## The one on its own

[The event write takes the log lock](where-a-realized-result-is-written-down.md) and enters that guard at no point.

## Which object the pair's first half must be

As the build runs, one lock is set on the risk state, and a check refuses to carry on where the pair would be given another in its place.

## Related

- [When the store writes without its locks](when-the-store-writes-without-its-locks.md)
- [Where a realized result is written down](where-a-realized-result-is-written-down.md)
