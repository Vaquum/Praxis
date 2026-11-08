---
row: P75-02
baseline: 49aa659
created: 2026-11-13 06:30 UTC
modified: 2026-11-13 06:30 UTC
evidence:
  - claim: "A buy's cost is the notional with the fee added, and a buy is refused where the quote balance is below that cost"
    source: "`replay_venue_adapter.py` 490, then 491-496"
  - claim: "A buy takes that cost out of the quote balance and puts the whole size into the base one"
    source: "`replay_venue_adapter.py` 497, then 498"
  - claim: "A sell is refused where the base balance is below the size, then gives up the size and takes in the notional with the fee subtracted"
    source: "`replay_venue_adapter.py` 500-505, then 506, then 507"
  - claim: "So the fee falls on the quote balance whichever way the order goes"
    source: "`replay_venue_adapter.py` 490 into 497, or 507"
  - claim: "The other simulated venue takes its fee out of whatever the side receives instead, chosen by side"
    source: "`ledger.py` 138, subtracted at 707, or 709"
  - claim: "A buy credits the size that was resolved, which a sum of money has already had floored onto the step"
    source: "`replay_venue_adapter.py` 498, the size resolved at 455-459"
  - claim: "A balance not yet held reads as nought wherever it is read, so a first trade on an unseen asset works from nothing"
    source: "`replay_venue_adapter.py` 491, or 497, or 498, or 500, or 506, or 507"
  - claim: "The refusal names the asset that fell short and carries the venue's one code for a refused order"
    source: "`replay_venue_adapter.py` 493-495, or 502-504"
  - claim: "The base asset is taken by cutting the quote asset's name off the end of the pair, and a pair not ending in it is refused"
    source: "`replay_venue_adapter.py` 513-515, then 517"
---
# How the replay venue settles a fill

Settling a filled order on the venue a replay trades against moves both balances, and the fee lands in the same place either way.

## A buy

The cost is the notional with the fee added. A buy is refused where the quote balance is below that cost, with a complaint naming the asset that fell short.

Otherwise the cost comes out of the quote balance and the whole size goes into the base one.

## A sell

Refused where the base balance is below the size. Otherwise the size is given up and the notional, with the fee subtracted, comes in.

## Where the fee falls

On the quote balance, whichever way the order goes. A buy pays it on top of what it spends; a sell has it taken out of what it receives.

So a buy on this venue credits the size that was resolved, undiminished, and the fee shows only in the money. A buy sized by a sum of money has had that size floored onto the step first, so what is credited is the floored size rather than what the sum would have bought exactly.

[The other simulated venue](the-asset-a-fee-is-taken-in.md) arranges this differently: it takes the fee out of whatever the side receives, chosen by side.

## A balance not yet held

Read as nought wherever it is read. So a first trade on an asset the account has yet to hold works from nothing rather than failing to find it.

## The pair's two halves

The base asset is taken by cutting the quote asset's name off the end of the pair. A pair not ending in that name is refused.

## Related

- [Replay](replay.md)
- [The asset a fee is taken in](the-asset-a-fee-is-taken-in.md)
