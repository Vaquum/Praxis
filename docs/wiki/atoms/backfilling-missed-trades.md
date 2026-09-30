---
row: P3-17
baseline: 49aa659
created: 2026-09-30 08:12 UTC
modified: 2026-09-30 09:02 UTC
evidence:
  - claim: "A mark of how far a previous asking got is read back per account and pair"
    source: "`praxis/trading.py` 1534, kept by account and pair at `event_spine.py` 1311-1314"
  - claim: "With no mark, the asking starts a day back instead"
    source: "`praxis/trading.py` 1535-1537 with the span at 59"
  - claim: "The mark is passed into the first asking unchanged"
    source: "`praxis/trading.py` 1538-1544 into `mytrades_backfill.py` 84-86"
  - claim: "That first asking includes the trade the mark points at"
    source: "`binance_adapter.py` 1905-1906, sent as given"
  - claim: "A repeat is refused only where the epoch, account, pair and venue name all match"
    source: "`event_spine.py` 1018-1023"
  - claim: "An empty answer ends the asking as complete"
    source: "`mytrades_backfill.py` 92-93"
  - claim: "A short answer ends it as complete"
    source: "`mytrades_backfill.py` 97-98"
  - claim: "The names are looked at only past that point"
    source: "`mytrades_backfill.py` 100-110"
  - claim: "Otherwise the next asking starts past the highest seen"
    source: "`mytrades_backfill.py` 112"
  - claim: "A full page whose trades carry no readable name ends it as incomplete"
    source: "`mytrades_backfill.py` 105-110"
  - claim: "Running out of pages ends it as incomplete, whether or not trades remain"
    source: "`mytrades_backfill.py` 119"
  - claim: "The mark is written only where the asking finished complete and a readable name was seen"
    source: "`praxis/trading.py` 1576-1578"
---
# Backfilling missed trades

Praxis asks the venue for trades it did not hear about — **backfilling** them — after [the feed](the-venue-feed.md) was away, or at a start, when something happened while nobody was listening.

The venue answers a page at a time, so the asking repeats: each answer says where the next should begin.

## Where it starts

A mark of how far a previous asking got is kept per account and pair, and read back to start from. With no mark, the asking starts a day back instead.

The mark is passed in unchanged, and the venue's answer **includes** the trade it points at. So the first page repeats one trade on purpose. [The record](where-duplicates-stop.md) refuses that repeat where the epoch, account, pair and venue name all match what it already holds.

## Where it stops

An answer with nothing in it ends the asking as complete, and so does a short one — a short page means the venue had no more to give. That test comes before the names are looked at, so a short page of unreadable trades still counts as done.

Otherwise the next asking starts past the highest trade seen.

## Where it stops short

A full page whose trades carry no readable name ends the asking incomplete. So does running out of pages, whether or not the venue had more.

The mark is written only where the asking finished complete and saw a readable name. An incomplete one leaves the previous mark standing, and where there was none, leaves none — so a later asking starts a day back and may miss what fell outside that.

Marks are per pair, so one pair can save its mark while another leaves the account's attempt incomplete.

## Related

- [The venue feed](the-venue-feed.md)
- [Where duplicates stop](where-duplicates-stop.md)
