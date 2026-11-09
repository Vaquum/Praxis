---
row: P183-02
baseline: 49aa659
created: 2026-11-09 13:31 UTC
modified: 2026-11-09 13:31 UTC
evidence:
  - claim: "A price named outright is used as named"
    source: "`execution_manager.py` 5208, then 5209, or 5218, then 5219"
  - claim: "A price given as an offset is worked out from the entry's average and snapped"
    source: "`execution_manager.py` 5211, then 5212-5216, or 5221, then 5222-5226"
  - claim: "The direction the offset is applied in turns on the side of the entry"
    source: "`execution_manager.py` 5206"
  - claim: "Snapping floors the price to a whole number of the venue's ticks"
    source: "`execution_manager.py` 5246"
  - claim: "A symbol whose venue sizes are not held has its price left exactly as it was"
    source: "`execution_manager.py` 5242, then 5243 into 5244"
  - claim: "The stop's own limit price is passed through as given, snapped by nothing"
    source: "`execution_manager.py` 5228"
  - claim: "On a change all three prices are snapped, including the stop's limit"
    source: "`execution_manager.py` 9873, and 9884, and 9895"
---
# What the venue's tick does to a protective price

A protective price goes to the venue floored to a whole number of the venue's ticks, and the flooring is skipped for a symbol whose venue sizes are not held.

## Named or worked out

A price named outright is used as named. A price given as an offset is worked out from the entry's average price and then snapped, with the direction the offset is applied in turning on the side of the entry.

So an offset-priced pair is always on the tick grid, and an outright-priced pair is whatever the caller said — at first placement.

## What snapping is

Flooring to a whole number of the venue's ticks. A symbol whose venue sizes are not held has its price left exactly as it was, which is how an unsnapped price reaches a venue at all.

## The one price that is passed through

The stop's own limit price, at first placement: it is handed back as given and snapped by nothing.

On a change, all three prices are snapped, that one included. So the same figure can reach the venue raw the first time and floored the second.

## Related

- [Protection](protection.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
