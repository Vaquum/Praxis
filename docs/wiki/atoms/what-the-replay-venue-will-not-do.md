---
row: P75-06
baseline: 49aa659
created: 2026-11-08 22:30 UTC
modified: 2026-11-08 22:30 UTC
evidence:
  - claim: "Registering an account opens a balance book seeded with a copy of the starting balances the venue was built with, the copy reaching the mapping and not what it holds"
    source: "`replay_venue_adapter.py` 116"
  - claim: "Taking an account back removes its book outright, and raises where no such book is held"
    source: "`replay_venue_adapter.py` 121, removing by key"
  - claim: "Asking what an account's credentials may do raises a not-supported rather than answering"
    source: "`replay_venue_adapter.py` 126-127"
  - claim: "Turning a venue's frame into a report raises a not-supported as well, the complaint naming the absence of such a stream"
    source: "`replay_venue_adapter.py` 440-441"
  - claim: "Cancelling an order, and cancelling a linked pair, each raise a not-found outright"
    source: "`replay_venue_adapter.py` 271, and 283"
  - claim: "Offering the cached rules answers with nothing for a symbol none are held for"
    source: "`replay_venue_adapter.py` 435, reading with a default"
  - claim: "The venue's health always answers with the health record's own defaults"
    source: "`replay_venue_adapter.py` 427"
  - claim: "The venue's clock is answered as whole milliseconds taken from the simulated clock, the fraction cut away"
    source: "`replay_venue_adapter.py` 422"
  - claim: "The price every order fills at is given through a step of its own, refused unless it is finite and above nought, and read from where that step stored it"
    source: "`replay_venue_adapter.py` 107-109, then 111, read at 186"
---
# What the replay venue will not do

The venue a replay trades against carries the adapter methods, and several of them answer by declining.

## Two it declines as unsupported

Asking what an account's credentials may do. Turning a venue's frame into a report — whose complaint names the absence of such a stream. Each raises a not-supported rather than answering.

## Two it declines as not found

Cancelling an order, and cancelling a linked pair. Each raises outright, without looking anything up — every order here is filled as it is taken, so none ever rests.

## Two it answers trivially

The venue's health always answers with the health record's own defaults.

Its clock is answered as whole milliseconds taken from the simulated clock, the fraction cut away.

## The accounts

Registering one opens a balance book seeded with a copy of the starting balances the venue was built with. The copy reaches the mapping and not what it holds, so a later change to one account's figures leaves the others as they were.

Taking one back removes its book outright, and raises where no such book is held.

## The price

Every order fills at one price, given through a step of its own and read back where an order is submitted. That step refuses a price unless it is finite and above nought, so [a fill](how-the-replay-venue-settles-a-fill.md) cannot work from a price that is no quantity. When the step is called is settled by whoever drives the replay.

## Related

- [Replay](replay.md)
- [What the replay venue answers when asked](what-the-replay-venue-answers-when-asked.md)
