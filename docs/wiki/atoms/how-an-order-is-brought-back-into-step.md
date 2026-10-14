---
row: P4-55
baseline: 49aa659
created: 2026-10-14 10:40 UTC
modified: 2026-10-14 10:40 UTC
evidence:
  - claim: "An order the record already has as ended is passed over"
    source: "`trading.py` 861-862"
  - claim: "One the venue has never heard of is logged and passed over, leaving the record as it stands"
    source: "`trading.py` 870-875"
  - claim: "A venue figure above the record's has the difference taken in as fills"
    source: "`trading.py` 877-880"
  - claim: "An order still behind the venue after that is left unfinished rather than ended"
    source: "`trading.py` 882-883"
  - claim: "Only one the venue has ended, and the record has not, is ended"
    source: "`trading.py` 885-890"
  - claim: "A cancellation, an expiry and a refusal are each turned into their own record"
    source: "`trading.py` 1663, 1671 and 1678, written at 1687"
  - claim: "A venue status of filled makes none of those, leaving the fills to close the order"
    source: "`trading.py` 1663, 1671 and 1678 against 1687"
---
# How an order is brought back into step

Squaring an order means asking the venue what became of it and making the record agree. Praxis does this for every order it still holds as working, and the order it does things in decides what it is safe to conclude.

## Asked, unless it is already over

An order the record has as ended is passed over: there is nothing left to learn.

## What the venue does not have

An order the venue has never heard of is logged and passed over, and the record is left exactly as it stands. The order is not written off, because the venue not having it is as consistent with a send that never arrived as with one that did and was forgotten.

## Fills first, then the ending

Where the venue shows more filled than the record does, the difference is taken in as fills before anything else is decided.

An order still behind the venue's figure after that is deliberately left unfinished. Ending it with fills missing would report a smaller trade than happened, and the missing fills would be stranded under an order the record had closed.

Only an order the venue has ended, and the record has not, is ended — and [a cancellation](how-a-trade-is-cancelled.md), an expiry and a refusal are each turned into their own kind of record rather than one general ending.

A venue status of filled gets none of those three. The fills are what close such an order, so one the venue calls filled and whose fills do not add up to its amount stays open here, for [the ordinary path](fills-and-the-order.md) to close.

## Related

- [Backfilling missed trades](backfilling-missed-trades.md)
- [What startup does with orphaned work](what-startup-does-with-orphaned-work.md)
- [Where duplicates stop](where-duplicates-stop.md)

---

Created 2026-10-14 10:40 UTC · Last modified 2026-10-14 10:40 UTC
