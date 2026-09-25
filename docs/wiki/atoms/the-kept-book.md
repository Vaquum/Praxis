---
row: P2-26
baseline: 49aa659
created: 2026-09-25 19:08 UTC
modified: 2026-09-25 19:07 UTC
evidence:
  - claim: "A copy of the latest book per symbol, held in memory with its arrival time"
    source: "`book_cache.py` 38 for the store, 44-45 for the write, 29-31 for what a copy holds"
  - claim: "One poller per symbol being traded, started when the host starts"
    source: "`launcher.py` 3819-3831"
  - claim: "Each poll overwrites the copy for that symbol"
    source: "`book_poller.py` 76-77"
  - claim: "One reader builds the gap and the age"
    source: "`book_cache.py` 124-125 and 134-139"
  - claim: "It builds the drift only when a strategy price was supplied and is above zero"
    source: "`book_cache.py` 130-132"
  - claim: "The other reads the middle of the gap alone"
    source: "`book_cache.py` 82"
  - claim: "Either returns nothing with no copy, an empty side, a best buy price at or below zero, or a crossed book"
    source: "`book_cache.py` 110-122, matching 66-80"
  - claim: "A poller that will not start is logged and the host trades on"
    source: "`launcher.py` 3805-3810"
  - claim: "The store begins empty"
    source: "`book_cache.py` 38"
  - claim: "A failed poll leaves the copy as it was"
    source: "`book_poller.py` 85-88"
---
# The kept book

The **kept book** is Praxis's own copy of the latest [order book](the-order-book.md) for a symbol, held in memory with the time it arrived, so a check can read a price without waiting on the [venue](what-a-venue-is.md).

One poller runs for each symbol being traded. Every couple of seconds it fetches five levels and overwrites that symbol's copy.

## What reads it

Two readers use the copy, and neither talks to the venue.

One serves the checks a request passes before it is accepted. It always builds the gap between the best buy and sell prices, and how old the copy is. It builds a third figure — how far the middle of that gap sits from the price the strategy expected — only when a strategy price came with the request and is above zero.

The other reads the middle of the gap alone, to turn an amount of money into an amount of coin.

Both return nothing in the same four cases: no copy has arrived, one side is empty, the best buy price is at or below zero, or the best buy price stands above the best sell price.

## When polling fails

The store begins empty, and only a successful poll puts anything in it.

So where a poller fails to start, both readers stay silent for that symbol for as long as the host runs. A poll that fails after earlier ones succeeded is different: it is logged, the loop carries on, and both readers go on answering from a copy that is growing older.

## Related

- [The order book](the-order-book.md)
- [What a venue is](what-a-venue-is.md)
