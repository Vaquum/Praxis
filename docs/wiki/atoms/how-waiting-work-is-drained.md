---
row: P1-03
baseline: 49aa659
created: 2026-09-20 16:30 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "One worker per account; a second registration is refused"
    source: "`execution_manager.py` 816-818, otherwise started and kept at 832-836"
  - claim: "The worker goes round until stopped"
    source: "`execution_manager.py` 3901-3907"
  - claim: "Venue news is drained before the priority line"
    source: "called at `execution_manager.py` 3907, body at 3734-3737"
  - claim: "After a failure the ordinary queue is emptied and each item refused"
    source: "`execution_manager.py` 3962-3967, body at 6988-6999"
  - claim: "An item whose refusal cannot be built is dropped unreported"
    source: "`execution_manager.py` 7003-7019"
  - claim: "A cancelled worker stops the emptying and leaves the rest queued"
    source: "`execution_manager.py` 7000-7002"
  - claim: "Held or failed takes no new submitted work"
    source: "`execution_manager.py` 3969-3971"
  - claim: "The cancellation retry runs before that leaving point"
    source: "`execution_manager.py` 3960"
  - claim: "At most one item is taken for execution per pass, though a failure empties the queue separately"
    source: "`execution_manager.py` 3980-3984, the failure path instead emptying it at 6988-6999"
  - claim: "Fed-out work past its deadline is ended instead of started"
    source: "`execution_manager.py` 3995-3996 rather than the start at 3998"
  - claim: "A ladder past its deadline is ended instead of started"
    source: "`execution_manager.py` 4004-4005 rather than the start at 4007"
---
# The account worker

Each account has one **worker**, going round the same circuit until it is stopped. Work waits in a queue for it to come round. One turn of that circuit is a **pass**.

## What a pass takes

A pass takes from the queues in this order: news from the venue, then [the priority line](the-priority-line.md), then at most one piece of [submitted work](how-an-order-is-placed.md).

Between the priority line and that last step it carries on with [work already under way](work-already-under-way.md).

## The ordinary queue

Submitted work gives up at most one item per pass, and many passes take none.

## What holds a pass back

While the account is still starting up, the pass does nothing else.

On hold or failed, the pass drains venue news, empties the priority line, retries a due [cancellation](how-a-trade-is-cancelled.md) and, if failed, empties its ordinary queue refusing each item. Then it leaves. The changes put back on the line are left alone.

An item whose refusal cannot be built is dropped with nothing reported. If the worker is cancelled partway through that emptying, it stops there and whatever is still queued stays queued.

## What taking one item does

The item is sent on according to how it was meant to be executed. Work meant to be fed out over time, and work meant to be laddered, is ended rather than started if its deadline has already passed.
