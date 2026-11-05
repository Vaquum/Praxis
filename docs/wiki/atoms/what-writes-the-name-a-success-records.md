---
row: N9-04
baseline: 49aa659
created: 2026-11-03 15:40 UTC
modified: 2026-11-05 11:10 UTC
evidence:
  - claim: "The name a success records goes onto the state object a write serializes, and is put out with the rest of that state by whatever write comes next"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 165 onto the object kept at 63, which `praxis/launcher.py` 4343 hands it, serialized by a later write at `praxis/launcher.py` 3549 into `nexus/infrastructure/state_store.py` 199, or by a checkpoint at 179 into `nexus/infrastructure/snapshot.py` 45, the set copied at `nexus/infrastructure/wal_codec.py` 78 into 94 and packed at 97"
  - claim: "The two marks a result carries stand clear until a handler passes one"
    source: "`nexus/infrastructure/praxis_connector/process_result.py` 30-31, a handler passing them instead at `nexus/infrastructure/praxis_connector/outcome_processor.py` 322-323 or 354-355"
  - claim: "The mark for the holding is set wherever the holding is found at all, even where the figure behind it already stood at nothing, so a holding already gone is what the exit road needs"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 605 into 610 before 612, against the return at 607-608, that return taken at 310 or 342 and placed on the result at 322 or 354"
---
# What writes the name a success records

[The name an outcome's success records](what-an-entry-outcome-changes.md) goes onto the state object a write serializes, so it is saved the way [the valuation figures are](which-of-a-hosts-changes-reach-the-log.md): put out with the rest of the state by whatever write comes next, to the log or to the snapshot beside it.

## Why no write is asked for on its account

[The write a host asks for after an outcome](which-of-a-hosts-changes-reach-the-log.md) turns on three marks, and recording the name sets none of them. Where all three stand clear, the name waits.

The two a result carries stand clear until a handler passes one.

## Which successes leave them clear

[Two roads](what-an-entry-outcome-changes.md) do: an acknowledgement of an order that is not an entry, and an exit refused or [cancelled](how-a-trade-is-cancelled.md) where the giving-back failed as well.

The second of those needs the holding to be gone, and that is its binding half. The mark for the holding is set wherever the holding is found at all, even where the figure behind it already stood at nothing, so only a holding that has gone leaves it clear.

## What the waiting comes to

The name sits on the state, so it goes down with the next write of that state, whichever cause asked for the write.

[The turning away of a repeat](what-stops-an-outcome-crossing-twice.md) reads that set as it stands in memory, so the wait costs nothing while the host runs. A start reads back only what was written, so a host that stopped with no write of any kind behind it comes back without the name.

## Related

- [Which of a host's changes reach the log](which-of-a-hosts-changes-reach-the-log.md)
- [What an entry outcome changes](what-an-entry-outcome-changes.md)
- [What stops an outcome crossing twice](what-stops-an-outcome-crossing-twice.md)
