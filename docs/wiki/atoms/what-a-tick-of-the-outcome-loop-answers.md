---
row: N77-02
baseline: 49aa659
created: 2026-11-09 00:32 UTC
modified: 2026-11-09 00:32 UTC
evidence:
  - claim: "Waiting outcomes are serviced before any new one is taken"
    source: "`nexus/core/outcome_loop.py` 209, ahead of 211"
  - claim: "A tick that found nothing waiting answers that nothing was taken"
    source: "`nexus/core/outcome_loop.py` 213-214"
  - claim: "A tick that took one answers that it did, whether the outcome dispatched or was parked"
    source: "`nexus/core/outcome_loop.py` 233, after 230-231"
  - claim: "A tick that only put the outcome behind a parked sibling answers the same way, having tried nothing"
    source: "`nexus/core/outcome_loop.py` 228, reached from 218-219"
  - claim: "A dispatch answers that it happened wherever the strategy resolved, the failure of the submitting falling through to the same answer"
    source: "`nexus/core/outcome_loop.py` 444, reached from 436-438"
---
# What a tick of the outcome loop answers

A tick answers whether it took an outcome off the queue, and that answer says nothing about what became of it.

## The order

Outcomes already waiting on a strategy are serviced first, before a new one is taken. So a pass over the parked ones runs on every tick, including the ticks that find nothing new.

## The two answers

A tick that found nothing waiting answers that nothing was taken. A tick that took one answers that it did.

## What the answer does not say

Whether the outcome got anywhere. One dispatched inline, one that failed to resolve and was parked, and one [put straight behind a parked sibling](an-outcome-waiting-on-a-strategy.md) without being tried at all are answered alike.

So a caller counting the ticks that took something is counting arrivals, not deliveries.

## The dispatch's own answer

A dispatch answers that it happened wherever the strategy resolved. The failure of the submitting of a strategy's actions falls through to that same answer, so actions lost on the way out leave the dispatch indistinguishable from one that placed them.

The one answer that means otherwise is [the strategy not resolving at all](an-outcome-waiting-on-a-strategy.md), which is what parks the outcome.

## Related

- [An outcome waiting on a strategy](an-outcome-waiting-on-a-strategy.md)
- [What one pass over the parked outcomes does](what-one-pass-over-the-parked-outcomes-does.md)
- [Which fills come back with a result](which-fills-come-back-with-a-result.md)
