---
row: P4-44
baseline: 49aa659
created: 2026-10-13 07:20 UTC
modified: 2026-11-10 09:56 UTC
evidence:
  - claim: "A long is closed by selling and a short by buying"
    source: "`execution_manager.py` 7607, then 7609-7611"
  - claim: "The venue's sizes must be at hand, and with them the name of the asset the cap is read in, either missing leaving the position open"
    source: "`execution_manager.py` 7613-7618 into 7625"
  - claim: "A leg the venue reports unfinished stops the flatten, and so does a query that fails"
    source: "`execution_manager.py` 7552, or 7561"
  - claim: "A list or leg the venue reports missing is read as cover already gone, so the flatten goes ahead"
    source: "`execution_manager.py` 7554 against 7561"
  - claim: "Nothing remaining, or nothing filled on the way in, makes it a no-op"
    source: "`execution_manager.py` 7638-7645"
  - claim: "A size under the smallest, or worth under the smallest value, is dropped, both weighed after the cap"
    source: "`execution_manager.py` 7681-7690 past the cap at 7668"
  - claim: "The order is recorded before it is sent, so a send that fails leaves a record the scan reads as an order of its own"
    source: "`execution_manager.py` 7779-7780 before 7783, failure written at 7802-7810, read at 6290-6293 from 7136-7137"
  - claim: "Only a restart drives that one again"
    source: "`execution_manager.py` 7996, reached from `trading.py` 600-602"
  - claim: "The scan tries again for a bracket still failed, with a remainder remembered and no flatten order placed"
    source: "`execution_manager.py` 7124-7141 driven from 7296, passed over at 7136-7137"
---
# When a flatten places nothing

A flatten is the order Praxis sends to close what is left of a position whose [protection was lost](when-protection-is-lost.md) — selling to close a long, buying to close a short. Sending it is an attempt: an unknown venue, a pair that may still rest, or too little left to close stop it before anything goes out.

## Stopped before it goes out

The venue's [sizes](the-sizes-a-venue-trades-in.md) must be at hand, and with them the asset the order is capped in; either missing leaves the position open.

Every list the cancelled pair might still rest under is asked after. A leg reported unfinished stops it, and so does a query that fails. A list or leg the venue reports missing is read as cover already gone, so the flatten goes ahead and any leg behind it goes unasked.

Nothing remaining, or nothing filled going in, makes it a no-op.

A size under the smallest the venue takes, or worth under its smallest value, is dropped — both weighed after the cap, either way round, so the cap is one way an order gets there.

Each stops the attempt rather than the remediation: the scan comes round again for a bracket still failed with a remainder remembered and no order of its own recorded. The order is recorded before it is sent, so a failed send leaves that record all the same, and only a restart drives it again.

## Smaller than the position

What is left is also [cut down](how-big-a-flatten-goes-out.md) to what the account can pay with — and a size cut far enough is a size that sends nothing. Nothing cuts a size to the largest the venue takes, so one still over it after that cutting is refused on the way out instead.

## Related

- [When protection is lost](when-protection-is-lost.md)
- [How big a flatten goes out](how-big-a-flatten-goes-out.md)
- [Protection](protection.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)

---

Created 2026-10-13 07:20 UTC · Last modified 2026-11-10 09:56 UTC
