---
row: N3-11
baseline: 49aa659
created: 2026-10-22 23:00 UTC
modified: 2026-10-23 09:00 UTC
evidence:
  - claim: "A position written back into the record counts its size at the price the host gives"
    source: "`nexus/startup/sequencer.py` 438"
  - claim: "One the record already held counts its size at the record's own cost basis"
    source: "`nexus/startup/sequencer.py` 450 into 468"
  - claim: "Where that basis is nought it is weighed at the host's price instead"
    source: "`nexus/startup/sequencer.py` 451-452"
  - claim: "Where the host's price is nought too it is weighed at the price the record entered it at"
    source: "`nexus/startup/sequencer.py` 452"
  - claim: "Whichever price is used in place of the basis is written onto the position as its cost basis"
    source: "`nexus/startup/sequencer.py` 466-467"
  - claim: "What that reaches is the money a sale releases and the next start's own sum, the gain on a sale being taken from the price entered at instead"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438 and `nexus/core/capital_controller/capital_controller.py` 214-272 against `nexus/infrastructure/praxis_connector/outcome_processor.py` 523-525"
  - claim: "A kept position whose size the host disagrees with is set to the host's size before it is weighed"
    source: "`nexus/startup/sequencer.py` 441-448"
  - claim: "The account's deployed figure is set to the total those prices come to, where it differs from what was kept"
    source: "`nexus/startup/sequencer.py` 470-478"
  - claim: "A position the record already held whose size or price will not read adds nothing to the total and stays in the record; one the import refuses never enters it"
    source: "`nexus/startup/sequencer.py` 416-418 against 424-437"
---
# What a start weighs a position at

A start adds up what every position is worth to set the account's deployed figure, and the price it weighs each one at depends on where the position came from.

## Written back

[A position the record was missing](what-a-start-does-with-a-dusted-position.md) counts its size at the price the host gives for it.

## Already held

One the record already held counts its size at the record's own cost basis. Where the host disagrees with the size, the host's size is taken first, and the record's is overwritten.

Where that cost basis is nought, the host's price stands in. Where the host's price is nought as well, the price the record entered the position at stands in instead. Whichever price is used is written onto the position as its cost basis. That is what the money a sale releases is worked out from, and what the next start's own sum reads. The gain on a sale is taken from the price the position was entered at, which this leaves alone.

## What the total becomes

The account's deployed figure is set to what those prices add up to, where that differs from what was kept. Where the host gives a size or price the start cannot read, a position the record already held is left out of the sum and stays in the record regardless. One the import refuses never enters the record at all.

## Related

- [What a start does with a dusted position](what-a-start-does-with-a-dusted-position.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)

---

Created 2026-10-22 23:00 UTC · Last modified 2026-10-23 09:00 UTC
