---
row: N6-09
baseline: 49aa659
created: 2026-10-26 16:26 UTC
modified: 2026-10-26 16:26 UTC
evidence:
  - claim: "Where the receiver was taken as bound to the name sent, the claim on the money is made before the send"
    source: "`praxis/launcher.py` 2088-2093, built only at 4239-4254 and reached from `nexus/strategy/action_submit.py` 313-315 before 337"
  - claim: "Where it was not, no claim is made before the send, and one is made after it under the name that came back"
    source: "`praxis/launcher.py` 4239-4254 against 4287-4293, after `nexus/strategy/action_submit.py` 337"
  - claim: "A claim refused after the send is logged and the registration is dropped, but only where this attempt put it there"
    source: "`praxis/launcher.py` 4295-4311"
  - claim: "The launcher hands Nexus a receiver that does declare the name, so with its own wiring this road is never taken"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 62 reading the shape of the receiver the launcher hands over at `praxis/launcher.py` 453-454 and builds at 4075, which carries the name through at 449, answering bound at `nexus/infrastructure/praxis_connector/praxis_outbound.py` 66-67, which returns before the road at `praxis/launcher.py` 4270-4271"
  - claim: "Where the registration goes, the strategy behind that command can no longer be named, and the loop reading outcomes parks the outcome rather than working it through"
    source: "`praxis/launcher.py` 4336-4339 read at `nexus/core/outcome_loop.py` 396-399 before 401-403, the parking at 230-231"
  - claim: "Where it stands, because an earlier attempt put it there, the outcome is worked through on the ordinary road only if that registration carries a record of the order"
    source: "`praxis/launcher.py` 4281-4285 against 4309-4310, read at 4471-4476 into 4499, a record left unmade at 1500-1501"
---
# Claiming the money after the send

Claiming the money after the send is the road Praxis takes where the receiving function it gave Nexus was not [read as bound to the name sent](which-name-a-command-is-kept-under.md) — the command goes first, and the claim follows.

## Which road

Where the receiver was [taken as bound to the name sent](which-name-a-command-is-kept-under.md), the claim is made before the send. Where it was not, no claim is made then: the command goes first, and the claim is made afterwards under the name that came back.

The launcher hands Nexus a receiver that does declare the name, so with its own wiring this road is never taken: it is there for a Praxis that cannot be read as holding to the name.

## What a refusal costs there

The command is already handed over: the send has come back with a name. The refusal is logged and the registration is dropped, but only where this attempt put it there.

Where it goes, the loop reading outcomes can no longer name the strategy behind that command, so an outcome for it is [parked rather than worked through](an-outcome-waiting-on-a-strategy.md). Where it stands, because an earlier attempt put it there, the outcome is worked through on the ordinary road — but only if that registration carries a record of the order; one left without reaches [the road for an order with no record](releasing-an-order-whose-record-was-lost.md).

## Related

- [What becomes of money set aside](what-becomes-of-money-set-aside.md)
- [Which name a command is kept under](which-name-a-command-is-kept-under.md)

---

Created 2026-10-26 16:26 UTC · Last modified 2026-10-26 16:26 UTC
