---
row: N41-01
baseline: 49aa659
created: 2026-11-11 22:30 UTC
modified: 2026-11-13 10:00 UTC
evidence:
  - claim: "Starting under the lock returns at once where a live worker is already held"
    source: "`nexus/core/outcome_loop.py` 145-147"
  - claim: "Otherwise it clears the stop signal and sets a worker going, named and running in the background"
    source: "`nexus/core/outcome_loop.py` 149-155"
  - claim: "Stopping takes the worker under the lock, sets the stop signal, and lets the lock go before waiting"
    source: "`nexus/core/outcome_loop.py` 169-175 into 177"
  - claim: "Stopping a loop holding no worker returns before the signal is set"
    source: "`nexus/core/outcome_loop.py` 172-173"
  - claim: "Whether the loop is running is answered under that same lock, and only a worker that both exists and is alive counts as running"
    source: "`nexus/core/outcome_loop.py` 139-140, the lock made at 132"
  - claim: "The one caller that stops it names no span, so the wait takes the loop's own"
    source: "`nexus/startup/shutdown_sequencer.py` 270 into `nexus/core/outcome_loop.py` 177"
---
# Starting and stopping the outcome loop

The loop reading outcomes back from Praxis runs on a worker of its own, and both starting and stopping it go through one lock.

## Starting

A loop already holding a live worker returns at once. Otherwise the stop signal is cleared and a worker is set going, named for the loop and running in the background.

## Stopping

The worker is taken under the lock and the stop signal set there. The lock is let go before the waiting begins, so a start or a second stop can run while this one waits.

A loop holding no worker returns before the signal is even set — so stopping something never started leaves the signal clear, and a later start has nothing to clear.

## Whether it is running

Answered under that same lock, and only a worker that both exists and is still alive counts. So a loop whose worker died on its own reads as not running, with the worker still held.

## The wait

The span is the caller's to name. The one place that stops this loop — [a host being brought down](what-a-stopping-host-halts-first.md) — names none, so the wait takes the loop's own span.

What happens at the end of that span is the loop's own answer, and [it differs from every other loop on this side](the-stop-that-blocks-a-restart.md).

## Related

- [The stop that blocks a restart](the-stop-that-blocks-a-restart.md)
- [An outcome waiting on a strategy](an-outcome-waiting-on-a-strategy.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
