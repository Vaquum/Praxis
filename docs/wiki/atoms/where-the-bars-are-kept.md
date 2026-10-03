---
row: P4-15
baseline: 49aa659
created: 2026-10-03 20:23 UTC
modified: 2026-10-03 20:37 UTC
evidence:
  - claim: "The reader opens one file per series, under a shared root"
    source: "`arrow_price_store.py` 92, the name at 28, the root kept at 59"
  - claim: "It sorts the closed bars and takes the last one's closing price"
    source: "`arrow_price_store.py` 119, 127 and 142-144"
  - claim: "Which bars count as closed turns on whether the frame carries an opening-stamp column"
    source: "`arrow_price_store.py` 115, the column named at 31"
  - claim: "Without that column, a bar counts as closed where its stamp plus the gap is at or before now"
    source: "`arrow_price_store.py` 114-116 and 119"
  - claim: "With it, where its stamp alone is at or before now"
    source: "`arrow_price_store.py` 114-116 and 119"
  - claim: "The reader keeps no frame and no price, so each call opens the file again"
    source: "`arrow_price_store.py` 59-61 against 92-144"
---
# Where the bars are kept

The bars a strategy is priced against live on disk, one file per series under a shared root. The reader opens the series file, sorts the bars that have closed, and takes the last one's closing price — [or gives nothing back](when-no-price-comes-back.md).

## When a bar has closed

That turns on whether the frame carries an opening-stamp column.

Without it, a bar counts as closed where its stamp plus the gap between bars is at or before now — the stamp being the opening. With it, the stamp is already the close, so the test is the stamp alone against now.

The bar still forming falls outside either test.

## Nothing is kept

The reader holds its root, its clock and its staleness bound, and no frame and no price. Each call opens the file again.

## Related

- [When no price comes back](when-no-price-comes-back.md)
- [The venue feed](the-venue-feed.md)
- [The mark sampler](the-mark-sampler.md)
