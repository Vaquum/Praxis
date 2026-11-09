---
row: P16-01
baseline: 49aa659
created: 2026-11-08 14:40 UTC
modified: 2026-11-08 15:12 UTC
evidence:
  - claim: "Where no mark is held, a page is asked for by whatever starting moment the asking was given, and no latest moment is ever sent with it"
    source: "`mytrades_backfill.py` 88-90, leaving `binance_adapter.py` 1911-1912 unreached, the starting moment sent only where there is one at 1908-1909"
  - claim: "The choice between asking by mark and asking by time is made afresh for each page"
    source: "`mytrades_backfill.py` 82-83"
  - claim: "Only a full page of readable names advances the mark, and a page that does leaves no road back to the moment"
    source: "`mytrades_backfill.py` 112 into 83, the three roads that return first at 92-93, or 97-98, or 105-110"
  - claim: "A mark and a time can never be sent together, the venue's reader refusing the pair"
    source: "`binance_adapter.py` 1896-1898"
---
# The window a backfill opens

A [backfill](backfilling-missed-trades.md) holding no mark asks the venue for trades from whatever starting moment it was given, and that moment is all it names.

## No far edge

The venue's reader can be given a latest moment as well. This road never gives it one, so the window has no far edge: what the venue is asked for runs from that moment onwards, and the asking ends where [the pages run out](backfilling-missed-trades.md) rather than at a moment.

A day back therefore asks for everything since a day ago, not for a day's worth of trades. The starting moment is sent only where the asking was given one; with neither a mark nor a moment, the venue is asked for a page with neither.

## One road, then the other

Each page's asking chooses between the mark and the moment, and the choice is made again for every page.

The moment is reachable only while no mark is held. A mark is set only by a full page whose trades carry readable names — the three answers that end the asking return before setting one — and once a page has set it, every page after is asked by mark and the moment is never looked at again.

The two can never be sent together: the venue's reader refuses that pair outright, which is why the asking is a choice between them.

## Related

- [Backfilling missed trades](backfilling-missed-trades.md)
- [The venue feed](the-venue-feed.md)
