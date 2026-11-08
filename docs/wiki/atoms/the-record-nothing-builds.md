---
row: P7-03
baseline: 49aa659
created: 2026-11-09 07:30 UTC
modified: 2026-11-09 07:30 UTC
evidence:
  - claim: "The refusals a fill's own record makes are reached from the tests and from nowhere in Praxis"
    source: "`praxis/core/domain/fill.py` 65-82, reached from `tests/test_domain_core.py` 35 by way of 196, and from no statement in Praxis"
  - claim: "The refusals it makes are the shared check over seven of its fields, the test on its moment, and the three on its figures"
    source: "`praxis/core/domain/fill.py` 65-82"
  - claim: "A test builds one, so every refusal the record makes runs only there"
    source: "`tests/test_domain_core.py` 35, reached from 196"
  - claim: "What the running system builds for a fill instead is the event record"
    source: "`praxis/core/execution_manager.py` 4312"
  - claim: "That event record weighs its three figures by the same comparisons"
    source: "`praxis/core/domain/events.py` 585, or 589, or 593"
---
# The record nothing builds

A fill's own record is built nowhere in Praxis outside the tests.

## What that means for its checks

Every refusal the record makes — the shared check over seven of its fields, the test on its moment, and the three on its figures — runs only when a test builds one.

So [what it requires](what-a-fills-own-record-requires.md) and [what it never asks](what-a-fills-own-record-never-asks.md) are facts about a record that only the tests build.

## What is built instead

The running system reports a fill as [an event record](what-a-fill-is.md), built in the manager and checked by rules of its own — which weigh its three figures by the same comparisons, so those three are made on a record that is built.

## Related

- [What a fill's own record requires](what-a-fills-own-record-requires.md)
- [What a fill's own record never asks](what-a-fills-own-record-never-asks.md)
- [Fills](what-a-fill-is.md)
