---
row: P1-07
baseline: 49aa659
created: 2026-09-23 08:18 UTC
modified: 2026-11-14 11:30 UTC
evidence:
  - claim: "A transport failure leaving the retry loop on an order send is wrapped as a submit timeout, where the send carried a name of its own"
    source: "`binance_adapter.py` 1633-1636 under the wrap at 1637-1643, past the test at 1628, taking what leaves the loop at 680, either built there at 660-662 or raised at 1135-1137 and caught instead at 595-596"
  - claim: "A send with no order name of its own returns earlier and is not wrapped"
    source: "`binance_adapter.py` 1628-1631"
  - claim: "One rejection code is wrapped as a duplicate name, whatever its reason, where the send carried a name of its own"
    source: "`binance_adapter.py` 1644-1651 past the test at 1628, with 94, the handler reading only the code"
  - claim: "Other venue errors and settings the venue will not accept are recorded failed on the spot"
    source: "either `execution_manager.py` 4292-4295 or 4296-4299"
  - claim: "Either wrap triggers a lookup before the send is called failed"
    source: "`execution_manager.py` 4282-4290"
  - claim: "The lookup asks the venue about the name Praxis used"
    source: "`execution_manager.py` 5518-5523, or for an OCO leaving instead at 5513-5516 for the list lookup at 5582"
  - claim: "A venue that has no such order makes the send a failure"
    source: "`execution_manager.py` 5524-5532"
  - claim: "A first lookup failing with a venue error makes the send a failure"
    source: "`execution_manager.py` 5533-5542"
  - claim: "A linked pair the venue calls finished has each leg asked about"
    source: "`execution_manager.py` 5616-5619, the legs queried at 5670-5676"
  - claim: "The first leg query failing with a venue error ends the asking and the whole pair counts as live"
    source: "the loop at `execution_manager.py` 5670-5676 returning for all of it at 5677-5688"
  - claim: "A found list that is neither rejected nor finished is adopted as live without asking its legs"
    source: "`execution_manager.py` 5620-5621, instead of the rejection at 5606-5614 or the leg query at 5616-5619"
  - claim: "A trade for an order already closed is taken in, adding to its amount, money and a buy's commission in the coin while its status stands"
    source: "`praxis/core/trading_state.py` 417-424, reached from `trading.py` 1753-1757"
  - claim: "Anything other than a trade for an already-closed order is passed over"
    source: "`trading.py` 1746-1751"
  - claim: "The name cannot be used again, a second request under it being refused as in use"
    source: "`execution_manager.py` 3452-3457"
---
# When a send's outcome is unknown

A call to the venue can fail without settling whether the order reached it. Praxis treats two such failures as unresolved and asks the venue before deciding.

## What counts as unresolved

Two kinds of failure send Praxis back to the venue to ask. Both kinds cover more than their names suggest: transport failures of several kinds — a timeout, a dropped connection, a server error, a body that will not parse — become the first, and a single venue rejection code becomes the second, whatever the venue gave as its reason.

Other venue errors and settings the venue will not accept are recorded failed on the spot. [A reply Praxis cannot read](a-reply-that-cannot-be-read.md) ends several ways of its own, and some of them record nothing.

## A fill that arrives after the answer

A send written off as refused leaves an order in the closed half of the record. A trade for it arriving later on the venue's feed is still taken in: its amount, its money and any commission a buy was charged in the coin are added to that closed order, and the order keeps the status it was closed with. Anything other than a trade for an already-closed order is passed over.

So a late fill corrects the figures and leaves the ending alone. Nothing revisits the outcome already reported, and the name cannot be used again — a second request under it is refused as in use.

## Related

- [A reply that cannot be read](a-reply-that-cannot-be-read.md)
- [Order placement](how-an-order-is-placed.md)
- [Trades, requests and orders](what-a-trade-is.md)
