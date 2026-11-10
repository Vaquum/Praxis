---
row: N45-02
baseline: 49aa659
created: 2026-11-08 17:14 UTC
modified: 2026-11-08 17:14 UTC
evidence:
  - claim: "The account's three rolling losses are summed over its strategies each time they are read"
    source: "`nexus/core/domain/risk_state.py` 215, or 221, or 227"
  - claim: "Its realized total is summed the same way"
    source: "`nexus/core/domain/risk_state.py` 233"
  - claim: "Each sum reads one field of each strategy's record, so a change to one field moves one sum"
    source: "`nexus/core/domain/risk_state.py` 215, or 221, or 227, or 233"
  - claim: "A strategy's high mark and its unrealized figure are read by none of the four"
    source: "`nexus/core/domain/risk_state.py` 215, 221, 227 and 233, which name four fields of the six declared at 38-44"
  - claim: "An account with no strategies recorded reads nought for each of the four"
    source: "`nexus/core/domain/risk_state.py` 215, or 221, or 227, or 233, each starting from nought"
  - claim: "A recovery hands the realized total back as the record's cumulative figure"
    source: "`nexus/infrastructure/state_store.py` 333"
---
# The figures the account does not store

Four of the figures read off the account's risk record are not kept on it. Each is summed over the strategies at the moment it is read.

## The four

The losses over the last day, week and month, and what the account has realized in all.

Each reads one field of each strategy's record, so a change to one of those fields moves one of the four. A strategy's high mark and its unrealized figure are read by none of them.

An account with no strategies recorded reads nought for each.

## What the sums depend on

Both what the records hold and which records are in the mapping. A strategy added or dropped moves a total with no record having changed.

So a figure read twice can differ for either reason, and nothing in the record distinguishes them.

## Where one of them is written back

[A recovery](what-a-recovery-writes-at-the-end.md) hands the realized total back to the record as its cumulative figure — a figure the record does store, set from one it does not.

## Related

- [What the risk records refuse](what-the-risk-records-refuse.md)
- [How far down the account is](how-far-down-the-account-is.md)
- [What a recovery writes at the end](what-a-recovery-writes-at-the-end.md)
