---
row: P150-01
baseline: 49aa659
created: 2026-11-15 19:30 UTC
modified: 2026-11-15 19:30 UTC
evidence:
  - claim: "The parameters are insisted upon as a ladder's change before anything is weighed"
    source: "`execution_manager.py` 8877-8879, then 8880"
  - claim: "A ladder with an amend already in flight is refused, the phase it is in named in the report"
    source: "`execution_manager.py` 8882 into 8889"
  - claim: "A ladder held for any reason at all is refused as frozen or stopping"
    source: "`execution_manager.py` 8891 into 8897"
  - claim: "A command whose own parameters are not a ladder's is refused, though the change's were"
    source: "`execution_manager.py` 8899 into 8904"
  - claim: "The new prices and the new weights are each the change's where it gave one, and the command's own where it did not"
    source: "`execution_manager.py` 8906, then 8907-8910, then 8911-8914"
  - claim: "The pair is then built once purely to see whether it would be refused, and a refusal there ends the change"
    source: "`execution_manager.py` 8915-8918, then 8919 into 8926"
  - claim: "Past all four the generation is raised by one and the initiation recorded"
    source: "`execution_manager.py` 8928, then 8929, then 8931-8932"
---
# What a ladder's change is refused for

A change to a ladder's grid is refused four ways: three read the ladder's own state, and one is found by building the new grid and seeing whether it is allowed to exist.

## The three about the ladder

An amend already in flight — the phase it is in named in the report. A ladder held for any reason at all, refused as frozen or stopping. And a command whose own parameters are not a ladder's, though the change's were.

A command whose parameters are not a ladder's can only arise where a ladder's change was aimed at a command running something else, and [the routing](how-a-change-is-routed-to-its-handler.md) sends a change by its own shape rather than by the command's mode.

## The one found by building

The new prices and the new weights are each taken from the change where it gave one, and from the command's own where it did not. So a change naming only prices keeps the weights it had.

That pair is then built once, purely to see whether it would be refused — the object is discarded and only the refusal matters. A grid that cannot exist ends the change there.

## What follows

The generation is raised by one, and the initiation recorded. From there the amend is a machine with phases, which [a restart can pick up](what-a-ladder-amend-caught-mid-flight-resumes-as.md) where it stopped.

## Related

- [How a change is routed to its handler](how-a-change-is-routed-to-its-handler.md)
- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
- [What a ladder amend caught mid-flight resumes as](what-a-ladder-amend-caught-mid-flight-resumes-as.md)
