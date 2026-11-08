---
row: N60-01
baseline: 49aa659
created: 2026-11-12 18:00 UTC
modified: 2026-11-12 18:00 UTC
evidence:
  - claim: "The signal's series must be text with something in it that equals itself trimmed"
    source: "`nexus/infrastructure/manifest.py` 53-59"
  - claim: "Its interval must be a whole number, with a true-or-false refused by a test of its own because it counts as one"
    source: "`nexus/infrastructure/manifest.py` 61-63"
  - claim: "Its interval must then stand above nought, and the reading that built it asked only its kind"
    source: "`nexus/infrastructure/manifest.py` 65-67, the reading at 484-486"
  - claim: "Its staleness answer must be the one word, and its label, where given, must be text"
    source: "`nexus/infrastructure/manifest.py` 69-71, and 73-75"
  - claim: "A timer's record asks the same three in the same order and asks nothing else"
    source: "`nexus/infrastructure/manifest.py` 93-99, then 101-103, then 105-107"
  - claim: "A strategy's record asks its signal to be a signal record, its share to be a finite figure of the exact kind, and that share to stand above nought and at or under a hundred"
    source: "`nexus/infrastructure/manifest.py` 148-150, then 152-157, then 159-161"
  - claim: "Its collar, where given, must be a finite figure of the exact kind at or above nought, the three asked as one test behind a test for its absence"
    source: "`nexus/infrastructure/manifest.py` 163-172"
  - claim: "Its timers must be a sealed run, each a timer record, and no two of them under one name"
    source: "`nexus/infrastructure/manifest.py` 174-176, then 180-183, then 185-187"
---
# What the strategy records refuse

[A strategy entry in a manifest](the-order-a-strategy-entry-is-read-in.md) becomes records of three kinds — one for the signal, one for the strategy, and one per timer, of which there may be none — and each refuses what the reading let through.

## The signal

Its series must be text with something in it, and must equal itself trimmed.

Its interval must be a whole number. A true-or-false is refused by a test of its own, which is there because a true-or-false counts as a whole number wherever that is asked plainly.

Its interval must then stand above nought. The reading asked only the kind, so this is the record's own addition.

Its staleness answer must be the single word that is accepted. Its label, where one is given, must be text.

## The timer

The same three, in the same order: a name that is text with something in it and equals itself trimmed, an interval that is a whole number with a true-or-false refused, and an interval above nought. The record asks nothing else.

## The strategy

Its signal must be a signal record. Its share must be a finite figure of the exact kind, and must then stand above nought and at or under a hundred.

Its collar, where one is given, must be a finite figure of the exact kind at or above nought — the three asked as one test, standing behind a test for its absence.

Its timers must arrive as a sealed run, each must be a timer record, and no two of them may stand under one name.

## Related

- [The order a strategy entry is read in](the-order-a-strategy-entry-is-read-in.md)
- [The two refusals the manifest record adds](the-two-refusals-the-manifest-record-adds.md)
