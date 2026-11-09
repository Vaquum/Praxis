---
row: P122-02
baseline: 49aa659
created: 2026-11-15 05:30 UTC
modified: 2026-11-15 05:30 UTC
evidence:
  - claim: "A delivery record carries the command's name, its side, whether it was an entry, its sum, its fees, the strategy, the trade name, the size, and whether the whole remainder was meant"
    source: "`launcher.py` 3238-3250"
  - claim: "Rebuilding the order's record from it takes those same fields back, one for one"
    source: "`launcher.py` 1639-1649"
  - claim: "An outcome rebuilt from its own record carries the fill's average price worked out from the sum and the amount filled, or nothing where nothing filled"
    source: "`launcher.py` 1674 into 1675-1677"
  - claim: "Its slice counts are set to one rather than read from the record"
    source: "`launcher.py` 1688, then 1689"
  - claim: "Its slippage measures are carried from the record rather than worked out again"
    source: "`launcher.py` 1693, and 1694"
  - claim: "The record's own moment stands in for when the outcome was made"
    source: "`launcher.py` 1691"
  - claim: "The rest is taken from the record as it stands"
    source: "`launcher.py` 1680-1686, and 1690, and 1692"
---
# What a delivery record carries

A delivery record is what the host writes down about an order before it is sent, so that a restart can make sense of an outcome for it.

## The fields

The command's name, its side, whether it was an entry, its sum, its fees, the strategy it belongs to, the [trade name](what-a-trade-is.md), the size, and whether the whole remainder was meant.

Rebuilding the order's record from it takes those same fields back, one for one. Nothing is worked out and nothing is defaulted, so what a restart holds about an order is exactly what was written before the order went out.

## The outcome beside it

An outcome is rebuilt from a record of its own, and that rebuilding is not one for one.

The fill's average price is worked out from the sum and the amount filled, and is nothing at all where nothing filled. The slice counts are set to one rather than read. The record's own moment stands in for when the outcome was made. The rest is taken as it stands.

## The measures carried rather than reworked

The two slippage measures come off the record. They were worked out from a pre-send estimate and the command's reference price, and neither of those is on the record — so working them out again would give nothing where the first time gave a figure.

So a replayed outcome agrees with the original on what it measured, and differs from it on how many slices it took and on the moment it was made.

## Related

- [Which of the host's appends can stop the work](which-of-the-hosts-appends-can-stop-the-work.md)
- [The event spine](the-event-spine.md)
