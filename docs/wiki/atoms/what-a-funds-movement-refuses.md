---
row: N16-04
baseline: 49aa659
created: 2026-11-08 10:26 UTC
modified: 2026-11-08 10:26 UTC
evidence:
  - claim: "Two of a funds movement's names are walked and each refused unless it is text with something left in it once trimmed"
    source: "`nexus/infrastructure/praxis_connector/fund_transaction.py` 41-42 over the two names, into 43-45"
  - claim: "Its moment must be a moment and must carry the UTC marker, both weighed by one test rather than two"
    source: "`nexus/infrastructure/praxis_connector/fund_transaction.py` 47-52"
  - claim: "Its amount must be a decimal, finite, and above nought, all three weighed by one test"
    source: "`nexus/infrastructure/praxis_connector/fund_transaction.py` 54-60"
  - claim: "Its direction must be one of a pair held as text and checked against a fixed set"
    source: "`nexus/infrastructure/praxis_connector/fund_transaction.py` 62-65, the pair at 17"
---
# What a funds movement refuses

The record of money moving into or out of an account is refused for failing any one of four checks.

## The two names

The account and the record's own reference, each text with something left once the blank space is trimmed off. One loop holds both to that.

## The moment

A moment, and one carrying the universal-time marker itself. One test asks both, so a moment of the wrong kind and a moment of the right kind in the wrong zone are turned back by the same line.

## The amount

A decimal, finite, and above nought. One test asks all three, so a whole number, an infinity and nought are turned back by the same line.

## The direction

One of a pair, held as text and checked against a fixed set: money in or money out. The records beside this one hold a kind as named values; this one holds it as words and compares.

So a direction differing only in case is refused, where a named value would not have let it be written at all.

## Related

- [What a mismatch refuses](what-a-mismatch-refuses.md)
- [What an account is](what-an-account-is.md)
