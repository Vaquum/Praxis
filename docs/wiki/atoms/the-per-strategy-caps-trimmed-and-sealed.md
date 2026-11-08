---
row: N73-02
baseline: 49aa659
created: 2026-11-13 04:30 UTC
modified: 2026-11-13 04:30 UTC
evidence:
  - claim: "The per-strategy caps must arrive as a mapping, anything else refused before an entry is read"
    source: "`nexus/core/validator/price_stage.py` 123-128"
  - claim: "Each key must be text, and must have something left once trimmed, the two refused with one wording"
    source: "`nexus/core/validator/price_stage.py` 132-137, then 139-145"
  - claim: "A trimmed key already gathered is refused, with one wording however the collision arose"
    source: "`nexus/core/validator/price_stage.py` 146-151"
  - claim: "A key repeated exactly cannot reach that test, a mapping holding one entry per key"
    source: "`nexus/core/validator/price_stage.py` 131, walking the mapping as given"
  - claim: "Each value must be a finite figure of the exact kind at or above nought, weighed after its key has been gathered as acceptable"
    source: "`nexus/core/validator/price_stage.py` 152-161, standing after 146"
  - claim: "What is gathered is keyed by the trimmed name, whatever the key written in the mapping handed in"
    source: "`nexus/core/validator/price_stage.py` 163"
  - claim: "The gathering is then written over the field behind a view that can only be read, by the means that goes round the sealing"
    source: "`nexus/core/validator/price_stage.py` 165-169"
---
# The per-strategy caps, trimmed and sealed

[The record of price limits](what-the-price-records-refuse.md) can carry a cap per strategy, and that mapping is rebuilt as the record is made.

## What it must be

A mapping. Anything else is refused before an entry is read.

## What each key must be

Text, with something left once trimmed. Both are refused with one wording, so a key that is a number and a key that is only spaces give the same complaint.

## The collision that is refused

A trimmed key already gathered is refused, with one wording however the collision arose.

Two names differing only by padding are what that test can catch. A key repeated exactly cannot reach it at all — a mapping holds one entry per key, so the repetition is gone before the walking begins.

## When a value is weighed

After its key has been gathered as acceptable. A cap must be a finite figure of the exact kind at or above nought.

So an entry wrong in both its key and its value is refused for the key.

## What the record ends up holding

A mapping keyed by the trimmed name, written over the field behind a view that can only be read.

So the key a cap ends up under is the trimmed name, whatever was written in the mapping handed in. Nothing holding the record can write into the mapping afterwards.

## Related

- [What the price records refuse](what-the-price-records-refuse.md)
- [How the strategies are built](how-the-strategies-are-built.md)
