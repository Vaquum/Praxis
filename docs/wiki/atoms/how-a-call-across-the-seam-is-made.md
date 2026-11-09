---
row: N47-01
baseline: 49aa659
created: 2026-11-12 04:30 UTC
modified: 2026-11-13 14:30 UTC
evidence:
  - claim: "Each way across refuses before calling where the function it would call was never configured"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 248-250, or 303-305, or 343-345, or 361-363, or 400-402, or 434-436"
  - claim: "Four of them hand the call to the host's loop from another thread and wait on it for one span"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 256-264 into 266-267, or 311-321 into 323-324, or 365-368 into 371, or 404-409 into 411-412"
  - claim: "A wait that runs out asks for the pending call to be cancelled, reports the timeout, and raises on"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 268-271, or 326-328, or 372-375, or 413-416"
  - claim: "The asking neither waits for the cancelling nor reads whether it took"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 269, whose answer nothing reads"
  - claim: "Two call straight through instead: registering an account, and pulling its positions"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 347-348, or 438"
  - claim: "The span is the same one for every call that waits"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 267, and 324, and 371, and 412, each reading the one span"
---
# How a call across the seam is made

Every call Nexus makes into Praxis goes through one connector. Each begins the same way, and most of them then cross by the same road.

## Refused before calling

Each way across holds the function it would call. Where that function was never wired in, the call is refused there and then — a failure about the wiring rather than about Praxis.

## Handed over, and waited on

Four of them hand the call to Praxis's own loop from outside it, since the connector is called from Nexus's threads while Praxis runs its work on that loop. The caller then waits on the result for one span, the same span for every call that waits.

## When the span runs out

The pending call is asked to cancel, the timeout is reported, and the failure is raised on.

The asking neither waits for the cancelling nor reads whether it took, so the far side may still be working on a call its caller has given up on.

A response arriving inside the span returns normally. Only one later than the span is indistinguishable, to the caller, from no response at all.

## The two that cross directly

Registering an account, and pulling its positions. Neither goes to the loop and neither waits, so the span never applies to them, and a caller learns of a failure only by what the call itself raises.

## Related

- [The name an order comes back with](the-name-an-order-comes-back-with.md)
- [The marker a command's moment must carry](the-marker-a-commands-moment-must-carry.md)
- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
