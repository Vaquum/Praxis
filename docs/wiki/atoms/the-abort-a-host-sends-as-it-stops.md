---
row: N6-03
baseline: 49aa659
created: 2026-10-26 16:20 UTC
modified: 2026-10-26 16:26 UTC
evidence:
  - claim: "An abort goes for each one a strategy asks for as the host stops, against the command identifier that answer already carries"
    source: "`nexus/startup/shutdown_sequencer.py` 386 into 581-587"
  - claim: "It carries the account, the moment, and a reason fixed in the code as the word for stopping"
    source: "`nexus/startup/shutdown_sequencer.py` 584-586, the reason at 51"
  - claim: "An abort with no identifier cannot be built at all, so a strategy trying to ask for one raises and the host keeps nothing from it"
    source: "`nexus/strategy/action.py` 240-243 under the frozen shape at 35, the raise caught at `nexus/startup/shutdown_sequencer.py` 329-330"
  - claim: "The send has a guard of its own against a missing identifier, which an answer that was built cannot reach"
    source: "`nexus/startup/shutdown_sequencer.py` 577-579 against `nexus/strategy/action.py` 241-243"
  - claim: "Where the connection out or the host's settings are absent, nothing at all is sent and the sales go with the aborts"
    source: "`nexus/startup/shutdown_sequencer.py` 368-380 returning before 382-386"
  - claim: "A send that raises is logged and the host goes on to the next thing it kept"
    source: "`nexus/startup/shutdown_sequencer.py` 588-590 under the loop at 382-386"
  - claim: "A sent abort's identifier is recorded, and that record is what the host waits on"
    source: "`nexus/startup/shutdown_sequencer.py` 592, read at 615"
  - claim: "A sale records its identifier later in its own road, after the record against the position has been built"
    source: "`nexus/startup/shutdown_sequencer.py` 425-431 before 461"
  - claim: "A sale whose record came apart there returns first, so its identifier goes unrecorded though the command was handed over at 407"
    source: "`nexus/startup/shutdown_sequencer.py` 432-443, against 407"
  - claim: "The abort is sent straight out, with no request built for it and no walk asked"
    source: "`nexus/startup/shutdown_sequencer.py` 582 against 398-404"
---
# The abort a host sends as it stops

An abort a stopping host sends asks Praxis to drop a command already handed over, naming it by the identifier the strategy's own answer carries.

## What it carries

The identifier, [the account](what-an-account-is.md), the moment, and a reason fixed in the code as the word for stopping. It goes straight out: no request is built for it and [the walk](the-checks-a-decision-passes.md) is never asked, where [the sale beside it](the-sale-a-host-sends-as-it-stops.md) at least builds a request and writes its own answer.

## What stops one going

An abort with no identifier cannot be built at all: asking for one raises where the request is made, and the host logs that and keeps nothing from that strategy. The send holds a guard against a missing identifier anyway, which no answer that was built can reach. Where the connection out or the host's settings are absent, nothing at all is sent, aborts and sales alike. A send that raises is logged and the host goes on to the next thing it kept.

## What the sending records

A sent abort's identifier is recorded, and that record is [what the host waits on](what-a-stopping-host-waits-for.md).

A sale records its identifier later in its own road — after the record against the position has been built. A sale whose record came apart there returns first, so its identifier goes unrecorded while the command itself has already been handed over.

## Related

- [The sale a host sends as it stops](the-sale-a-host-sends-as-it-stops.md)
- [The roads around the checks](the-roads-around-the-checks.md)

---

Created 2026-10-26 16:20 UTC · Last modified 2026-10-26 16:26 UTC
