---
row: N41-02
baseline: 49aa659
created: 2026-11-08 16:59 UTC
modified: 2026-11-08 16:59 UTC
evidence:
  - claim: "A worker still alive when the wait runs out keeps its place, the stopping returning without clearing it"
    source: "`nexus/core/outcome_loop.py` 179-185"
  - claim: "A start asks whether the place holds a worker that is still alive, and returns only then"
    source: "`nexus/core/outcome_loop.py` 146-147"
  - claim: "So the block lasts exactly as long as that worker runs: once it finishes, a start puts a new worker in its place"
    source: "`nexus/core/outcome_loop.py` 146 failing, then 149-155"
  - claim: "A worker that exited within the wait has its place cleared, and only where the place still holds that same worker"
    source: "`nexus/core/outcome_loop.py` 187-189"
  - claim: "Every stop sets one shared signal, so a stop entering after a restart signals the new worker"
    source: "`nexus/core/outcome_loop.py` 170 and 175, the signal made once at 131"
---
# The stop that blocks a restart

Where the wait for the outcome loop's worker runs out with the worker still alive, [the stopping](starting-and-stopping-the-outcome-loop.md) leaves that worker in its place and returns.

## How long the block lasts

A start asks whether the place holds a worker that is still alive, and returns only then.

So the block lasts exactly as long as that worker runs. While it runs, a start does nothing — which is the point, since a second worker would read the same outcomes beside the first. Once it finishes, a start puts a new worker in its place, with no stop needed in between.

## The clearing, and the question it asks

A worker that did exit within the wait has its place cleared, under the lock, and only where the place still holds that same worker.

That question stops a late stop from clearing a worker it never waited for: where a start has already put a new one in the place, the old stop leaves it there.

## The signal they share

The clearing is careful; the signalling is not. There is one stop signal, made as the loop is, and every stop sets it.

So a stop entering after a restart tells the new worker to exit — the signal it sets is the one that worker reads. A start clears the signal before setting a worker going, so the order these three happen in decides whether the new worker survives.

## Related

- [Starting and stopping the outcome loop](starting-and-stopping-the-outcome-loop.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
- [An outcome waiting on a strategy](an-outcome-waiting-on-a-strategy.md)
