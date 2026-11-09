---
row: N6-04
baseline: 49aa659
created: 2026-10-26 16:26 UTC
modified: 2026-11-09 04:19 UTC
evidence:
  - claim: "The wait is over the identifiers the sending recorded, which is every abort that went and every sale whose record against the position was built"
    source: "`nexus/startup/shutdown_sequencer.py` 614-615 over 592 and 461, against 443"
  - claim: "It reads outcomes off a queue, each read waiting a short while of its own for one to arrive"
    source: "`nexus/startup/shutdown_sequencer.py` 650 into `nexus/infrastructure/praxis_connector/praxis_inbound.py` 42-45"
  - claim: "A fill or an ending is worked through against the host's figures, which move only where that identifier belongs to a sale whose record was kept and a processor is wired"
    source: "`nexus/startup/shutdown_sequencer.py` 659-660 into 767-768, past 749-750 and 752-754 and 756-765, the record written at 460"
  - claim: "An ending strikes its identifier off whether the figures moved or not, so an abort's ending clears the wait and moves nothing"
    source: "`nexus/startup/shutdown_sequencer.py` 662-663 against 752-754, an abort recorded at 592 with no record written for it"
  - claim: "The reading goes on until nothing is left outstanding or a deadline passes"
    source: "`nexus/startup/shutdown_sequencer.py` 647-649"
  - claim: "The deadline is a span the stopping sequence is built with, and the launcher that builds it names none, leaving the sequence's own standing figure"
    source: "`nexus/startup/shutdown_sequencer.py` 164 into 616 and 647, the building at `praxis/launcher.py` 4009-4029"
  - claim: "Recording nothing while sending means waiting for nothing, and an absent connection in is logged and waited on for nothing"
    source: "`nexus/startup/shutdown_sequencer.py` 604-605 and 607-612"
  - claim: "Each identifier still outstanding at the deadline has an abort attempted for it, under a reason naming the running out, a send that raises being logged and the rest still tried"
    source: "`nexus/startup/shutdown_sequencer.py` 622 into 793-805, the reason at 52"
  - claim: "The reading then runs again over what is left, for half as long"
    source: "`nexus/startup/shutdown_sequencer.py` 624-627, the half at 53"
  - claim: "What survives that is logged by name and left, and the host goes on to save, checkpoint and unregister with no ending seen for those commands"
    source: "`nexus/startup/shutdown_sequencer.py` 629-634 before 190-196"
---
# What a stopping host waits for

A stopping host waits on the identifiers its sending recorded: every abort that went, and every sale whose record against the position was built.

A sale whose record came apart is [left out of that list](the-abort-a-host-sends-as-it-stops.md) though the command went.

## The reading

It reads [outcomes](what-an-outcome-is.md) off a queue — [the queue it asked the other reader to leave](what-a-stopping-host-halts-first.md) — each read waiting a short while of its own for one to arrive.

A [fill](what-a-fill-is.md) or an ending is passed to the host's figures, which move only where that identifier belongs to a sale whose record was kept. An ending strikes its identifier off either way, so an abort's ending clears the wait and moves nothing.

The reading goes on until the list is empty or a deadline passes, set from a span the stopping sequence is built with — which the launcher that builds it leaves unnamed, so the sequence's own standing figure holds. Where nothing was recorded, or the connection in is absent, there is nothing to read and the host moves on.

## When the deadline passes

Each identifier still outstanding has an abort attempted for it, under a reason naming the running out rather than the stopping; a send that raises is logged and the rest are still tried. Then the reading runs again over what is left, for half as long.

## When that runs out too

What survives is logged by name and left. The host goes on to save what its strategies hold, write its last record and unregister — so stopping can finish with commands it never saw end.

## Related

- [Where an outcome outside the wait is sent](where-an-outcome-outside-the-wait-is-sent.md)
- [The abort a host sends as it stops](the-abort-a-host-sends-as-it-stops.md)

---

Created 2026-10-26 16:26 UTC · Last modified 2026-11-09 04:19 UTC
