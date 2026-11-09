---
row: P115-01
baseline: 49aa659
created: 2026-11-14 11:00 UTC
modified: 2026-11-14 11:00 UTC
evidence:
  - claim: "The used weight is taken from a header, read only where the header is there"
    source: "`binance_adapter.py` 2425, then 2427"
  - claim: "A header that will not read as a whole number is suppressed, leaving the figure as it was"
    source: "`binance_adapter.py` 2428, naming the one failure it suppresses"
  - claim: "A figure below nought is rejected, and only a figure at or above it is kept"
    source: "`binance_adapter.py` 2430 into 2431"
  - claim: "Keeping it also restarts the window the figure expires with"
    source: "`binance_adapter.py` 2432"
  - claim: "The order count is read only where an account was named, under the same two tests"
    source: "`binance_adapter.py` 2434 into 2435, then 2437 into 2438-2439, then 2440 into 2441"
  - claim: "Keeping the order count restarts no window, so it stands until the next header replaces it"
    source: "`binance_adapter.py` 2441, carrying no companion to 2432"
  - claim: "The warning is reckoned from the stored figure rather than the one that expires"
    source: "`binance_adapter.py` 2444, against 349-352"
  - claim: "It is given only on the crossing down, a flag remembering which side the last reckoning fell on"
    source: "`binance_adapter.py` 2445, then 2447, then 2454"
---
# What the allowance headers are trusted for

Two headers tell the adapter how much of the venue's allowance it has spent, and each is taken only if it reads as a sensible figure.

## The weight

Read only where the header is there. A header that will not read as a whole number is suppressed, leaving the figure as it was. A figure below nought is rejected.

Only a figure at or above nought is kept — and keeping it also restarts the window [the figure expires with](how-the-adapter-reckons-its-headroom.md).

## The order count

Read only where an account was named, under the same two tests. Keeping it restarts no window, so it stands until the next header replaces it.

So the two figures are taken with equal care and forgotten quite differently, and that difference lives in this one routine: the weight's keeping carries a companion line and the count's does not.

## The warning

Reckoned from the stored figure rather than the one that expires. So the warning can speak of weight the headroom reckoning would already treat as gone.

It is given only on the crossing down, a flag remembering which side the last reckoning fell on. So a long spell below the threshold warns once, and recovering above it arms the warning again.

## Related

- [How the adapter reckons its headroom](how-the-adapter-reckons-its-headroom.md)
