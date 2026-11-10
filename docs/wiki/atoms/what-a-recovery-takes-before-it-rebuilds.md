---
row: N38-01
baseline: 49aa659
created: 2026-11-08 16:49 UTC
modified: 2026-11-08 16:49 UTC
evidence:
  - claim: "A recovery checks the log's marker before it reads anything"
    source: "`nexus/infrastructure/state_store.py` 259, ahead of 260-261"
  - claim: "A plain reading of the events checks it too"
    source: "`nexus/infrastructure/state_store.py` 344, ahead of 345"
  - claim: "The number the next record will carry is taken from the last record the log still holds"
    source: "`nexus/infrastructure/state_store.py` 271-272"
  - claim: "A checkpoint drops every record of a state change and keeps only recent events, so the record it continues from can be far behind the last one written"
    source: "`nexus/infrastructure/wal.py` 289-292, read back at `nexus/infrastructure/state_store.py` 261"
  - claim: "The moment the rolling losses are measured back from is read off the clock as the recovery runs"
    source: "`nexus/infrastructure/state_store.py` 286, used at 287"
  - claim: "Those losses are derived only where the log left events, and are otherwise left empty"
    source: "`nexus/infrastructure/state_store.py` 287"
---
# What a recovery takes before it rebuilds

A recovery takes three things before it rebuilds a figure: the log's marker, the number the next record will carry, and the moment to measure the losses back from.

## The marker

The log's marker is checked first, before the snapshot is opened or a record read. A plain reading of the events checks it too, so neither road into the log skips it.

## The number

The record the log ends with carries a number, and the next record the host writes carries one past it. Where the log holds nothing, the number stands where it was.

The log the recovery reads is what [the last checkpoint left](what-the-thirty-day-cut-leaves.md), which is every record of a state change gone and only recent events kept. So the record the numbering continues from can sit far behind the last record the previous run wrote, and a log left empty by that cut starts the numbering over.

## The moment

The moment the rolling losses are measured back from is read off the clock as the recovery runs — not off the snapshot, and not off the last record.

So the same log recovered an hour later measures its windows from an hour later, and an event inside a window at one recovery can be outside it at the next.

Those losses are worked out only where the log left events behind. Where it left none, they start empty, and [what a strategy is left with](what-the-thirty-day-cut-leaves.md) is decided by the rebuilding that follows.

## Related

- [What a start reads back from a checkpoint](what-a-start-reads-back-from-a-checkpoint.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
- [What a recovery writes at the end](what-a-recovery-writes-at-the-end.md)
