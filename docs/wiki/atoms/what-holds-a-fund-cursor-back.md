---
row: P104-02
baseline: 49aa659
created: 2026-11-09 08:06 UTC
modified: 2026-11-09 08:20 UTC
evidence:
  - claim: "A movement in any asset but the quote one is skipped"
    source: "`praxis/trading.py` 1158 into 1159-1160"
  - claim: "Each movement is admitted to the manager, and the answer says whether it was new"
    source: "`praxis/trading.py` 1170, weighed at 1171"
  - claim: "Delivery to the caller's callback stands inside a guard whose catch names any failure"
    source: "`praxis/trading.py` 1179-1180 into 1181"
  - claim: "A failed delivery marks the pass undelivered and leaves the walk at once"
    source: "`praxis/trading.py` 1187, then 1188"
  - claim: "The cursor moves only where something was found and every one of them was delivered"
    source: "`praxis/trading.py` 1156, then 1190"
  - claim: "Where it moves, it moves to the latest moment among everything fetched"
    source: "`praxis/trading.py` 1191-1193"
---
# What holds a fund cursor back

The cursor moves forward only when every movement in the window reached the caller, and one failure holds it where it was.

## What is considered

A movement in any asset but the quote one is skipped. So the pass reads everything the venue offers and acts on one asset's worth.

## What each movement does

It is admitted to the manager, and the answer says whether it was new. Then it is handed to the caller's callback, inside a guard whose catch names any failure.

## The failure that stops the walk

A failed delivery marks the pass undelivered and leaves the walk at once. The movements after it in the window are not attempted at all.

So one listener failure costs the rest of that window, and the pass ends early rather than carrying on and reporting partial success.

## When the cursor moves

Only where something was found and every one of them was delivered. Where it moves, it moves to the latest moment among everything fetched — including the ones skipped for being in another asset.

So a window of movements all in other assets still advances the cursor past them, and a single delivery failure leaves the cursor behind every movement in the window, including the ones already delivered.

## Related

- [Where a fund pass starts looking](where-a-fund-pass-starts-looking.md)
