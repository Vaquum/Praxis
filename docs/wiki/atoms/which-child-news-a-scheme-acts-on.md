---
row: P148-01
baseline: 49aa659
created: 2026-11-15 18:30 UTC
modified: 2026-11-15 18:30 UTC
evidence:
  - claim: "News that is not a fill, a cancellation, an expiry or a rejection is dropped at once"
    source: "`execution_manager.py` 6399 into 6400"
  - claim: "News naming an order the account does not hold is dropped, and so is news whose order belongs to no running scheme"
    source: "`execution_manager.py` 6402, then 6403 into 6404, or 6406, then 6407 into 6408"
  - claim: "An order now in a terminal state is taken off the scheme's live children"
    source: "`execution_manager.py` 6410 into 6411"
  - claim: "A scheme mid-amend then stops there, its children left for the amend to settle"
    source: "`execution_manager.py` 6413 into 6414"
  - claim: "A child that ended in anything but a full fill, where the scheme is open, is treated as a failed slice and the pass ends"
    source: "`execution_manager.py` 6416-6419 into 6420-6426, then 6427"
  - claim: "Everything that reaches the end asks whether the scheme can now be finished"
    source: "`execution_manager.py` 6429"
---
# Which child news a scheme acts on

A fed-out order learns what became of its children from the venue's news, and three kinds of news are dropped before any of it is acted on.

## The three it drops

News that is none of a fill, [a cancellation](how-a-trade-is-cancelled.md), an expiry or a rejection. News naming an order the account does not hold. And news whose order belongs to no running scheme.

So news for a scheme already finished is dropped by the third test, since finishing takes the scheme out of the running ones.

## What a terminal child costs

It is taken off the scheme's live children first, before anything is decided.

A scheme mid-amend then stops there — its children are the amend's business, and the amend settles them. So a child ending during an amend is forgotten as a live child and nothing else is done about it here.

## The failed slice

A child that ended in anything but a full fill, where the scheme is open, is treated as a failed slice and the pass ends. A scheme already held for some other reason takes a different road, which leaves its existing hold in place.

## What everything else reaches

The question of whether the scheme can now be finished. A child that filled whole reaches it, and so does news that changed nothing terminal at all.

## Related

- [How waiting work is drained](how-waiting-work-is-drained.md)
- [What a resumed scheme comes back holding](what-a-resumed-scheme-comes-back-holding.md)
- [A change waiting out a hold](a-change-waiting-out-a-hold.md)
