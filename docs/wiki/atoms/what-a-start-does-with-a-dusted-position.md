---
row: N3-10
baseline: 49aa659
created: 2026-10-22 21:00 UTC
modified: 2026-10-23 09:00 UTC
evidence:
  - claim: "A dust write deletes the position from Nexus's record and leaves both deployed figures as they were"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 576-580 into 594-595, and 696-702"
  - claim: "A start asks the host for the positions it holds"
    source: "`nexus/startup/sequencer.py` 363"
  - claim: "Each one the record is missing is written back from the size and price the host gives, where it can be"
    source: "`nexus/startup/sequencer.py` 412-415 into 420-423 and 437, built at 283-290"
  - claim: "A written-back position adds its size at the host's price to the total the account's deployed figure is then set from"
    source: "`nexus/startup/sequencer.py` 438 into 470-478"
  - claim: "One the import refuses, one whose name is not a string, and one whose size or price will not read are each passed over instead"
    source: "`nexus/startup/sequencer.py` 424-437, 372-377 and 416-418"
  - claim: "One the import itself refuses is left out of that figure, and logged"
    source: "`nexus/startup/sequencer.py` 423-437"
  - claim: "The account's figure is then set to what those positions came to, where that differs from what was kept"
    source: "`nexus/startup/sequencer.py` 468-478"
  - claim: "Each strategy's figure is worked out from the record's positions afterwards, the import having already added to them"
    source: "`praxis/launcher.py` 4085 before 4101, the import reached from `nexus/startup/sequencer.py` 174-177, into `nexus/core/capital_controller/capital_controller.py` 214-272"
  - claim: "The host drops a position from its own book where a fill leaves nothing of it, or where it is told the trade closed"
    source: "`praxis/core/trading_state.py` 517-519, and 571-573 reached from 217-218"
  - claim: "A close the venue refuses at intake produces neither: no order is placed and nothing is reported"
    source: "`praxis/launcher.py` 1323 into 1363-1369"
---
# What a start does with a dusted position

A dusted position is one Nexus has taken out of its record, and a start decides whether the money behind it goes with it.

## The import

A start asks the host for the positions it holds. Each one the record is missing is written back into the record from the size and price the host gives, and its size at the host's price added to a running total. Three are passed over instead, each logged: one the import refuses, one whose name is not a string, and one whose size or price will not read.

[What each position is weighed at](what-a-start-weighs-a-position-at.md) differs between one written back and one the record already held.

## The order of the two passes

Each strategy's figure is worked out from the record's positions after the import, so a position written back is one of them. [The dust write](what-a-dusted-scrap-leaves-behind.md) removed it from the record; the import can put it back.

## What decides it

Whether the host still holds the position. It drops one from its own book where a fill leaves nothing of it, or where it is told the trade closed. A close the venue refuses at intake is neither: no order is placed and nothing is reported, so the host keeps it.

So the dust write takes the position out of Nexus's record and leaves the money standing, and the next start writes the position back and sets the figures from it — at the host's price rather than the cost basis it had.

## Related

- [What a dusted scrap leaves behind](what-a-dusted-scrap-leaves-behind.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)

---

Created 2026-10-22 21:00 UTC · Last modified 2026-10-23 09:00 UTC
