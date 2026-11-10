---
row: P2-48
baseline: 49aa659
created: 2026-10-13 06:45 UTC
modified: 2026-10-13 06:45 UTC
evidence:
  - claim: "A snapshot whose top levels on either side sum below a floor is logged and dropped, no order size being consulted"
    source: "`praxis/binsim/feed.py` 219-235"
  - claim: "A snapshot whose update number has not moved for the allowed run of polls is logged and dropped"
    source: "`praxis/binsim/feed.py` 249-265, the book replaced only past it at 267"
  - claim: "A body that cannot be read is logged, and the polling carries on"
    source: "`praxis/binsim/feed.py` 312-326, waiting again at 328-330"
  - claim: "So is a readable body the book refuses: a side out of price order, a crossed best pair, a level at or below nought, or an update number below the one standing"
    source: "`praxis/binsim/book.py` 81-91, 93-103, 105-108 and 110-113, raised into `praxis/binsim/feed.py` 312"
  - claim: "An endless value, or one that is not a number, is refused as the body is read, before the sums"
    source: "`praxis/binsim/feed.py` 381-384, reached from 364-365 before 219-220"
  - claim: "A dropped snapshot leaves the one already held standing, orders filling against that"
    source: "`praxis/binsim/feed.py` 267 reached in neither case, read for orders at `praxis/binsim/server.py` 328"
  - claim: "Where none was ever accepted there is no book, and an order meets the staleness refusal"
    source: "`praxis/binsim/server.py` 338-342"
  - claim: "The age the staleness refusal reads is taken from the clock as a snapshot lands, leaving the time written inside one for other purposes"
    source: "`praxis/binsim/feed.py` 280 against the book's own stamp at 267, read at `praxis/binsim/server.py` 332"
---
# What a binsim snapshot is turned away for

A snapshot is one answer to [the simulated venue](binsim.md)'s poll for the real venue's depth, and the only thing that moves [its book](binsims-book.md) on. One too thin, one bringing no news, and one the book itself refuses are each dropped.

## Too thin to trade against

The top levels of each side are added up, and one whose buy or sell side comes to less than a floor is dropped, no order's size being consulted. Reading the body turns every price and amount into a finite decimal: an endless value, or one that is not a number, is refused there, before the sums.

## Not moving

Each snapshot carries a number the real venue advances as the book changes. One that has not moved for an allowed run of polls is read as a feed that stopped bringing news, and dropped too.

## Refused on its own terms

A body that cannot be read — bad shape, bad numbers — is logged, and the polling waits and goes round. So is one that reads perfectly well and the book itself refuses: a side out of price order, a best buy at or above the best sell, a level at or below nought, or an update number below the one standing.

## What a drop leaves behind

A drop leaves the last snapshot accepted standing as the book, and orders go on filling against it. What catches up with that is the age: the clock the [staleness refusal](when-binsim-turns-an-order-away.md) reads is taken as a snapshot lands, so a feed whose snapshots keep being dropped passes that check until the age crosses the threshold, then fails it for every order. Where none was ever accepted there is no book, and an order meets that same refusal.

## Related

- [Binsim](binsim.md)
- [Binsim's book](binsims-book.md)
- [When binsim turns an order away](when-binsim-turns-an-order-away.md)

---

Created 2026-10-13 06:45 UTC · Last modified 2026-10-13 06:45 UTC
