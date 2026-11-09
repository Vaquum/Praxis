---
row: N52-01
baseline: 49aa659
created: 2026-11-12 09:30 UTC
modified: 2026-11-13 13:30 UTC
evidence:
  - claim: "Where a positions lock is given, it must be the very lock the risk record holds"
    source: "`nexus/core/mtm_loop.py` 87-90 into 91-92 and 107"
  - claim: "A risk record carrying no lock at all fails that same check"
    source: "`nexus/core/mtm_loop.py` 88, which asks whether the record has one"
  - claim: "A loop given no lock is built without the check being made"
    source: "`nexus/core/mtm_loop.py` 87, whose test begins with the lock being there"
  - claim: "Its interval is refused unless it is a whole or ordinary number, with a true-or-false refused outright, and refused at or below nought by comparison"
    source: "`nexus/core/mtm_loop.py` 79-85"
  - claim: "What is kept is that interval as a plain number"
    source: "`nexus/core/mtm_loop.py` 111"
---
# The lock the marking insists on

The loop marking positions to the market refuses to be built where the lock it is given is not the same object as the lock [the risk record](what-the-risk-records-refuse.md) holds.

## Why identity rather than possession

The loop writes to the risk record — each strategy's unrealized figure, and the account's. A lock that merely exists would let the loop and the record's own readers hold different locks and write at once.

So the check is identity: the object handed in must be the object the record carries. A record carrying none at all fails it too.

## The case it does not check

A loop given no lock. The check begins with the lock being there, so a loop built without one is built without the question being asked — and then nothing stands between its writes and anyone else's.

## The interval

A whole or ordinary number, with a true-or-false refused outright by a test of its own, and compared with nought. Finiteness is not asked, so a figure that is no number by value passes the comparison and is kept — the same gap [the health loop](the-health-loops-interval-and-mark.md) and [the checkpoint timer](the-interval-a-checkpoint-timer-takes.md) leave.

What is kept is the figure as a plain number.

## Related

- [What the risk records refuse](what-the-risk-records-refuse.md)
- [The mark that ends a turn](the-mark-that-ends-a-turn.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
