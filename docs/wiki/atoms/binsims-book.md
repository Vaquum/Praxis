---
row: P3-06
baseline: 49aa659
created: 2026-09-28 10:46 UTC
modified: 2026-09-28 17:34 UTC
evidence:
  - claim: "The book is replaced whole rather than changed in part"
    source: "`book.py` 115-116"
  - claim: "A background poller fetches and replaces it, waiting between goes"
    source: "`feed.py` 157 into 267, waiting at 303-329"
  - claim: "An interval that is not above zero is refused"
    source: "`feed.py` 100-101"
  - claim: "An order sized in coin takes from each level what it holds, or what is left"
    source: "`book.py` 162-163"
  - claim: "An order sized in money compares each level's cost with the budget left"
    source: "`book.py` 226-239"
  - claim: "Walking stops when nothing is left to fill"
    source: "`book.py` 159-160"
  - claim: "The walk returns what the levels gave, which can be less than asked"
    source: "`book.py` 166"
  - claim: "A send the book cannot cover is refused before anything is booked"
    source: "either `server.py` 430-438 or 463-472"
  - claim: "An amount that is not a real figure, or not above zero, is refused"
    source: "`book.py` 144-148"
---
# Binsim's book

The book [the simulated venue](binsim.md) fills against is a list of prices it is handed, rather than one it builds. A background poller fetches a fresh one, replaces the whole thing, waits, and goes again — refusing an interval that is not above zero.

So nothing anyone sends to binsim ever joins its book. The book comes from outside and is only ever read.

## Filling against it

An order sized in coin takes from each level what that level holds, or what is left to fill, whichever is smaller. An order sized in money works differently: it compares each level's cost against the budget left, and divides by the price to get the amount.

Either way the walk stops once nothing is left, and returns what the levels gave.

## When the book is too thin

The walk can give less than was asked for. That shortfall is not a partial fill: the send is refused outright before anything reaches [the balances](binsims-ledger.md).

So an order larger than the book showing at that moment fails, rather than filling what it can.

## Between replacements

The book does not move between one replacement and the next, however many orders are filled against it.

Two sends moments apart therefore see exactly the same prices and the same depth, and neither leaves a mark on what the other sees.

## Related

- [Binsim](binsim.md)
- [Binsim's ledger](binsims-ledger.md)
