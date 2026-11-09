---
row: N6-06
baseline: 49aa659
created: 2026-10-26 16:26 UTC
modified: 2026-11-09 03:10 UTC
evidence:
  - claim: "Handing a command to Praxis puts the send on another thread's loop and waits on the calling side for a name to come back"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 180-183 into 185-186"
  - claim: "That name is what the handover answers with"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 224"
  - claim: "Whether Nexus's own name travels out with the command is settled once, as the connector is built, by reading the shape of the receiving function"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 62-74 read at 105-108, each send only branching on what that left at 177-178"
  - claim: "A receiver declaring a parameter of that name is taken as bound to it; one that does not, but takes a keyword catch-all, is sent the name without being held to it; one that does neither, and one whose shape cannot be read at all, are sent no name"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 66-67, 69-74 and 61 into 63-64, acted on at 177-178"
  - claim: "The receiver the launcher hands over declares that parameter, so with Praxis's own wiring it is read as bound"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 62 reading the shape of the receiver handed over at `praxis/launcher.py` 453-454 and built at 4075, which carries the name through at 449, answering bound at `nexus/infrastructure/praxis_connector/praxis_outbound.py` 66-67"
  - claim: "A name that does not come back inside the handover's own span has the wait dropped and the handover raises"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 186-193"
  - claim: "A name coming back different from the one sent refuses the handover, and only where the receiver was taken as bound to it"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 195-198 into 210 and 214"
  - claim: "A differing name from a receiver not taken as bound is answered with as it stands"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 195-198 falling through to 224"
  - claim: "The span the handover waits is its own, and the span passed on as the order's is the one the command carries, or that same wait taken to the nearest whole second and held at one or more where the command carries none"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 186 against 152-156 into 166"
---
# The name an order comes back with

The name an order comes back with is what Praxis answers the handover with, and it may or may not be the name Nexus sent.

## The handover

Praxis runs on another thread's loop, so the send is put onto that loop and the handover waits on this side for the answer. The span it waits is its own. The span passed on as the order's is the one [the command](how-a-decision-becomes-a-command.md) carries — or, where it carries none, that same wait taken to the nearest whole second and held at one or more.

## Whose name it is

Whether Nexus's own name travels out with the command is settled once, as the connector is built, by reading the shape of the receiving function. Each send then only reads off what that settled.

A receiver declaring a parameter of that name is taken as bound to it. One that does not, but takes a keyword catch-all, is sent the name without being held to it. One that does neither is sent no name, and so is one whose shape cannot be read at all.

The receiver the launcher hands over declares the parameter, so with Praxis's own wiring the first of the three is the live case.

## The two failures

A name that does not come back inside the handover's span has the wait dropped and the handover raises, and [what follows](what-nexus-does-when-a-command-does-not-get-across.md) is the caller's own business.

A name coming back different from the one sent refuses the handover, and only where the receiver was taken as bound to it. From a receiver that is not, a differing name is answered with as it stands, and that is the road on which [the name a command is kept under](which-name-a-command-is-kept-under.md) can be the answered one.

## Related

- [Which name a command is kept under](which-name-a-command-is-kept-under.md)
- [How a decision becomes a command](how-a-decision-becomes-a-command.md)

---

Created 2026-10-26 16:26 UTC · Last modified 2026-11-09 03:10 UTC
