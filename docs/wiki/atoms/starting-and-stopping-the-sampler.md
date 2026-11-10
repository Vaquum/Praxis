---
row: P24-02
baseline: 49aa659
created: 2026-11-08 15:54 UTC
modified: 2026-11-08 15:54 UTC
evidence:
  - claim: "Starting a sampler that holds a task still running raises"
    source: "`mark_sampler.py` 77-78, the test at 71"
  - claim: "Otherwise it clears the stop signal and sets the loop going as a task named for the account and the pair"
    source: "`mark_sampler.py` 80-83"
  - claim: "Stopping sets the stop signal, cancels the task and waits for it"
    source: "`mark_sampler.py` 94 into 96-100"
  - claim: "The waiting swallows the cancelling and nothing else, so another failure of the task comes back out of the stopping"
    source: "`mark_sampler.py` 99-100 suppressing one kind, ahead of 102"
  - claim: "The task is forgotten where the waiting returns"
    source: "`mark_sampler.py` 102"
  - claim: "A sampler holding no task is stopped without complaint"
    source: "`mark_sampler.py` 96, which finds none"
---
# Starting and stopping the sampler

[The sampler](the-mark-sampler.md) is started by setting its loop going as a task of its own, and stopped by signalling that loop and then cancelling the task.

## Starting

A sampler holding a task that has not finished raises where it is started again. That is the whole of what running means here.

Otherwise the stop signal is cleared and the loop begins, as a task named for the account and the pair.

## Stopping

The stop signal is set first, which is what the loop reads between samples. Then the task is cancelled and waited for.

The waiting swallows one thing: the cancelling itself. A task that ended some other way — [an interval the wait cannot use](what-the-mark-sampler-is-built-with.md), say — has its failure come back out of the stopping, and the task is still held afterwards.

Where the waiting returns, the task is forgotten. A sampler holding no task is stopped without complaint: the signal is set and there is nothing to cancel.

## What a sampler holds afterwards

A sampler that stopped cleanly holds no task, and can be started again.

One whose task failed some other way still holds it, and holds it finished — so starting it again is allowed, since starting asks only whether the task it holds is still running.

## Related

- [The mark sampler](the-mark-sampler.md)
- [What the mark sampler is built with](what-the-mark-sampler-is-built-with.md)
- [Starting and stopping the timers](starting-and-stopping-the-timers.md)
