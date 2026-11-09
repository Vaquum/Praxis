---
row: P126-02
baseline: 49aa659
created: 2026-11-15 07:30 UTC
modified: 2026-11-15 07:30 UTC
evidence:
  - claim: "An account's accounting wiring is written into one mapping from inside its build"
    source: "`launcher.py` 4355"
  - claim: "Its runtime is written into another only once that build has answered"
    source: "`launcher.py` 3993 into 3994, past 3992"
  - claim: "The runtime is taken out again on the ordinary way out, and on the failing one"
    source: "`launcher.py` 4001 into 4002, or 4037-4038"
  - claim: "An arriving report reads the wiring by the account it names, and does nothing where none stands"
    source: "`launcher.py` 2986"
  - claim: "Reaching an account reads the runtime instead, and refuses where none stands"
    source: "`launcher.py` 3969, then 3972 into 3973-3977"
  - claim: "Each mapping is built empty with a lock of its own"
    source: "`launcher.py` 2812, then 2813, then 2814, then 2815"
---
# The two mappings an account lives in

An account is written into two mappings at two different moments, and each answers a different question about it.

## The wiring

Written from inside the account's build, before the build has answered. It carries what an arriving report needs to be accounted for, and an arriving report reads it by the account it names.

Nothing in the host takes an account out of it, so an account's wiring stands for as long as the host does. A report arriving while the account is still building is therefore accounted for.

## The runtime

Written only once the build has answered, and taken out again on both ways out — the ordinary one and the failing one.

Reaching an account reads the runtime rather than the wiring, and refuses where none stands. So the half-built account a report can still be accounted for in cannot be reached by an operator or by reconciliation.

## Why they are not one mapping

They are published on different edges and withdrawn on different edges. The wiring says an account's figures can still be moved; the runtime says an account can still be asked something.

One mapping would have to pick an edge, and whichever it picked, the other question would be answered wrongly for the span between them.

## Related

- [When an account can be delivered to](when-an-account-can-be-delivered-to.md)
- [The road an arriving report takes](the-road-an-arriving-report-takes.md)
