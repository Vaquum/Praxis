---
row: N79-03
baseline: 49aa659
created: 2026-11-09 03:10 UTC
modified: 2026-11-09 03:10 UTC
evidence:
  - claim: "Whether the loop is running is read without the lock that every write of it takes"
    source: "`nexus/core/mtm_loop.py` 121, against 126, or 136, or 162"
  - claim: "One pass can be asked for outright, and marks without consulting the flag at all"
    source: "`nexus/core/mtm_loop.py` 151"
  - claim: "The whole of a pass stands inside a guard whose catch names any exception"
    source: "`nexus/core/mtm_loop.py` 217, the catch at 310"
  - claim: "A pass that raises is reported, and the tick that follows is scheduled all the same"
    source: "`nexus/core/mtm_loop.py` 310, the scheduling standing after at 168-169"
---
# What the mark loop leaves unguarded

Three things about the loop that values open positions are deliberately loose: the flag's reading, the way a pass can be asked for, and what a failed pass costs.

## The flag read without the lock

Whether the loop is running is read without the lock that every write of it takes. A reader can therefore see a flag mid-change, and the answer is a report of a moment rather than a promise about the next one.

## A pass asked for outright

One pass can be asked for outright, and marks without consulting the flag at all. So positions can be valued on a loop that was never started, and while a scheduled pass is running. What keeps two passes from treading on each other is [the hold the marking takes](the-lock-the-marking-insists-on.md), where the loop was given one to take — never the flag.

## A pass that raises

The whole of a pass stands inside a guard whose catch names any exception. A pass that raises is reported, and the tick that follows is scheduled all the same.

So one bad pass costs one valuation. The figures stay as the last good pass left them until the next one succeeds.

## Related

- [How the mark loop paces itself](how-the-mark-loop-paces-itself.md)
- [The lock the marking insists on](the-lock-the-marking-insists-on.md)
