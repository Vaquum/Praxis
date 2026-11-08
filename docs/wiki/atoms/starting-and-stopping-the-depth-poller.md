---
row: P51-02
baseline: 49aa659
created: 2026-11-12 08:30 UTC
modified: 2026-11-12 08:30 UTC
evidence:
  - claim: "Starting raises where the poller is already running"
    source: "`praxis/binsim/feed.py` 152-153"
  - claim: "Otherwise it clears the stop signal, opens a session and sets the poll loop going as a task of its own"
    source: "`praxis/binsim/feed.py` 155-157"
  - claim: "Stopping sets the stop signal, waits on the task swallowing the one error a cancelled task raises, forgets it, and then closes the session"
    source: "`praxis/binsim/feed.py` 163 into 165-169, and 171-173"
  - claim: "A failure of any other kind escapes the waiting, leaving the task held and the session open"
    source: "`praxis/binsim/feed.py` 166-167, which suppresses one kind, ahead of 169 and 171-173"
  - claim: "A poll made before a session exists raises"
    source: "`praxis/binsim/feed.py` 185-186"
  - claim: "An answer that is not the one success status raises"
    source: "`praxis/binsim/feed.py` 191-197 with the status at 38"
  - claim: "The body is read as JSON whatever kind the answer claims to be"
    source: "`praxis/binsim/feed.py` 205"
---
# Starting and stopping the depth poller

[The poller](what-the-depth-poller-is-built-with.md) opens its own session and runs its loop as a task, and the pair that starts and stops it is unlike the other loops on this side.

## Starting

A poller already running raises where it is started again — where [the timers](starting-and-stopping-the-timers.md) return quietly and [the sampler](starting-and-stopping-the-sampler.md) raises as this does.

Otherwise the stop signal is cleared, a session is opened, and the loop is set going as a task named for itself.

## Stopping

The stop signal is set. The task is waited on, with the error a cancelled task raises swallowed, and forgotten. Then the session is closed and forgotten too.

Nothing is cancelled here: the signal is what the loop reads, so stopping waits for the loop to come round to it rather than cutting it short.

The swallowing reaches that one error and nothing else. A task that failed another way has that failure come out of the stopping, with the task still held and the session still open — so a stop that raises leaves the poller holding both.

## The one poll

A poll made before a session exists raises, which is what a caller forcing a first snapshot before the loop starts must avoid.

An answer that is not the one success status raises. A body is read as JSON whatever kind the answer claims to be, so an upstream labelling its JSON as something else is still read — and what the body must contain is [checked afterwards](what-a-binsim-snapshot-is-turned-away-for.md).

## Related

- [What the depth poller is built with](what-the-depth-poller-is-built-with.md)
- [What a binsim snapshot is turned away for](what-a-binsim-snapshot-is-turned-away-for.md)
- [Starting and stopping the sampler](starting-and-stopping-the-sampler.md)
