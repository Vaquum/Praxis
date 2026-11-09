---
row: N84-03
baseline: 49aa659
created: 2026-11-09 04:45 UTC
modified: 2026-11-09 04:45 UTC
evidence:
  - claim: "A rejection and a cancel each release the order's outstanding total from whichever pot its state names"
    source: "`nexus/core/capital_controller/capital_controller.py` 673-674, or 675-676, and 1002-1003, or 1004-1005"
  - claim: "A state naming neither pot is answered as a failure by both"
    source: "`nexus/core/capital_controller/capital_controller.py` 677 into 678-685, and 1006 into 1007-1014"
  - claim: "Both then take the order out of the book and lower the strategy's deployed figure by that same total"
    source: "`nexus/core/capital_controller/capital_controller.py` 687-688, and 1016-1017"
  - claim: "An order the book does not hold is answered as a failure and marked a broken rule by a rejection"
    source: "`nexus/core/capital_controller/capital_controller.py` 664 into 666-667, marked at 670"
  - claim: "The same absence is answered the same way by a cancel, and marked an expected miss"
    source: "`nexus/core/capital_controller/capital_controller.py` 993 into 995-996, marked at 999"
  - claim: "A state naming neither pot is marked the same two ways by the same two handlers"
    source: "`nexus/core/capital_controller/capital_controller.py` 684, and 1013"
  - claim: "Both answer a success carrying nothing else"
    source: "`nexus/core/capital_controller/capital_controller.py` 690, and 1019"
---
# How a rejection and a cancel mark the same failure

A rejection and [a cancel](how-a-trade-is-cancelled.md) do the same work to the money, and put a different mark on the same two failures.

## The work they share

Each releases the order's outstanding total from whichever pot its state names — one pot for an order in flight, another for one working. A state naming neither is answered as a failure by both.

Both then take the order out of the book and lower the strategy's deployed figure by that same total. Both answer a success carrying nothing else.

## The mark they differ on

An order the book does not hold is marked a broken rule by a rejection, and an expected miss by a cancel. A state naming neither pot is marked the same two ways by the same two handlers.

## Why that is the whole difference

A cancel can reasonably arrive for an order that has already finished — a race the caller cannot avoid — so its absence is an ordinary outcome.

A rejection arrives from the venue about an order this side believes it has out. Its absence means the two sides disagree about what exists, which is the kind of thing a reader of the marks is meant to chase.

So a caller counting broken rules counts races as such from one handler and not the other, on identical evidence.

## Related

- [What becomes of money set aside](what-becomes-of-money-set-aside.md)
- [What a fill against a reservation refuses](what-a-fill-against-a-reservation-refuses.md)
