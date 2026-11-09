---
row: P179-02
baseline: 49aa659
created: 2026-11-16 10:00 UTC
modified: 2026-11-16 10:00 UTC
evidence:
  - claim: "The version is lifted to the first where it stands below it"
    source: "`execution_manager.py` 6911"
  - claim: "The account's other work is frozen before anything is recorded"
    source: "`execution_manager.py` 6913-6917, then 6918"
  - claim: "The failure is recorded, and only then is the bracket's standing moved to failed"
    source: "`execution_manager.py` 6918-6920, then 6921"
  - claim: "The remediation is remembered against the account"
    source: "`execution_manager.py` 6922-6924"
  - claim: "The close is attempted only where the account's settings answer flatten-then-halt"
    source: "`execution_manager.py` 6933-6936, then 6937, then 6938-6941"
  - claim: "The remembered remediations are drained last of all"
    source: "`execution_manager.py` 6943"
---
# What happens before a lost protection's close is attempted

A bracket whose protection is lost has four things done to it before any order goes out to close the position.

## In order

The version is lifted to the first where it stands below it, so a bracket whose protection was never changed still carries a version the record will accept.

The account's other work is frozen. Then the failure is recorded. Then the bracket's standing is moved to failed. Then the remediation is remembered against the account.

## Then, and only sometimes, the close

The close is attempted only where the account's settings answer flatten-then-halt. A setting answering anything else leaves the position open with the failure recorded and the work frozen.

## Last

The remembered remediations are drained.

The freezing comes before the close, so a bracket closed out on this road had the account's other work frozen first. The record comes before the standing, so a restart falling between the two finds the failure written, the standing being memory and the record not.

## Related

- [When protection is lost](when-protection-is-lost.md)
- [The holds a report places](the-holds-a-report-places.md)
- [When a flatten places nothing](when-a-flatten-places-nothing.md)
