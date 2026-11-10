---
row: N16-05
baseline: 49aa659
created: 2026-11-08 10:26 UTC
modified: 2026-11-08 10:26 UTC
evidence:
  - claim: "Three of a mismatch's names are walked and each refused unless it is text with something left in it once trimmed"
    source: "`nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` 46-47 over the three names, into 48-50"
  - claim: "Its moment must be a moment and must carry the UTC marker, both weighed by one test"
    source: "`nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` 52-57"
  - claim: "Its two figures are walked and each refused unless it is a finite decimal"
    source: "`nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` 59-61 into 62-63"
  - claim: "A mismatch whose two figures agree is refused"
    source: "`nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` 65-67"
  - claim: "That is the one check putting two of its fields side by side, the others each weighing one"
    source: "`nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` 46-67, which compares two of its fields at 65 and nowhere else"
  - claim: "The difference it reports is the venue's figure less the one projected, worked out on each reading"
    source: "`nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` 41"
---
# What a mismatch refuses

The record of a disagreement between what the venue reports and what was projected is refused for failing any one of four checks, and the last of them is what makes it a mismatch.

## The three names

The account, the record's own reference, and the asset, each text with something left once the blank space is trimmed off.

## The moment and the two figures

The moment must be a moment carrying the universal-time marker itself, both asked by one test. The two figures — what was expected and what the venue reports — are walked and each refused unless it is a finite decimal.

## The two that must differ

A record whose two figures agree is refused. So this record cannot be made to say nothing is wrong: a disagreement is what it is for, and a line turns back one that does not disagree.

That is the one check putting two of its fields side by side. Every other weighs one field alone.

## The difference

What the record reports as the gap is the venue's figure less the one projected, worked out on each reading rather than kept. Since the two must differ, that gap can never be nought.

## Related

- [What a funds movement refuses](what-a-funds-movement-refuses.md)
- [The holds a report places](the-holds-a-report-places.md)
