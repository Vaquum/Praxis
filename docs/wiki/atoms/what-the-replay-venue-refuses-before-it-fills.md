---
row: P75-01
baseline: 49aa659
created: 2026-11-08 22:30 UTC
modified: 2026-11-08 22:30 UTC
evidence:
  - claim: "A kind of order other than a market one is refused, with a complaint naming the kind that arrived"
    source: "`replay_venue_adapter.py` 179-184"
  - claim: "A venue with no current price refuses next, so the price is in hand before the account is looked for"
    source: "`replay_venue_adapter.py` 186-192, ahead of 194-200"
  - claim: "An account the venue does not hold is refused third"
    source: "`replay_venue_adapter.py` 194-200"
  - claim: "A size and a sum of money together are refused, and a sum of money on anything but a buy is refused after that"
    source: "`replay_venue_adapter.py` 202-207, then 209-214"
  - claim: "Every refusal in the module carries the same venue code and differs only in its reason and its words"
    source: "`replay_venue_adapter.py` 182, or 190, or 198, or 205, or 212, or 465, or 472, or 494, or 503"
  - claim: "Four more refusals stand past those five: no size and no sum at all, a size resolving to nought or below, a quote balance too small, and a base balance too small"
    source: "`replay_venue_adapter.py` 463-467, and 469-474, then 491-496, or 500-505"
  - claim: "A pair not ending in the quote asset's name is refused by a different kind of failure, raised while the base asset is taken"
    source: "`replay_venue_adapter.py` 513-515, reached from 219"
  - claim: "The size is then settled, the notional taken as that size times the price, and the fee as the notional times one rate held for the whole venue"
    source: "`replay_venue_adapter.py` 216, then 217, then 218"
  - claim: "The order is recorded as wholly filled, with an identifier for the order and one for the execution both built from a single rising count"
    source: "`replay_venue_adapter.py` 223-225, recorded at 229-232"
  - claim: "A caller giving no name of its own has the venue's name used in its place"
    source: "`replay_venue_adapter.py` 226"
---
# What the replay venue refuses before it fills

The venue a replay trades against fills every order it accepts in full, at one price. Five refusals stand before it works anything out, and four more past that.

## The five, in order

A kind of order other than a market one, with a complaint naming the kind that arrived.

A venue with no current price. So the price is in hand before the account is even looked for.

An account the venue does not hold.

A size and a sum of money given together.

A sum of money on anything but a buy.

## The four that come later

Two while the size is worked out — no size and no sum at all, and a size resolving to nought or below — and two [while the balances are moved](how-the-replay-venue-settles-a-fill.md).

So a caller past the first five has not been accepted, only had its figures taken.

## What the refusals have in common

Every one carries the same venue code, differing only in its reason and its words. A caller sorting by that code cannot tell them apart; one reading the reason can.

One stands apart: a pair not ending in the quote asset's name is raised as a different kind of failure, while the base asset is taken.

## What is worked out next

The size, then the notional as that size times the price, then the fee as the notional times one rate held for the whole venue. So every order here pays the same rate.

## What is recorded

The order, as wholly filled, with an identifier for the order and one for the execution both built from a single rising count. A caller giving no identifier of its own has the venue's used in its place.

## Related

- [Replay](replay.md)
- [How the replay venue settles a fill](how-the-replay-venue-settles-a-fill.md)
