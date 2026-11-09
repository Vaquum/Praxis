---
row: P92-01
baseline: 49aa659
created: 2026-11-13 23:30 UTC
modified: 2026-11-13 23:30 UTC
evidence:
  - claim: "A submitted order asks for a signed caller first, then takes the poller, the staleness span, the book and the ledger off the application"
    source: "`praxis/binsim/server.py` 325, then 326, and 327, and 328, and 329"
  - claim: "The book's age is the clock now less the moment of the poller's last good poll"
    source: "`praxis/binsim/server.py` 331, then 332"
  - claim: "The caller's own name for the order is trimmed, with an empty one standing in where none came"
    source: "`praxis/binsim/server.py` 387"
  - claim: "A name coming to nothing is refused"
    source: "`praxis/binsim/server.py` 389 into 390-393"
  - claim: "The side is turned into its own kind before either road is taken"
    source: "`praxis/binsim/server.py` 395"
  - claim: "A money-sized order walks the book for that money, then snaps the walk onto the step, sums the amount from it and weighs that against the lot rules"
    source: "`praxis/binsim/server.py` 419, then 440, then 441, then 442"
  - claim: "An amount-sized order reads its amount, refuses one at or below nought, weighs it against the lot rules, and then walks the book"
    source: "`praxis/binsim/server.py` 444, then 446 into 447-450, then 452, then 455"
  - claim: "A book with nothing in it refuses either road alike, under a code saying the book is stale"
    source: "`praxis/binsim/server.py` 418 into 420 into 425-426, or 454 into 456 into 458-460"
---
# What a submitted order is weighed against

An order sent to binsim is weighed against the caller's signature, the freshness of the book, its own name, and whichever of two ways it named a size.

## What is gathered first

A signed caller, before anything else. Then the poller, the staleness span, the book and the ledger, each taken off the application.

The book's age is the clock now less the moment of the poller's last good poll — so the age is measured from when a poll last succeeded, rather than from when the book last changed.

## The name

The caller's own name for the order is trimmed, with an empty one standing in where none came. A name coming to nothing is refused, so a caller must name its order and cannot send one unnamed.

## The two ways to size an order

The side is turned into its own kind before either road is taken.

A money-sized order walks the book for that money, then snaps the walk onto the step, sums the amount from it and weighs that against the lot rules. An amount-sized order reads its amount, refuses one at or below nought, weighs it against the lot rules, and then walks the book.

So the lot rules are weighed after the walk on one road and before it on the other. A money-sized order can only fail them once the book has told it what it would get.

## The book that has nothing

It refuses either road alike, under a code saying the book is stale.

## Related

- [When binsim turns an order away](when-binsim-turns-an-order-away.md)
