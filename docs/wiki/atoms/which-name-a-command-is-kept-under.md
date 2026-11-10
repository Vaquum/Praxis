---
row: N6-08
baseline: 49aa659
created: 2026-10-26 16:26 UTC
modified: 2026-10-26 16:26 UTC
evidence:
  - claim: "Which road is taken follows the one reading of the receiver, answered to the launcher as a yes or a no"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 134 over what 62-74 left at 105-108, read by the launcher at `praxis/launcher.py` 4253"
  - claim: "Where the receiver is taken as bound to the name sent, a record of the command is written before the send, keyed by that name"
    source: "`praxis/launcher.py` 2083-2087, the writing built only at 4239-4254 and reached from `nexus/strategy/action_submit.py` 313-315 before 337"
  - claim: "On that road the name that comes back is handed to the record it already wrote, which keeps its own key"
    source: "`nexus/strategy/action_submit.py` 420-422 against the key fixed at `praxis/launcher.py` 2087"
  - claim: "Where the receiver is taken as merely able to pass the name, or cannot be read, the writing-before is left unbuilt and the record waits for the send"
    source: "`praxis/launcher.py` 4239-4254 against `nexus/strategy/action_submit.py` 310-315"
  - claim: "A record is written after it instead, keyed by the name that came back"
    source: "`praxis/launcher.py` 4270-4285 over the name carried out at `nexus/strategy/action_submit.py` 446-453"
  - claim: "The receiver the launcher hands over declares that name, so with Praxis's own wiring the first road is the live one"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 62 reading the shape of the receiver handed over at `praxis/launcher.py` 453-454 and built at 4075, which carries the name through at 449, answering bound at `nexus/infrastructure/praxis_connector/praxis_outbound.py` 66-67, which returns before the second road at `praxis/launcher.py` 4270-4271"
  - claim: "An outcome is looked up under the name the outcome itself carries, either way"
    source: "`praxis/launcher.py` 4470-4471"
  - claim: "A sale a stopping host sends keeps the answered name in a list of its own and waits on that, where the record it builds after the send holds together"
    source: "`nexus/startup/shutdown_sequencer.py` 407 into 461, read at 615, against 432-443"
---
# Which name a command is kept under

A command is kept under one of two names — the one Nexus sent or the one Praxis answered with — and which it is follows from [how the receiver was read](the-name-an-order-comes-back-with.md), answered to the launcher as a yes or a no.

## The bound receiver

Where the receiver was taken as bound to the name sent, the record of the command is written before the send, keyed by that name. The name that comes back is handed to that record afterwards, which keeps the key it already has.

## The unbound receiver

Where it was not, the record waits for the send and is written after it, keyed by the name that came back. So the answered name governs wherever Nexus's own was not binding: where the receiver was sent the name without being held to it, and where it was sent no name at all.

With Praxis's own wiring this road is never taken: the receiver the launcher hands over declares the name. [When the money set aside is claimed](when-money-set-aside-moves-onto-an-order.md) differs with the road too.

## Looking one up again

An [outcome](what-an-outcome-is.md) is looked up under the name the outcome itself carries, either way. So the road taken has to leave the record under the name Praxis will put on the outcome: a record written under one name and an outcome arriving under another finds nothing.

[A sale a stopping host sends](the-sale-a-host-sends-as-it-stops.md) keeps the answered name in a list of its own and [waits on that](what-a-stopping-host-waits-for.md), where the record it builds after the send holds together.

## Related

- [The name an order comes back with](the-name-an-order-comes-back-with.md)
- [When the money set aside moves onto an order](when-money-set-aside-moves-onto-an-order.md)

---

Created 2026-10-26 16:26 UTC · Last modified 2026-10-26 16:26 UTC
