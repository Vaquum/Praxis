---
row: P3-26
baseline: 49aa659
created: 2026-10-12 01:40 UTC
modified: 2026-10-12 01:40 UTC
evidence:
  - claim: "A cancel the venue does not confirm leaves the order live and places nothing"
    source: "`execution_manager.py` 8717-8723"
  - claim: "An order the venue still calls live places nothing either, and is left alone"
    source: "`execution_manager.py` 8725-8732"
  - claim: "What is left at or below the venue's smallest size is never placed, and the request is reported filled on what it already has"
    source: "`execution_manager.py` 8803-8808, reported at 10471-10479"
  - claim: "A replacement that times out, is refused, or cannot be found afterwards ends the request cancelled on what it had filled"
    source: "`execution_manager.py` 10355-10365, reported at 10505-10512"
---
# When a price change places nothing

[A price change](how-a-price-change-is-carried-out.md) replaces the resting order, and several things stop the replacement ever going out. Each leaves the request in a different state.

## The cancel does not settle

Where the venue neither confirms the cancel nor answers what the order came to, the order is left live and nothing is placed. The request keeps waiting, and a later pass or a restart has to deal with it.

Where the venue answers and the order is still working, nothing is placed either, and the order is again left as it is.

## Too little is left to trade

Where what remains is at or below the smallest size the venue trades in, no order can carry it. The request is reported filled on what it already has, and the remainder is left as dust.

## The replacement will not go

Where the replacement times out, the venue is asked about it first, and the change carries on where the venue has it. Where it is refused, or the asking cannot be answered, the request ends cancelled — reported on what the old order and the failed replacement filled between them, the original being gone by then. The venue may still be holding that replacement, which is [recorded](../register.md) as U-01.

## Related

- [How a price change is carried out](how-a-price-change-is-carried-out.md)
- [When a send is unclear](when-a-send-is-unclear.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)

---

Created 2026-10-12 01:40 UTC · Last modified 2026-10-12 01:40 UTC
