---
row: P11-03
baseline: 49aa659
created: 2026-11-10 07:30 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "Stopping a poller sets the signal, cancels the task, and waits for it while swallowing the interruption that raises"
    source: "`praxis/infrastructure/book_poller.py` 63 into 65-69"
  - claim: "The task is then forgotten"
    source: "`praxis/infrastructure/book_poller.py` 71"
  - claim: "The host stops its pollers one after another, each waited for"
    source: "`praxis/launcher.py` 3848-3850"
  - claim: "The whole walk is bounded at ten seconds"
    source: "`praxis/launcher.py` 3854, then 3855"
  - claim: "A walk that fails or runs out of time keeps the pollers recorded for another attempt"
    source: "`praxis/launcher.py` 3856-3857, which leaves 3860 unreached"
  - claim: "A walk that finishes forgets them"
    source: "`praxis/launcher.py` 3860, reached rather than 3857"
---
# The stop that waits for its pollers

Stopping a book poller waits for the turn in hand, and the host stopping all of them waits for each in turn under one limit.

## What one stop does

It sets the signal, cancels the task, and waits for that task to end — swallowing the interruption the wait raises, so a stop does not fail because it did the interrupting itself.

The task is then forgotten, which is what lets the poller be started again.

## What the host does

It walks its pollers and waits for each. The walk runs on the loop from another thread, and the whole of it is bounded at ten seconds — not ten seconds each.

So a host with many pollers shares one limit between them, and a poller late in the walk has whatever time the ones before it left.

## What a failed walk keeps

A walk that fails, or that runs out of its ten seconds, keeps the pollers recorded. Only a walk that finishes forgets them.

So a host whose shutdown could not stop its pollers still knows which ones they were, and a later attempt has something to work from. [The other loops the host stops](what-a-loops-stop-leaves-running.md) wait for nothing and so have nothing to keep.

## Related

- [What a book poller refuses and answers](what-a-book-poller-refuses-and-answers.md)
- [The gap between polls](the-gap-between-polls.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
