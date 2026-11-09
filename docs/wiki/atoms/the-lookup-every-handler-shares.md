---
row: P88-03
baseline: 49aa659
created: 2026-11-09 06:08 UTC
modified: 2026-11-09 06:08 UTC
evidence:
  - claim: "The shared lookup reads the live book alone"
    source: "`trading_state.py` 294"
  - claim: "Finding nothing there is reported as a warning naming the event that asked, the order and the account"
    source: "`trading_state.py` 295"
  - claim: "It then hands back whatever it found, nothing included, so each caller weighs that for itself"
    source: "`trading_state.py` 303"
  - claim: "One handler looks in the closed book first and answers at once where the order is already there"
    source: "`trading_state.py` 606 into 607"
  - claim: "It then goes through the shared lookup like the others, and answers where that found nothing"
    source: "`trading_state.py` 609-611, then 612-613"
  - claim: "Otherwise it marks the order filled, stamps it, and closes it"
    source: "`trading_state.py` 615, and 616, then 617"
---
# The lookup every handler shares

Every handler that needs an order asks one routine for it, and that routine reads the live book alone.

## What it does on a miss

Finding nothing there is reported as a warning naming the event that asked, the order and the account. It then hands back whatever it found, nothing included, so each caller weighs that for itself.

The warning is therefore the lookup's, and the deciding is the caller's — a handler that treats a miss as ordinary still leaves a warning behind it.

## The handler that checks twice

One handler looks in the closed book first, and answers at once where the order is already there. It then goes through the shared lookup like the others, and answers where that found nothing. Otherwise it marks the order filled, stamps it, and closes it.

## What checking twice buys

A repeat. Because [a closing moves the order to the closed book](what-closing-an-order-moves-it-to.md), a second copy of any other terminal event reaches the shared lookup, finds nothing, and leaves a warning.

This one handler finds the order in the closed book instead, and answers in silence. So the same repeat is noisy for every kind but this one, and quiet for this one by its own first line.

## Related

- [What closing an order moves it to](what-closing-an-order-moves-it-to.md)
- [How an event finds its way through the projection](how-an-event-finds-its-way-through-the-projection.md)
