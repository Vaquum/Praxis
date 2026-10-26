---
row: N5-05
baseline: 49aa659
created: 2026-10-25 11:40 UTC
modified: 2026-10-25 11:50 UTC
evidence:
  - claim: "The three are worked out before the position is built, and nothing is built where the working out answers with nothing"
    source: "`nexus/startup/sequencer.py` 317-346 into 276-280, feeding the building at 282-291"
  - claim: "All three are taken off what the host gave for the position"
    source: "`nexus/startup/sequencer.py` 317, 326 and 334-335"
  - claim: "A position the working out refuses is passed over, staying out of the record and out of the sum the account's figure is set from"
    source: "`nexus/startup/sequencer.py` 422-437 against 438, into 470-478"
  - claim: "A strategy that is missing or blank answers with nothing, logged with the trade and the size the host gave"
    source: "`nexus/startup/sequencer.py` 318-324"
  - claim: "A symbol that is missing or blank answers the same way, logged with the trade alone"
    source: "`nexus/startup/sequencer.py` 327-332"
  - claim: "A side the record has no match for answers the same way, logged with the side it was given, the host's own side being read through the value it carries"
    source: "`nexus/startup/sequencer.py` 335-344"
  - claim: "Each of the three answers with nothing where it fails, so the answer carrying all three is reached only past all of them"
    source: "`nexus/startup/sequencer.py` 324, or 332, or 344, against 346"
---
# Where an imported position's names come from

An imported position's strategy, symbol and side are the three things [a start must know](what-a-written-back-position-carries.md) before it can write that position back, and all three come off what the host gave for it.

## Read in turn

The strategy is read first, then the symbol, then the side. The side is read through the value the host's own side carries, and matched against the sides the record keeps.

Each is read for being there and being usable: a strategy or symbol that is missing or blank, and a side the record has no match for, each answer with nothing where they stand. The answer carrying all three is reached only past all of them.

## What a refusal costs

A working out that answers with nothing is the end of that position: nothing is built, and the start passes it over — out of the record, and out of [the sum the account's figure is set from](what-a-start-weighs-a-position-at.md). Each failure is logged, though with different details: the trade and the size for a missing strategy, the trade alone for a missing symbol, the side itself for one that will not match.

So a position the host holds under no strategy it can name is left out of Nexus's record entirely — not written back under a stand-in, and not carried as an unnamed holding.

## Related

- [What a written-back position carries](what-a-written-back-position-carries.md)
- [What a start weighs a position at](what-a-start-weighs-a-position-at.md)

---

Created 2026-10-25 11:40 UTC · Last modified 2026-10-25 11:50 UTC
