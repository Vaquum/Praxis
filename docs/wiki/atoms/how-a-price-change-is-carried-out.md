---
row: P3-25
baseline: 49aa659
created: 2026-10-12 00:45 UTC
modified: 2026-10-12 01:51 UTC
evidence:
  - claim: "A price change on a single order cancels the resting order and places a fresh one"
    source: "`execution_manager.py` 8716 and 8746 into 8786-8795, the fresh one sent from 8797-8799"
  - claim: "The change is written down before the cancel goes out, and read back on a restart, so the next name follows rather than repeating one"
    source: "`execution_manager.py` 8695-8697 into 8700-8713, ahead of the cancel at 8716, read back at 1140-1143"
  - claim: "The venue is asked what the cancelled order really filled before anything is placed"
    source: "`execution_manager.py` 8779-8782, reached before 8786"
  - claim: "A fill that cannot be accounted for parks the change and leaves the original unfinished"
    source: "`execution_manager.py` 8783-8784 with 8747-8748"
  - claim: "The fresh order is sized from the command's whole amount less everything recorded filled across its orders"
    source: "`execution_manager.py` 8797-8799 summing 2674-2683"
  - claim: "What is left at or below the venue's smallest size is never placed, and the request is reported filled on what it already has"
    source: "`execution_manager.py` 8803-8808, reported at 10471-10479"
---
# How a price change is carried out

A **price change** on a [single order](changing-work-already-sent.md) replaces that order rather than editing it. The order resting at the [venue](what-a-venue-is.md) is cancelled, and a fresh one is placed for what is left to trade.

## The order of it

The change is written down before the cancel goes out, so a restart in the middle counts it and names the fresh order next in sequence rather than reusing a name. The venue is asked what the cancelled order really filled before anything is placed, so a fill that arrived while the cancel was in flight is on the books first. Only then is [the cancelling](how-a-trade-is-cancelled.md) written down, and only then does the fresh order go out. The two never rest at the venue together by this road.

## What is left to trade

The fresh order is sized from the whole amount the [request](what-a-trade-is.md) named, less everything recorded filled across that request's orders — open and closed alike. Because the record was brought up to the venue's figure first, a fill the cancel raced is counted rather than ordered a second time.

## When nothing is placed

Where what is left is at or below the smallest size the venue trades in, nothing is placed: the request is reported filled on what it already has, and the remainder is left as dust.

## When the figures will not settle

Where the asking cannot be made to agree, the change is parked and the original is deliberately left unfinished. The missed fill stays recoverable that way, rather than being stranded under an order the record has already closed.

## Related

- [Changing work already sent](changing-work-already-sent.md)
- [What a venue is](what-a-venue-is.md)
- [Fills and the order](fills-and-the-order.md)

---

Created 2026-10-12 00:45 UTC · Last modified 2026-10-12 01:51 UTC
