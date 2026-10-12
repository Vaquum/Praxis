---
row: P3-26
baseline: 49aa659
created: 2026-10-12 01:40 UTC
modified: 2026-10-12 10:12 UTC
evidence:
  - claim: "A cancel the venue does not confirm leaves the order live and places nothing, and parks no change for a later pass"
    source: "`execution_manager.py` 8717-8723, returning before the parking at 8747-8748"
  - claim: "An order the venue still calls live places nothing either, and is left alone"
    source: "`execution_manager.py` 8725-8732"
  - claim: "What is left is weighed against the smallest size loaded for that symbol, and falling short the request is reported filled on what it already has"
    source: "`execution_manager.py` 8799-8808, reported at 10471-10479"
  - claim: "Where no size was loaded for the symbol the weighing is against zero, so any remainder at all is placed"
    source: "`execution_manager.py` 8800-8801 reading the cache at `binance_adapter.py` 2153, filled only from `trading.py` 562"
  - claim: "A replacement that times out, is refused, or cannot be found afterwards ends the request cancelled on what it had filled"
    source: "`execution_manager.py` 10355-10365, reported at 10505-10512"
---
# When a price change leaves no new order

[A price change](how-a-price-change-is-carried-out.md) replaces the resting order, and several things leave the request with no replacement it can account for. The first three stop the send before it happens, each leaving the request differently placed; the last is a send that went out and came back unconfirmed, where the replacement may be resting after all.

## The cancel does not settle

Where the venue neither confirms the cancel nor answers what the order came to, the order is left live and nothing is placed. Nothing is parked for a later pass either, so the request waits on an order that is still working.

Where the venue answers and the order is still working, nothing is placed and the order is again left as it is.

## Too little is left to trade

What remains is weighed against [the smallest size the venue trades in](the-sizes-a-venue-trades-in.md), as loaded for that symbol at startup. Falling short, it cannot be carried: the request is reported filled on what it has, and the remainder is left as dust. An amount equal to that size still goes.

With no size loaded for the symbol, the weighing is against zero, so any remainder at all is placed, however far under what the venue takes.

## The send is not confirmed

The order has gone to the venue here. Where the send times out, the venue is asked about it, and the change carries on where the venue has it. Where it is refused, or the asking cannot be answered, the request ends cancelled — reported on what the old order and the failed replacement filled between them, the original being gone by then. The venue may still be holding that replacement, which is [recorded](../register.md) as U-01.

## Related

- [How a price change is carried out](how-a-price-change-is-carried-out.md)
- [When a send is unclear](when-a-send-is-unclear.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)

---

Created 2026-10-12 01:40 UTC · Last modified 2026-10-12 10:12 UTC
