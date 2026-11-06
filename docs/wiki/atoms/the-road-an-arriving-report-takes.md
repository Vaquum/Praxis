---
row: P5-05
baseline: 49aa659
created: 2026-11-05 16:22 UTC
modified: 2026-11-06 06:59 UTC
evidence:
  - claim: "Each report the turning returns is put on the account's queue"
    source: "`praxis/launcher.py` 2988 and 2992"
  - claim: "The pass that moves the figures between them runs only where the account's wiring is published"
    source: "`praxis/launcher.py` 2985-2986 and the test at 2989 before 2990, with 2992 standing outside it"
  - claim: "That pass returns without working the report through where its command has no context registered"
    source: "`praxis/launcher.py` 2902 before the return at 2916, against the working through at 2919"
  - claim: "An outcome for an account with no queue is dropped before it is turned into reports"
    source: "`praxis/launcher.py` 2974-2983, which returns rather than reaching 2988"
  - claim: "The names a start gathers from the spine are read nowhere between the turning and the queue"
    source: "`praxis/launcher.py` 2988 and 2992, with no read of the gather at 1735-1736 between them"
---
# The road an arriving report takes

An outcome is turned into reports, and each report [the turning](outcomes-that-never-come-back.md) returns is put on the account's queue.

## The pass in between

Between the turning and the queue a report is put through the accounting, but only where the account's wiring is published, and that pass returns before working the report through where its command has no context registered. The queue takes the report either way.

## What it does not read

The names [a start gathers to decide what to send again](how-an-undelivered-outcome-is-replayed.md) are read nowhere between the turning and the queue.

## Where an outcome is dropped

An outcome for an account with no queue is dropped before it is turned into reports at all.

## Related

- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
- [Outcomes that never come back](outcomes-that-never-come-back.md)
- [An outcome waiting on a strategy](an-outcome-waiting-on-a-strategy.md)
