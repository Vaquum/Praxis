---
row: P2-13
baseline: 49aa659
created: 2026-09-25 18:31 UTC
modified: 2026-09-25 19:07 UTC
evidence:
  - claim: "Two lists of levels, each level a price and an amount"
    source: "`venue_adapter.py` 419-420 for a level, 434-436 for the pair of lists"
  - claim: "Praxis asks the venue, names a count, and builds the lists from the reply"
    source: "asked with the count at `binance_adapter.py` 2265-2270, built at 2282-2292"
  - claim: "The likely-price working-out asks for twenty levels a side"
    source: "`execution_manager.py` 4194-4197 with the count at 147"
  - claim: "Closing-out pricing asks without naming a count and reads only the top level"
    source: "asked at `execution_manager.py` 6685, read at either 6692 for a buy or 6716 for a sell"
  - claim: "A poller asks for five levels every couple of seconds"
    source: "`launcher.py` 638-639 with the count at 198 and the gap at 197"
  - claim: "Refusal, an unparsed reply and a parsed reply missing a list are three separate raises"
    source: "either `binance_adapter.py` 2272-2273, or 2277-2279, or 2294-2296"
  - claim: "Each asker catches the broad kind, which covers all three"
    source: "caught at `execution_manager.py` 4222 and 6686, the narrower kind being covered by that catch per `test_venue_adapter.py` 261"
  - claim: "Closing-out pricing falls back to the opening price"
    source: "either `execution_manager.py` 6685-6687 or 6708-6710"
  - claim: "A failed poll is logged and the loop carries on"
    source: "`book_poller.py` 85-88"
  - claim: "The working-out is skipped, and a market order with a maximum set is then refused"
    source: "skipped at `execution_manager.py` 4222-4228, refused at 4230-4240 by way of 4064-4079"
---
# The order book

An **order book** is what a [venue](what-a-venue-is.md) publishes about one symbol: two lists of levels, buyers on one side and sellers on the other, each level a price and an amount wanted at that price.

Praxis keeps no book of its own making. It asks the venue for one, says how many levels it wants, and builds the two lists from the reply.

## Who asks, and how deep

[Working out the likely price](how-the-likely-price-is-worked-out.md) asks for twenty levels a side, because it walks down them until the size is covered.

Pricing an order that closes a position out asks without naming a count and reads only the top level: the best sell price when buying back, the best buy price when selling out.

A poller asks for five levels every couple of seconds and [keeps the reply](the-kept-book.md) where checks can read it without waiting on the venue.

## When the ask fails

A refusal, a reply that cannot be parsed at all, and a parsed reply with a list missing are three separate failures, but each asker catches the broad kind that covers all three, so all three reach it the same way.

What happens next depends on who asked. Closing-out pricing falls back to the price the position was opened at. The poller writes a line to the log and carries on.

The likely-price working-out is skipped, leaving no figure — and [the likely-price check](how-the-likely-price-is-checked.md) refuses a market order when a maximum has been set for the host and no figure arrived. For that one order, a book that could not be fetched is the difference between trading and not.

## Related

- [The kept book](the-kept-book.md)
- [A reply that cannot be read](a-reply-that-cannot-be-read.md)
