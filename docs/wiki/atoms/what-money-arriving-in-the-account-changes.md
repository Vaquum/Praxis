---
row: N3-02
baseline: 49aa659
created: 2026-10-22 15:10 UTC
modified: 2026-10-23 09:00 UTC
evidence:
  - claim: "A deposit or withdrawal the venue reports is written to the log, and the body touches no figure besides the mark that it was seen"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 737-757"
  - claim: "A repeat of the same identifier is dropped and answers no"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 737-743"
  - claim: "The account's own pool is read for how large a share of it an order is, for how much of it is in use, and for the figure a budget starts from"
    source: "`nexus/core/capital_controller/capital_controller.py` 367, 396 and 459"
  - claim: "The figure a strategy is told it has to spend is sliced from the settings' pool instead, in three places; two take its committed money off the slice and the third hands the slice over whole"
    source: "`praxis/launcher.py` 2516-2518 and `nexus/startup/shutdown_sequencer.py` 313-315 against `nexus/startup/sequencer.py` 720-724"
  - claim: "It is read once more for what is left uncommitted, everything committed being taken off it"
    source: "`nexus/core/domain/capital_state.py` 109-115"
  - claim: "A start that finds no record makes a fresh one from the figure the settings carry"
    source: "`nexus/startup/sequencer.py` 239-246 into `nexus/core/domain/instance_state.py` 157"
  - claim: "The settings refuse a figure that is not a positive number"
    source: "`nexus/infrastructure/manifest.py` 421-434"
  - claim: "A start that finds a record takes the pool back out of it instead, the settings' figure going unread"
    source: "`nexus/startup/sequencer.py` 239-240 into `nexus/infrastructure/wal_codec.py` 198"
  - claim: "Those two, and the line writing it into the snapshot, are everywhere the figure is set"
    source: "`nexus/core/domain/instance_state.py` 157, `nexus/infrastructure/wal_codec.py` 198 and 173"
---
# What money arriving in the account changes

Money arriving in the account is written down and changes nothing else. A deposit the venue reports buys no more than the account could already buy.

## What is written

The report is logged with the account it names, its own identifier, which way the money went, and how much. Beside the log, the only thing the body touches is the mark that this identifier has been seen — so a second delivery of the same report is dropped and answers no.

## Why nothing moves

Two pools are kept, and a fresh account takes both from the settings. The account's own, in its record, is read in four places: how large a share of it one order is, how much of it is in use, the figure a budget starts from, and what is left uncommitted once everything committed is taken off it. The settings' pool is read in three more. Two slice it and take the strategy's committed money off; the third hands the slice over whole.

It is set in two: a start that finds no record makes a fresh one from the figure the settings carry, which they refuse unless it is a positive number; and a start that finds a record takes the figure back out of it, leaving the settings' one unread. Those two and the line writing it into the snapshot are everywhere it is set.

So raising the account's pool is a matter of starting an account that has no record yet. For one already running, the figure the budgets start from is the one it was born with, and a deposit cannot move it. Changing the settings and starting again moves what a strategy is told, and leaves what the checks weigh as it was.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What each check weighs](what-each-check-weighs.md)

---

Created 2026-10-22 15:10 UTC · Last modified 2026-10-23 09:00 UTC
