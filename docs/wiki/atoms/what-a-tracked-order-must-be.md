---
row: N40-02
baseline: 49aa659
created: 2026-11-11 21:30 UTC
modified: 2026-11-11 21:30 UTC
evidence:
  - claim: "Its three names must each be text with something left once trimmed, the trimming only testing them"
    source: "`nexus/core/capital_controller/tracked_order.py` 59-61, or 63-65, or 67-69"
  - claim: "Its three figures must each be a finite figure of the exact kind at or above nought"
    source: "`nexus/core/capital_controller/tracked_order.py` 71-77, or 79-85, or 87-95"
  - claim: "What is left unfilled must not exceed the whole"
    source: "`nexus/core/capital_controller/tracked_order.py` 97-99"
  - claim: "Its state must be one of the two named"
    source: "`nexus/core/capital_controller/tracked_order.py` 101-103, the two at 28-29"
  - claim: "Its moment must be a moment carrying the universal-time marker itself"
    source: "`nexus/core/capital_controller/tracked_order.py` 105-107, or 109-110"
---
# What a tracked order must be

The record of an order holding an account's money is refused for any one of a fixed list of failings, checked as it is built.

## The three names

The order's own name, the name of the holding it consumed, and the name of the strategy that placed it. Each must be text with something left once the blank space is trimmed off.

The trimming only tests them. What the record carries is the name as it arrived, padding and all — [the same answer](the-key-this-record-will-not-trim-for-you.md) a command crossing the seam gives, rather than the refusal the capital record gives.

## The three figures

What the order locks, what is held back for its fees, and what of it is still unfilled. Each must be a finite figure of the exact kind at or above nought.

What is still unfilled must also not exceed what the order locks, so the record cannot say more is outstanding than was ever committed.

## The state and the moment

The state must be one of two: sent and unacknowledged, or acknowledged and resting. A finished order is not a state here — such an order leaves the tracking instead.

The moment must be a moment, and must carry the universal-time marker itself. A zone merely standing at that offset is refused, which is the stricter of [the two rules](the-moments-with-no-marker.md) these two sides apply to a moment.

## Related

- [The keys that must match what they hold](the-keys-that-must-match-what-they-hold.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [The moments with no marker](the-moments-with-no-marker.md)
