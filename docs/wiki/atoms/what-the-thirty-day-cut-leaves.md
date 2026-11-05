---
row: N7-09
baseline: 49aa659
created: 2026-10-27 17:30 UTC
modified: 2026-11-05 11:10 UTC
evidence:
  - claim: "The cutoff is read off the clock as the checkpoint runs, not off anything the log holds"
    source: "`nexus/infrastructure/snapshot.py` 52 before 53, the span standing at 20"
  - claim: "So an event one checkpoint keeps a later one drops, with neither the log nor the snapshot having changed in between"
    source: "`nexus/infrastructure/snapshot.py` 52 before 53 into `nexus/infrastructure/wal.py` 291-292"
  - claim: "A checkpoint rewrites the log behind the snapshot, keeping a strategy event only where the record of it was written within the last thirty days"
    source: "`nexus/infrastructure/snapshot.py` 52-53 into `nexus/infrastructure/wal.py` 289-303, the span standing at 20"
  - claim: "Every record of a state change goes, whatever its age"
    source: "`nexus/infrastructure/wal.py` 289-292 keeping one kind only"
  - claim: "Nothing is rewritten where no log has been written yet"
    source: "`nexus/infrastructure/wal.py` 284-285"
  - claim: "A start works each strategy's rolling losses and realized result out of the events left, putting nought where a strategy has none"
    source: "`nexus/infrastructure/state_store.py` 314-324"
  - claim: "The event inside a record carries a moment of its own, taken from the outcome it was built from"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 265 inside the event built at 260-268"
  - claim: "The rolling losses read the event's own moment, dropping one older than thirty days and bucketing the rest by it"
    source: "`nexus/infrastructure/loss_derivation.py` 97-98, the buckets added to at 107, at 110 under 109, and at 113 under 112"
  - claim: "They also drop any event whose result is nought or better, so they count losses alone"
    source: "`nexus/infrastructure/loss_derivation.py` 94-95"
  - claim: "The realized result reads no moment at all, summing what the events still there come to"
    source: "`nexus/infrastructure/loss_derivation.py` 149-151"
  - claim: "Both figures pass the surviving events through one filter first, which drops a repeat of an outcome already counted and keeps every event carrying no outcome name"
    source: "`nexus/infrastructure/loss_derivation.py` 39-45, called at 93 and 149"
  - claim: "The best that strategy's trading has come to is kept at whichever is larger, the stored figure or the new total, and is held at nought or above"
    source: "`nexus/infrastructure/state_store.py` 325-327, held at `nexus/core/domain/risk_state.py` 53 before the raise at 55"
  - claim: "Nothing measures a fall from that figure, the falls being measured from the account's own peaks"
    source: "`nexus/core/domain/risk_state.py` 253 and 258, read at `nexus/core/mode_controller.py` 402-411"
---
# What the thirty-day cut leaves

The cut [a checkpoint](what-a-checkpoint-holds.md) makes keeps a strategy event only where its record was written inside the last thirty days, and drops every record of a state change whatever its age. Where no log has been written yet, nothing is rewritten.

## Where the cutoff falls

Thirty days back from the clock read as the checkpoint runs, so it stands somewhere different at every checkpoint: an event one checkpoint keeps, a later one drops, though nothing about the log or the snapshot changed in between.

## What a start makes of what is left

It works out again, for each strategy, [how much it has lost](how-far-down-the-account-is.md) over the last day, week and month, and what its trading has come to in all, putting nought where a strategy has no events left.

The two read those events differently. The losses read each event's own moment, taken from the outcome it was built from, dropping one older than thirty days by it, bucketing the rest by it, and dropping any event whose result is nought or better. The total reads no moment at all, summing whatever is left. So the old outcome recorded today counts toward the total and not toward the losses.

Both pass the events through one filter first, which drops a repeat of an outcome already counted and keeps every event carrying no outcome name.

## What survives it

The best that strategy's trading has come to is kept at whichever is larger, the stored figure or the new total, and never goes below nought — so one whose records all fell outside the cut comes back with its total at nought and that figure where it was. Nothing measures a fall from it: [the falls that are measured](how-far-down-the-account-is.md) run from the account's own peaks.

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [How far down the account is](how-far-down-the-account-is.md)

---

Created 2026-10-27 17:30 UTC · Last modified 2026-11-05 11:10 UTC
