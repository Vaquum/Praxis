---
row: P101-02
baseline: 49aa659
created: 2026-11-09 07:57 UTC
modified: 2026-11-09 07:57 UTC
evidence:
  - claim: "Every event built from a report carries the report's own moment"
    source: "`praxis/trading.py` 1777, used at 1789, or 1807, or 1816, or 1825"
  - claim: "A trade becomes a fill, but only where the manager can name the trade the command belongs to"
    source: "`praxis/trading.py` 1779 into 1780, then 1781, the fill built at 1787"
  - claim: "A cancelling becomes its own event carrying a fixed reason"
    source: "`praxis/trading.py` 1804 into 1805-1811"
  - claim: "A refusal becomes its own event carrying the venue's reason, or a fixed one where the venue gave none"
    source: "`praxis/trading.py` 1813 into 1814-1819"
  - claim: "An expiry becomes its own event carrying no reason at all"
    source: "`praxis/trading.py` 1822 into 1823-1828"
  - claim: "Any other kind of report becomes nothing"
    source: "`praxis/trading.py` 1830"
---
# What a report becomes

A report that survived the discarding becomes one of four events, or nothing.

## What they share

Every event built from a report carries the report's own moment, read once before the kinds are weighed. So the moment is the venue's, not this side's clock.

## The trade

A trade becomes a fill — but only where the manager can name the trade the command belongs to. Where it cannot, the report is dropped with a warning instead, so a fill arriving for a command this side has forgotten produces no event at all.

That makes the fill the one conversion that can fail. The other three cannot.

## The three that always convert

A cancelling becomes its own event carrying a fixed reason. A refusal becomes its own event carrying the venue's reason, or a fixed one where the venue gave none. An expiry becomes its own event carrying no reason at all.

So two of the three invent a reason where the venue said nothing, and the third says nothing in that case either — an expiry has no reason field to fill.

## Everything else

Any other kind of report becomes nothing. The kinds not named here are not errors and leave no trace; the report is read, found to be none of the four, and let go.

## Related

- [The five reasons a report is discarded](the-five-reasons-a-report-is-discarded.md)
