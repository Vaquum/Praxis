---
row: P7-02
baseline: 49aa659
created: 2026-11-08 09:11 UTC
modified: 2026-11-08 09:11 UTC
evidence:
  - claim: "A fill's amount and price are refused where they stand at or below nought, and its fee where it stands below nought"
    source: "`praxis/core/domain/fill.py` 74-76, or 77-79, against 80-82"
  - claim: "No check of the record's own asks any of those three to be a finite figure, or to be a decimal"
    source: "`praxis/core/domain/fill.py` 65-82, which tests none of the three for either"
  - claim: "Neither its side nor the flag saying whether the order waited or took what was there is weighed in any way"
    source: "`praxis/core/domain/fill.py` 65-82, which names neither"
---
# What a fill's own record never asks

Three figures on a fill's own record are weighed against nought, and five of its fields are weighed for nothing else at all.

## The three figures

The amount and the price are refused where they stand at or below nought. The fee is refused where it stands below nought.

Each of the three is compared and nothing more. No check of the record's own asks any of them to be a finite figure, or to be a decimal.

## The two fields nothing reads

Its side, and the flag saying whether the order waited for someone to trade with it or took an offer already there. Neither is weighed in any way as the record is made.

So a record may say it sold while carrying a side that is not one of the named ones, and [what it does require](what-a-fills-own-record-requires.md) will not catch it.

## Related

- [What a fill's own record requires](what-a-fills-own-record-requires.md)
- [The record nothing builds](the-record-nothing-builds.md)
