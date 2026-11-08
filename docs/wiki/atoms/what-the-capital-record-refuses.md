---
row: N37-01
baseline: 49aa659
created: 2026-11-11 19:00 UTC
modified: 2026-11-12 00:00 UTC
evidence:
  - claim: "The pool must be finite and above nought"
    source: "`nexus/core/domain/capital_state.py` 44-46"
  - claim: "Five further figures must each be finite and at or above nought"
    source: "`nexus/core/domain/capital_state.py` 48-58"
  - claim: "The per-strategy mapping must be a mapping"
    source: "`nexus/core/domain/capital_state.py` 60-62"
  - claim: "Each key must be text with something left once trimmed"
    source: "`nexus/core/domain/capital_state.py` 66-70, or 72-77"
  - claim: "Each value must be a figure of the exact kind, finite, and at or above nought"
    source: "`nexus/core/domain/capital_state.py` 84-89, or 90-95"
  - claim: "A fresh state asks the same of the pool before handing it over, in two tests where the record makes one"
    source: "`nexus/core/domain/instance_state.py` 148-150, or 152-154, ahead of 156-157"
  - claim: "The mapping is rebuilt as the record is built and put back over the field it arrived in"
    source: "`nexus/core/domain/capital_state.py` 64 and 97 into 99"
---
# What the capital record refuses

The record of what an account's money is doing checks every figure it holds as it is built, and checks the mapping of what each strategy has out twice over.

## The figures

The pool must be finite and above nought.

Five more figures are held to being finite and at or above nought: what the positions come to, what is resting at the venue, what is on its way there, what is held back for fees, and what is set aside for requests. Each may be nought.

## The mapping

It must be a mapping. Each key must be text with something left once the blank space is trimmed off, and [a padded key is refused outright](the-key-this-record-will-not-trim-for-you.md) rather than trimmed for the caller.

Each value must be a figure of the exact kind, finite, and at or above nought — so a value given as an ordinary number is refused even where its size would pass.

## The pool, asked for twice

A state built fresh asks the same of the pool before it hands it over: finite and of the exact kind in one test, above nought in a second. The record then asks both again in one.

So a pool of nought is refused twice over, by two records, with two different complaints — the fifth pair of rules the register has found standing in two places.

## What the record holds afterwards

The mapping is rebuilt as the record is built, and put back over the field it arrived in. So what the record holds is its own, and the keys it holds are the ones that passed.

## Related

- [The key this record will not trim for you](the-key-this-record-will-not-trim-for-you.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What moves a strategy's committed figure](what-moves-a-strategys-committed-figure.md)
