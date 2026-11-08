---
row: P75-03
baseline: 49aa659
created: 2026-11-13 06:30 UTC
modified: 2026-11-13 06:30 UTC
evidence:
  - claim: "A symbol the venue holds no rules for has its quantity passed through unchanged and unrefused"
    source: "`replay_venue_adapter.py` 139-141"
  - claim: "A quantity below the smallest size is refused before any snapping is done"
    source: "`replay_venue_adapter.py` 143-146"
  - claim: "The snapping is a floor onto the step, so a quantity between two steps becomes the lower"
    source: "`replay_venue_adapter.py` 148"
  - claim: "A snapped quantity at or below nought, or below the smallest size, is refused with the same reason as one that was below it to begin with"
    source: "`replay_venue_adapter.py` 149-152, against 143-146"
  - claim: "A reference price given turns the snapped quantity into a value, refused where that value is below the smallest the venue takes"
    source: "`replay_venue_adapter.py` 154-157"
  - claim: "With no reference price given, that last check is skipped and the snapped quantity is answered"
    source: "`replay_venue_adapter.py` 154, then 159"
  - claim: "A sum of money is turned into a size by dividing by the price, and then floored onto the step where rules are held"
    source: "`replay_venue_adapter.py` 456, then 457-459"
  - claim: "Neither a size nor a sum of money is refused with its own reason, and a size resolving to nought or below is refused after either road"
    source: "`replay_venue_adapter.py` 463-467, then 469-474"
---
# What the replay venue snaps a quantity to

A quantity offered to the venue a replay trades against is brought onto the venue's grid by one step, which answers either with a snapped quantity or with a reason.

## No rules, no change

A symbol the venue holds no rules for has its quantity passed through unchanged. Nothing is snapped and nothing is refused.

## The order of the checks

A quantity below the smallest size is refused before any snapping is done.

The snapping is then a floor onto the step, so a quantity between two steps becomes the lower of them.

A snapped quantity at or below nought, or below the smallest size, is refused — with the same reason as one that was below the minimum to begin with. So a caller reading the reason cannot tell a quantity that was too small from one the snapping made too small.

## The check that may not happen

A reference price, where one is given, turns the snapped quantity into a value, and that value below the smallest the venue takes is refused.

With no reference price, that check is skipped and the snapped quantity is answered.

## A sum of money instead of a size

Divided by the price to give a size, then floored onto the step where rules are held.

Neither a size nor a sum given is refused with a reason of its own, and a size resolving to nought or below is refused after either road.

## Related

- [What the replay venue refuses before it fills](what-the-replay-venue-refuses-before-it-fills.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)
