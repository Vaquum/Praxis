---
row: N83-03
baseline: 49aa659
created: 2026-11-13 17:30 UTC
modified: 2026-11-13 17:30 UTC
evidence:
  - claim: "The builder of the request answers with nothing where no trade is named, and reports it"
    source: "`nexus/startup/shutdown_sequencer.py` 536 into 537-538"
  - claim: "It answers with nothing where the trade named is not held, and reports that too"
    source: "`nexus/startup/shutdown_sequencer.py` 540-541 into 542-547"
  - claim: "It answers with nothing where there is no configuration, and reports nothing at all"
    source: "`nexus/startup/shutdown_sequencer.py` 549 into 550"
  - claim: "The builder of the order raises where no trade is named or no size given"
    source: "`nexus/startup/shutdown_sequencer.py` 491 into 492-493"
  - claim: "It raises where the request it was handed names no side"
    source: "`nexus/startup/shutdown_sequencer.py` 495 into 496-497"
  - claim: "The order it builds is made only once every one of those has passed"
    source: "`nexus/startup/shutdown_sequencer.py` 518, standing after 516"
---
# The same absence in the two exit builders

Closing a position as a host stops goes through two builders, and a missing [trade](what-a-trade-is.md) name stops each of them differently.

## The request

Built first. Where no trade is named it answers with nothing, and reports it. A trade named but missing from the positions the host holds answers with nothing again, and reports that too.

Where there is no configuration it answers with nothing and reports nothing at all — the only one of its three roads that leaves no trace.

## The order

Built second, from the request. Where no trade is named or no size given, it raises. Where the request names no side, it raises.

The order itself is made only once every one of those has passed.

## Why the difference matters

The same absence — no trade named — is a quiet nothing in the first builder and a raise in the second. A host stopping with such an action skips that position and carries on; one that somehow reached the second builder stops the stopping itself.

So the first builder is the one that decides which positions are even attempted, and the second trusts what it is handed.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [What the wait for outcomes takes off the pending set](what-the-wait-for-outcomes-takes-off-the-pending-set.md)
