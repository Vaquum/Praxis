---
row: P18-01
baseline: 49aa659
created: 2026-11-10 19:00 UTC
modified: 2026-11-10 19:00 UTC
evidence:
  - claim: "A start reads the state from the snapshot and then lets any record of a state change the log still holds replace it"
    source: "`nexus/infrastructure/state_store.py` 260-261 into 266-267, the records appended again as the host runs at 198-207"
  - claim: "Where no snapshot file is there, the read answers nothing at all rather than failing"
    source: "`nexus/infrastructure/snapshot.py` 66-68"
  - claim: "It then works each strategy's losses and realized result out again from what the log still holds, while the peaks and the deepest fall are kept at whichever is larger, the stored figure or the new one"
    source: "`nexus/infrastructure/state_store.py` 314-324, the peaks kept at 325-327 and at `nexus/core/domain/risk_state.py` 243-251 and 266-270 through 333"
---
# What a start reads back from a checkpoint

A start builds its state from [the snapshot](what-a-checkpoint-holds.md) and then lets any record of a state change the log still holds replace what it read.

## Where there is no snapshot

The read answers nothing at all rather than failing, so a first start and a lost file arrive at the host the same way.

## What the log adds

A checkpoint leaves no record of a state change behind it, so the records a start finds are the ones the host appended after the last checkpoint. Each replaces what the snapshot said.

## What is not taken as read

Two of the figures are worked out again rather than trusted: a start [recomputes each strategy's losses and what its trading has come to](what-the-thirty-day-cut-leaves.md) from the events the log still holds.

The peaks and the deepest fall are treated the other way about — kept at whichever is larger, the stored figure or the newly worked-out one, so neither a stale snapshot nor a thinned log can lower them.

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
