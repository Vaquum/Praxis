---
row: N5-02
baseline: 49aa659
created: 2026-10-25 11:10 UTC
modified: 2026-10-26 11:10 UTC
evidence:
  - claim: "A release asked for by order identifier alone answers success where no such order is tracked"
    source: "`nexus/core/capital_controller/capital_controller.py` 1056-1062"
  - claim: "An order in flight has its remainder taken off the in-flight figure, and one working off the working figure"
    source: "`nexus/core/capital_controller/capital_controller.py` 1064-1069"
  - claim: "An order in any other state is refused and nothing is moved"
    source: "`nexus/core/capital_controller/capital_controller.py` 1064-1076"
  - claim: "The order is then dropped and its remainder asked of the strategy's figure, which drops the strategy where what is left lands near nought, and the release answers success"
    source: "`nexus/core/capital_controller/capital_controller.py` 1078-1080 into 1096-1115, answered at 1094"
  - claim: "The remainder is what the order has left to fill plus that part's share of the fee guessed for the whole, or the whole guess where the order was for nothing"
    source: "`nexus/core/capital_controller/tracked_order.py` 120-129"
  - claim: "It is asked for where an order's money had been taken but its sending came apart, and where an ending arrives with no order record to answer it"
    source: "`praxis/launcher.py` 1989-1994 reached from `nexus/strategy/action_submit.py` 389-399, and at `praxis/launcher.py` 4476 and 4481 into 4484-4486"
---
# Releasing an order whose record was lost

A release by name is how the money behind an order is given back where the host can name the order and no longer describe it.

## The two roads to it

Two roads reach this release: an order whose money had been taken but whose sending came apart, and an ending that arrives with no order record to answer it. Both carry the identifier, and the release works from that alone.

## What it does with the name

An order in flight has its remainder taken off the in-flight figure; one working has it taken off the working figure. Either way the order is then dropped and the same remainder asked of the strategy's figure — which drops that strategy from the figures where what is left lands near nought.

An order in any other state is refused before any of that, and nothing moves.

The remainder is what the order has left to fill, plus that part's share of the fee guessed for the whole — so a release after a part-fill gives back what never went out and the fee that was set aside for it. An order that was for nothing at all releases the whole guess.

## Answering success for nothing

Where no such order is tracked, the release answers success rather than refusing. A second ask about an order already released, and an ask about one that never reached the controller, are answered the same way as a release that did something.

## Related

- [What a strategy's committed figure moves on](what-moves-a-strategys-committed-figure.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)

---

Created 2026-10-25 11:10 UTC · Last modified 2026-10-25 11:10 UTC
