---
row: N79-02
baseline: 49aa659
created: 2026-11-13 13:30 UTC
modified: 2026-11-13 13:30 UTC
evidence:
  - claim: "A position's figure is the mark less the entry price, times the size, signed by the side"
    source: "`nexus/core/mtm_loop.py` 284, then 285, then 286"
  - claim: "The sign is the only difference a side makes, a buy counting one way and everything else the other"
    source: "`nexus/core/mtm_loop.py` 285"
  - claim: "Each figure is kept against the trade's own name"
    source: "`nexus/core/mtm_loop.py` 287"
  - claim: "A strategy's figure is built up as the walk goes, each position's added to what stands for that strategy"
    source: "`nexus/core/mtm_loop.py` 283 into 288-289"
  - claim: "The whole is summed over the same walk, from nought"
    source: "`nexus/core/mtm_loop.py` 291, starting from 280"
  - claim: "All three are built before anything at all is written"
    source: "`nexus/core/mtm_loop.py` 280-282, ahead of 293"
  - claim: "The mark each figure is read from was gathered one symbol at a time as the prices came back"
    source: "`nexus/core/mtm_loop.py` 246, into the map made at 229"
  - claim: "A pass finding no positions answers where it stands, without reaching the working out"
    source: "`nexus/core/mtm_loop.py` 269, standing inside the branch opened at 256"
---
# What a mark works out for each position

A pass works out three things before it writes anything: a figure for each position, a figure for each strategy, and one for the whole.

## A position's figure

The mark less the entry price, times the size, signed by the side. A buy counts one way and everything else the other, and the sign is the only difference a side makes to the arithmetic.

The mark it is read from was gathered one symbol at a time, as [each price came back](the-mark-that-ends-a-turn.md).

## The three tallies

Each position's figure is kept against the trade's own name. A strategy's is built up as the walk goes, each position's added to whatever stands for that strategy already. The whole is summed over the same walk, from nought.

So one walk over the positions produces all three, and a position belonging to no strategy anyone asked about still reaches the whole.

## Before anything is written

All three are built before anything at all is written. [The writing is a second walk](which-of-a-hosts-changes-reach-the-log.md), so a pass that fails part-way through the arithmetic leaves every figure as it was.

## Where there is nothing to value

A pass finding no positions answers where it stands, without reaching the working out at all.

## Related

- [How the mark loop paces itself](how-the-mark-loop-paces-itself.md)
- [The mark that ends a turn](the-mark-that-ends-a-turn.md)
- [The lock the marking insists on](the-lock-the-marking-insists-on.md)
