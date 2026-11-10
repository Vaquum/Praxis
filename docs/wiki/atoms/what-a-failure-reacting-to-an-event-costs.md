---
row: P168-01
baseline: 49aa659
created: 2026-11-09 13:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "The drain takes an event at a time for as long as any remain"
    source: "`execution_manager.py` 3848, then 3849, then 3852"
  - claim: "An account marked poisoned has every remaining event taken off and dropped without being reacted to"
    source: "`execution_manager.py` 3850 into 3851"
  - claim: "Each event drives three reactions inside one guard: the report, the owning scheme's advance, and the owning bracket's drive"
    source: "`execution_manager.py` 3862, then 3863, then 3864, then 3865"
  - claim: "The task being stopped is let through rather than swallowed"
    source: "`execution_manager.py` 3866, then 3867"
  - claim: "Every other failure is swallowed, and the drain goes on to the next event"
    source: "`execution_manager.py` 3868, then 3848"
---
# What a failure reacting to an event costs

An event admitted for an account is reacted to on the account's own task, and the three reactions it drives stand inside one guard.

## The drain

An event is taken at a time for as long as any remain. An account marked poisoned has every remaining event taken off and dropped without being reacted to — the queue empties either way, and only the reacting is skipped.

## The three reactions

The report Nexus hears, the owning scheme's advance, and the owning bracket's drive, in that order and inside one guard.

The task being stopped is let through rather than swallowed. Every other failure is swallowed, and the drain goes on to the next event.

## What the shared guard means

A failure in the first reaction leaves the second and third undone for that event. So a report that cannot be sent takes the scheme's advance and the bracket's drive down with it, for that one event — and the next event is reacted to in full, including the advance the one before it missed.

Nothing retries the reactions for the event that failed. What they would have done is reached, if at all, by whatever the next event drives.

## Related

- [Which record an event is booked into](which-record-an-event-is-booked-into.md)
- [What admitting an event refuses](what-admitting-an-event-refuses.md)
- [Which thread the manager will take work from](which-thread-the-manager-will-take-work-from.md)
