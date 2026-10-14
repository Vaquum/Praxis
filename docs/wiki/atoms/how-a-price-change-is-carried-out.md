---
row: P3-25
baseline: 49aa659
created: 2026-10-12 00:45 UTC
modified: 2026-10-14 08:50 UTC
evidence:
  - claim: "A price change on a single order cancels the resting order and places a fresh one"
    source: "`execution_manager.py` 8716 and 8746 into 8786-8795, the fresh one sent from 8810-8813"
  - claim: "The change is written down before the cancel goes out, and read back on a restart, so the next name follows rather than repeating one"
    source: "`execution_manager.py` 8695-8697 into 8700-8713, ahead of the cancel at 8716, read back at 1140-1143"
  - claim: "What the cancelled order really filled is settled before anything is placed, the venue being asked only where its figure stands above the record"
    source: "`execution_manager.py` 8779-8782 into 8168-8169, reached before 8786"
  - claim: "A fill that cannot be accounted for parks the change and leaves the original unfinished"
    source: "`execution_manager.py` 8783-8784 with 8747-8748"
  - claim: "The fresh order is sized from the command's whole amount less everything recorded filled across its orders"
    source: "`execution_manager.py` 8797-8799 summing 2674-2683"
  - claim: "A replay counts each change and rewrites the request's price, and a part-shown order's shown amount with it"
    source: "`execution_manager.py` 1140-1151 into 10247-10254"
  - claim: "The change is held in memory alone, so a stop before the cancel leaves the order resting and one after it leaves nothing standing"
    source: "`execution_manager.py` 8713 before 8716, the cancel written at 8794 before the replacement at 8810-8813"
---
# How a price change is carried out

A **price change** on a [single order](changing-work-already-sent.md) replaces that order rather than editing it. The order resting at the [venue](what-a-venue-is.md) is cancelled, and a fresh one is placed for what is left to trade.

## The order of it

The change is written down before the cancel goes out. What the cancelled order filled is settled before anything is placed — the venue asked only where its figure stands above the record — so a fill that arrived while the cancel was in flight is on the books first. Only then is [the cancelling](how-a-trade-is-cancelled.md) written down, and the fresh order sent. The two never rest at the venue together by this road.

## What is left to trade

The fresh order is sized from the whole amount the [request](what-a-trade-is.md) named, less everything recorded filled across that request's orders, open and closed alike. The record having been brought up to the venue's figure first, a fill the cancel raced is counted rather than ordered twice.

## When the figures will not settle

Where the asking cannot be made to agree, the change is parked and the original left unfinished on purpose. The missed fill stays recoverable that way, rather than stranded under an order the record has closed.

## What a restart keeps of it

A replay counts each change and rewrites the request's price, and [a part-shown order](part-shown-orders.md)'s shown amount with it. That count is what the next name is built from, so a restart names onward.

The change is held in memory alone, and the window the stop lands in decides what is left: before the cancel the old order still rests; between the cancel and the replacement nothing stands at all; past that the fresh order is there, to be found by name.

## Related

- [Changing work already sent](changing-work-already-sent.md)
- [When a price change leaves no new order](when-a-price-change-places-nothing.md)
- [What a venue is](what-a-venue-is.md)
- [Fills and the order](fills-and-the-order.md)

---

Created 2026-10-12 00:45 UTC · Last modified 2026-10-14 08:50 UTC
