---
row: N1-07
baseline: 49aa659
created: 2026-10-18 13:00 UTC
modified: 2026-10-23 07:08 UTC
evidence:
  - claim: "A fill on an entry grows its position, where one on an exit reduces it instead"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 448-449 against 451"
  - claim: "A refusal of an exit lowers what the position has pending rather than its size, and so does an exit handled as a cancellation, an expiry included; one of an entry reaches no position at all"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 308-310 and 334-342, the change at 610, an expiry reaching 334 by the dispatch at 152-161 against the kinds at `nexus/infrastructure/praxis_connector/trade_outcome_type.py` 26-31"
  - claim: "An exit's profit is measured from the entry price, the fees it costs taken off"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 523-525 and 533"
  - claim: "The cost basis sets the money an exit gives back instead"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438, released at 242-247"
  - claim: "The position's size, entry price and cost basis are each worked out again over the size the fill leaves"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 479-485"
  - claim: "The entry price weights the price the fill reports by its size, where the cost basis adds the value it reports and the fees as they stand"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 480-482 against 483-485"
  - claim: "The position is looked at only after the money has moved, a fill whose move failed returning before it"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 224-237 before 256-258"
  - claim: "An entry fill naming no trade raises"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 463-465"
  - claim: "The raise is caught by the loop that handed the outcome over, logged, and the strategy told of that same outcome"
    source: "`nexus/core/outcome_loop.py` 402-408 then 419-425"
  - claim: "So does one naming a trade that has no position under it"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 469-471"
  - claim: "An entry fill reports no realized profit or loss, so the risk figures are left alone for one"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 448-449, read at 260 before 285-291"
---
# When an entry's position grows

A position grows when a fill arrives for the entry that opened it. [A fill on an exit](what-an-exit-outcome-changes.md) works the other way. A refusal of an exit lowers what it has pending rather than its size, and so does an exit handled as [a cancellation](how-a-trade-is-cancelled.md), an expiry among them. The same outcomes for an entry reach no position.

## The three figures worked out again

The fill adds its size to the position's, and the entry price and the cost basis are worked out again over that new size. The entry price weights the old price by the old size and the fill's by its own, over the two together. The cost basis weights the old basis the same way, then adds the value the fill came to and the fees it cost as they stand, both being amounts already.

So a position filled in pieces carries the average of the pieces rather than the first. The two are read for different things later: an exit's profit from the entry price, with that exit's fees off, and the money it gives back from the cost basis.

## Two fills that raise

An entry's position is looked at only once the money has moved, a fill whose move failed never getting this far. Past that point, a fill naming no trade raises, and so does one naming a trade with no position under it. Neither stops the loop that handed the outcome over: it logs the raise and carries on with that same outcome, so the strategy is told of a fill whose position never moved.

## Nothing is realized here

An entry's fill reports no profit or loss, and the risk figures are written only where one is. They move at the exit.

## Related

- [What an entry outcome changes](what-an-entry-outcome-changes.md)
- [What an exit outcome changes](what-an-exit-outcome-changes.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)

---

Created 2026-10-18 13:00 UTC · Last modified 2026-10-23 07:08 UTC
