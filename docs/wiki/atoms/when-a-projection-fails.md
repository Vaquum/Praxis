---
row: P2-34
baseline: 49aa659
created: 2026-09-26 07:02 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "The call handing an event to the order-and-holdings projection carries no guard"
    source: "`execution_manager.py` 2081"
  - claim: "The money projection is guarded where it is called"
    source: "`execution_manager.py` 2092-2098"
  - claim: "Events admitted from outside and events off the venue's feed stop the account"
    source: "either `execution_manager.py` 3249-3261 or 3768-3780"
  - claim: "A stopped account turns away the commands waiting in its queue"
    source: "`execution_manager.py` 3958-3963"
  - claim: "It carries out an abort all the same, and puts an amend back to wait"
    source: "`execution_manager.py` 3912-3919, put back at 3952-3953"
  - claim: "A priority instruction that fails ends there"
    source: "`execution_manager.py` 3937-3950"
  - claim: "A command taken off the queue that fails ends there"
    source: "`execution_manager.py` 3993-4019"
  - claim: "A scheme that fails while being advanced is dropped, the recording of it being best-effort"
    source: "`execution_manager.py` 5874-5884, called at 5838"
  - claim: "Putting up protection for a bracket rebuilt after a restart has no guard of its own"
    source: "`execution_manager.py` 4738-4761, called at 3974"
  - claim: "What escapes every guard stops the account"
    source: "`execution_manager.py` 4025-4026"
---
# When a projection fails

The call that hands an event to [the order-and-holdings projection](what-a-fill-changes.md) carries no guard, so a failure there travels back out to whatever asked for it. The money projection is guarded where it is called, and a failure in that one goes no further.

What becomes of the first kind turns on where it was asked for.

## From outside the loop

An event admitted from outside, and an event arriving on the venue's feed, both stop the [account](what-an-account-is.md).

A stopped account is not an idle one. The commands waiting in its queue are turned away, but an abort handed to it is still carried out, so a position can still be closed; an amend is put back to wait until the account is usable again, which takes a restart.

## From inside the loop

Most of what the loop does carries a guard, and each ends something different.

A priority instruction that fails ends there. A command taken off the queue that fails ends there. A scheme that fails while being advanced is dropped altogether — Praxis tries to record it as failed on the way, but drops it whether that recording works or not.

All three leave the account running.

## What carries no guard

Putting up protection for a bracket rebuilt after a restart. A failure there, and any other escaping every guard the loop sets, reaches the loop's own and stops the account.

## Related

- [What a fill changes](what-a-fill-changes.md)
- [What an account is](what-an-account-is.md)
