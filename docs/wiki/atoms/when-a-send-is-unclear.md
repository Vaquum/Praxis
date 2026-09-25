---
row: P1-07
baseline: 49aa659
created: 2026-09-23 08:18 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "A transport failure leaving the retry loop on an order send is wrapped as a submit timeout"
    source: "`binance_adapter.py` 1637-1643, wrapping what leaves the loop at 680, either built there at 660-662 or raised at 1135-1137 and caught instead at 595-596"
  - claim: "A send with no order name of its own returns earlier and is not wrapped"
    source: "`binance_adapter.py` 1628-1631"
  - claim: "One rejection code is wrapped as a duplicate name, whatever its reason"
    source: "`binance_adapter.py` 1644-1651 with 94, the handler reading only the code"
  - claim: "Other venue errors and bad parameters are recorded failed on the spot"
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
---
# When a send's outcome is unknown

A call to the venue can fail without settling whether the order reached it. Praxis treats two such failures as unresolved and asks the venue before deciding.

## What counts as unresolved

Two wrapped failures are chased. Both wrappers cover more than their names suggest: transport failures of several kinds — a timeout, a dropped connection, a server error, a body that will not parse — become the first, and a single venue rejection code becomes the second, whatever the venue gave as its reason.

Other venue errors and bad parameters are recorded failed on the spot. [A reply Praxis cannot read](a-reply-that-cannot-be-read.md) has several endings of its own, and some of them record nothing.

## Related

- [A reply that cannot be read](a-reply-that-cannot-be-read.md)
- [Order placement](how-an-order-is-placed.md)
- [Trades, requests and orders](what-a-trade-is.md)
