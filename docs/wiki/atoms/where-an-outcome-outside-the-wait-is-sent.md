---
row: N6-05
baseline: 49aa659
created: 2026-10-26 16:26 UTC
modified: 2026-11-09 04:19 UTC
evidence:
  - claim: "A stopping host puts each outcome it reads on one of two roads, by whether its identifier is on the list the stopping still has outstanding"
    source: "`nexus/startup/shutdown_sequencer.py` 655-657 against 659-663, the list built at 615 and shortened at 663"
  - claim: "The second road ends at a handler the launcher wired"
    source: "`nexus/startup/shutdown_sequencer.py` 701-702, the handler passed at `praxis/launcher.py` 4026"
  - claim: "The list holds every sale whose record was kept and every abort whose send came back, the latter under the identifier of the command that abort names"
    source: "`nexus/startup/shutdown_sequencer.py` 461 and 592 after 588-590, the identifier required of the request at `nexus/strategy/action.py` 240-243"
  - claim: "So a command sent long before the stopping, where the stopping aborted it, is on the first road"
    source: "`nexus/startup/shutdown_sequencer.py` 592 into 615"
  - claim: "One from before the stopping that no abort named is on neither of those two additions, so it takes the second road"
    source: "`nexus/startup/shutdown_sequencer.py` 461 and 592 as the only additions to the list read at 615, against 655-657"
  - claim: "A sale whose record came apart takes the second, as does a command every abort naming it raised on, and a second outcome for an identifier already shortened away"
    source: "`nexus/startup/shutdown_sequencer.py` 432-443 before 461, 588-590 before 592 under the keeping at 346-357, and 663"
  - claim: "Where no handler is wired the outcome is logged and nothing else is done with it, the reading going straight on"
    source: "`nexus/startup/shutdown_sequencer.py` 692-699 returning into 657"
  - claim: "The handler looks the command up and works the outcome through where it finds a record of it"
    source: "`praxis/launcher.py` 4470-4474 into 4499"
  - claim: "Finding none, it logs and, where the outcome is an ending, drops the registration and asks for the order's money back"
    source: "`praxis/launcher.py` 4476-4497"
  - claim: "A handler that raises is logged and the reading goes on"
    source: "`nexus/startup/shutdown_sequencer.py` 703-708"
  - claim: "Outcomes reach the stopping because the loop that would ordinarily take them off the queue is stopped before the stopping starts reading, though a worker outlasting that stop can still take one"
    source: "`nexus/core/outcome_loop.py` 211 reached from 379-382, stopped at `nexus/startup/shutdown_sequencer.py` 186 before 189, the outlasting at `nexus/core/outcome_loop.py` 179-185"
---
# Where an outcome outside the wait is sent

A stopping host puts each [outcome](what-an-outcome-is.md) it reads on one of two roads, by whether its identifier is on the list the stopping still has outstanding. The second road ends at a handler the launcher wired.

## Which outcomes take it

The list holds what the stopping itself sent: every sale whose record was kept, and every abort whose send came back — the latter under the identifier of the command that abort names. So a command sent long before the stopping, where the stopping aborted it, is on the first road after all.

The second road takes [a sale whose record came apart](the-abort-a-host-sends-as-it-stops.md), a command from before the stopping that no abort named, a command every abort naming it raised on, and a second outcome for an identifier already struck off.

These reach the stopping because [the loop that would ordinarily take them off the queue](stopping-the-loop-that-reads-outcomes.md) is stopped before the stopping starts reading — though a worker outlasting that stop can still take one away first.

## Where it ends

At a handler the launcher wired. That handler looks the command up and works the outcome through where it finds a record of it. Finding none, it logs, and where the outcome is an ending it drops the registration and [asks for the order's money back](releasing-an-order-whose-record-was-lost.md).

Where no handler is wired, the outcome is logged and nothing else is done with it. A handler that raises is logged too, and [the reading](what-a-stopping-host-waits-for.md) goes straight on either way.

## Related

- [What a stopping host waits for](what-a-stopping-host-waits-for.md)
- [Stopping the loop that reads outcomes](stopping-the-loop-that-reads-outcomes.md)

---

Created 2026-10-26 16:26 UTC · Last modified 2026-11-09 04:19 UTC
