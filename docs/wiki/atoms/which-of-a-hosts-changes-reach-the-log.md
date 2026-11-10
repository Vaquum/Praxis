---
row: N8-03
baseline: 49aa659
created: 2026-10-28 18:45 UTC
modified: 2026-10-29 09:37 UTC
evidence:
  - claim: "A change writes the whole state, not the part that changed, so a replay takes the last such record as what it starts from"
    source: "`nexus/infrastructure/state_store.py` 199 into 200-206, the replay starting from it at 265-267"
  - claim: "Two causes ask for that write: an operator's halt or resume, always; and an outcome worked through, only where it succeeded and one of three marks is set, two of them carried on the result and the third where its command stands among the keys of a mapping added to only where one of those two was carried"
    source: "`praxis/launcher.py` 3548-3549, and 4439 under the test at 4404-4408, the third mark read at 4401 from the mapping added to at 2941-2942 under the test at 2938, its only insertion"
  - claim: "A failure to write after an operator's halt or resume answers the operator with a failure instead"
    source: "`praxis/launcher.py` 3552"
  - claim: "The valuation loop writes unrealised figures onto each position, onto each strategy and onto the account, and asks for no write of its own"
    source: "`nexus/core/mtm_loop.py` 293-309, no store call anywhere in the module"
  - claim: "Those figures are carried by whatever write another cause asks for, each write putting all three out"
    source: "`nexus/infrastructure/wal_codec.py` 345, 228 and 273"
  - claim: "The halt raises a hold and the resume lowers it, on the mode of the one account the runtime carries, and either is done before the write is attempted"
    source: "`nexus/core/mode_controller.py` 436 and 448, reached from `praxis/launcher.py` 3537 or 3543, either before 3548-3549, the account read at 3531"
  - claim: "A checkpoint writes out that same state object to the snapshot beside the log"
    source: "`nexus/infrastructure/state_store.py` 178-179 into `nexus/infrastructure/snapshot.py` 45-51"
  - claim: "The rewrite behind it keeps strategy events alone, so every record of a state change is dropped from the log"
    source: "`nexus/infrastructure/wal.py` 289-292 before 295-303"
---
# Which of a host's changes reach the log

A record of a state change holds the whole state, whatever part of it moved, so a replay takes the last such record as the state it starts from.

## The two causes that ask for a write

An operator's halt or resume asks for one every time, without condition. Both act on one account: the halt raises a hold on the mode that account runs under, and the resume lowers it.

An outcome from the venue asks for one only where working it through succeeded and one of three marks is set. Two of those marks are carried on the result itself. The third stands where the outcome's command is among the keys of a mapping that is added to only where one of those first two was carried, so it tracks them rather than anything of its own.

## What a failure to write costs

The hold has already been raised or lowered by the time the write is attempted. A write that fails answers the operator with a failure.

## The figures that reach the log by waiting

The loop that values the positions writes unrealised figures in three places — onto each position, onto each strategy, and onto the account — and asks for no write of its own at all.

Those figures reach the log only when one of the two causes above writes the state out, and because every such write puts the whole state out, each of them carries all three.

[A checkpoint](what-a-checkpoint-holds.md) is no third cause here. It writes the same state object to the snapshot beside the log, so the figures are carried there instead, and the rewrite behind it drops every record of a state change.

## Related

- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [What a checkpoint holds](what-a-checkpoint-holds.md)

---

Created 2026-10-28 18:45 UTC · Last modified 2026-10-29 09:37 UTC
