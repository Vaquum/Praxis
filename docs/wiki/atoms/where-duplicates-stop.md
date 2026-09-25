---
row: P2-32
baseline: 49aa659
created: 2026-09-25 19:41 UTC
modified: 2026-09-25 19:50 UTC
evidence:
  - claim: "A fill is offered to the record before anything else is told"
    source: "`execution_manager.py` 4328-4330"
  - claim: "The same execution can be made into a fill from a send's reply, from the venue's live reports, and from a later reconciling of its trade list"
    source: "`execution_manager.py` 4312, `praxis/trading.py` 1787 and 1045-1052"
  - claim: "The record holds the epoch, the account, the symbol and the venue's name for the execution together"
    source: "`event_spine.py` 147-152, written at 1019-1020"
  - claim: "The epoch is given to the host from outside and survives a restart"
    source: "`launcher.py` 4867, carried at 4962-4963"
  - claim: "A fill matching all four is refused there"
    source: "`event_spine.py` 1021-1022"
  - claim: "Nothing comes back for a fill refused that way"
    source: "`execution_manager.py` 4329-4330"
---
# Where duplicates stop

A [fill](what-a-fill-is.md) is offered to the record before anything acts on it, and only what the record accepts is passed on.

That makes the record the one place a repeat is caught, and repeats are ordinary. The same execution reaches Praxis by three routes: the reply to the send that caused it, the venue's live reports, and a later walk through the venue's own list of trades. It must count once however many of them arrive.

## What counts as the same

Four things are held together for every execution taken: the epoch, the [account](what-an-account-is.md), the symbol, and the venue's own name for that execution.

The epoch is a number the host is given when it starts, so restarting under the same one keeps every refusal already earned. A fill matching all four is refused. The same venue name under a different account, a different symbol, or a different epoch is taken as new.

## What a refusal leaves

Nothing comes back for a fill refused this way, and the projections are never told about it. [What it would have changed](what-a-fill-changes.md) is left exactly as it was.

The refusal is not a failure. It is the ordinary outcome for a report Praxis has already counted, and the send that carried it goes on.

## Related

- [What a fill is](what-a-fill-is.md)
- [What a fill changes](what-a-fill-changes.md)
