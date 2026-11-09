---
row: P171-01
baseline: 49aa659
created: 2026-11-09 13:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "Each waiting event is taken together with the answer its caller is waiting on, and a count of those in flight raised"
    source: "`execution_manager.py` 3804, then 3805, then 3806"
  - claim: "That count is lowered whatever happens"
    source: "`execution_manager.py` 3834, then 3835"
  - claim: "The event is recorded and applied, and a place given has it queued for reacting to"
    source: "`execution_manager.py` 3808, then 3809, then 3813 into 3814"
  - claim: "The caller is told the place, which is nothing at all where the record took the event as one it already holds"
    source: "`execution_manager.py` 3816 into 3817"
  - claim: "A caller who has stopped waiting is told nothing, on every road"
    source: "`execution_manager.py` 3816, or 3820, or 3831"
  - claim: "A writer that will never run again has every still-waiting caller handed an error instead"
    source: "`execution_manager.py` 3704, then 3705, then 3706 into 3707, reached from 3645-3651"
  - claim: "The writer being stopped mid-drain tells the caller the writer stopped, and lets the stop travel"
    source: "`execution_manager.py` 3819, then 3821-3826, then 3828"
  - claim: "Any other failure is told to the caller and the drain goes on to the next event"
    source: "`execution_manager.py` 3830, then 3832, then 3804"
---
# What a caller waiting on an admitted event is told

A caller handing an event to an account waits for the place the record gives it, and the account's own task is what answers.

## The answer

The event is recorded and applied. A place given has the event queued for reacting to, and the caller is told that place.

The place can be nothing at all, where the record took the event as one it already holds. So nothing means admitted before rather than not admitted.

## The failures

The writer being stopped mid-drain tells the caller the writer stopped, and lets the stop travel — so the caller hears a stopped writer even where the recording already took, and the event stands in the record for a restart to find.

Any other failure is told to the caller as it stands, and the drain goes on to the next event.

## What is true on every road

A caller who has stopped waiting is told nothing, and the count of events in flight is lowered whatever happens — including the road where the stop travels.

## Related

- [What admitting an event refuses](what-admitting-an-event-refuses.md)
- [What a failure reacting to an event costs](what-a-failure-reacting-to-an-event-costs.md)
- [Which thread the manager will take work from](which-thread-the-manager-will-take-work-from.md)
