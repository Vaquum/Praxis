---
row: P3-26
baseline: 49aa659
created: 2026-10-12 01:40 UTC
modified: 2026-10-12 04:22 UTC
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
# When a price change places nothing

[A price change](how-a-price-change-is-carried-out.md) replaces the resting order, and several things stop the replacement ever going out. Each leaves the request in a different state.

## The cancel does not settle

Where the venue neither confirms the cancel nor answers what the order came to, the order is left live and nothing is placed. The change is not parked either: nothing is set down for a later pass to pick up, so the request is left waiting on an order that is still working.

Where the venue answers and the order is still working, nothing is placed either, and the order is again left as it is.

## Too little is left to trade

What remains is weighed against the smallest size the venue trades in, as loaded for that symbol when the account started. Where it falls short, no order can carry it: the request is reported filled on what it already has, and the remainder is left as dust. An amount equal to that smallest size still goes.

Where no size was loaded for the symbol, the weighing is against zero instead, and any remainder at all is placed, however far under what the venue will take.

## The replacement will not go

Where the replacement times out, the venue is asked about it first, and the change carries on where the venue has it. Where it is refused, or the asking cannot be answered, the request ends cancelled — reported on what the old order and the failed replacement filled between them, the original being gone by then. The venue may still be holding that replacement, which is [recorded](../register.md) as U-01.

## Related

- [How a price change is carried out](how-a-price-change-is-carried-out.md)
- [When a send is unclear](when-a-send-is-unclear.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)

---

Created 2026-10-12 01:40 UTC · Last modified 2026-10-12 04:22 UTC
