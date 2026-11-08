---
row: P16-01
baseline: 49aa659
created: 2026-11-10 16:00 UTC
modified: 2026-11-10 16:00 UTC
evidence:
  - claim: "Where no mark is held, a page is asked for by time, and no latest time is ever sent with it"
    source: "`mytrades_backfill.py` 88-90, leaving `binance_adapter.py` 1911-1912 unreached"
  - claim: "The choice between asking by mark and asking by time is made afresh for each page"
    source: "`mytrades_backfill.py` 82-83"
  - claim: "A page that advances the mark leaves no road back to the time"
    source: "`mytrades_backfill.py` 112 into 83"
  - claim: "A mark and a time can never be sent together, the venue's reader refusing the pair"
    source: "`binance_adapter.py` 1896-1898"
---
# The window a backfill opens

A [backfill](backfilling-missed-trades.md) holding no mark asks the venue for trades from one moment onwards, and that moment is all it names.

## No far edge

The venue's reader can be given a latest moment as well. This road never gives it one, so the window is open at the far end: the asking covers that moment through to the newest trade the venue holds, however long ago the moment was.

A day back therefore means everything since a day ago — not a day's worth of trades.

## One road, then the other

Each page's asking chooses between the mark and the moment, and the choice is made again for every page.

The moment is reachable only while no mark is held. The first page's answer sets a mark, so every page after it is asked by mark, and the moment is never looked at again.

The two can never be sent together: the venue's reader refuses that pair outright, which is why the asking is a choice between them.

## Related

- [Backfilling missed trades](backfilling-missed-trades.md)
- [The venue feed](the-venue-feed.md)
