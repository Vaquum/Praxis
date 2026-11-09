---
row: P141-02
baseline: 49aa659
created: 2026-11-15 15:00 UTC
modified: 2026-11-15 15:00 UTC
evidence:
  - claim: "The account is taken out of the manager's own mapping first, by a removal that answers with what it removed"
    source: "`execution_manager.py` 2952"
  - claim: "Finding nothing there refuses the whole call"
    source: "`execution_manager.py` 2953 into 2954-2955"
  - claim: "The published amendable set for that account is dropped next"
    source: "`execution_manager.py` 2957"
  - claim: "Every admission still waiting is then failed, carrying the same words a fresh call would have been refused with"
    source: "`execution_manager.py` 2959-2964, against 2954-2955"
  - claim: "The worker's task is cancelled and waited for, with the interruption that raises swallowed"
    source: "`execution_manager.py` 2966, then 2967, then 2968 into 2969"
  - claim: "Because the removal comes first, an admission in progress finds a different account under that name and is refused"
    source: "`execution_manager.py` 2952, ahead of 2966-2969, read by 3242 into 3243-3247"
---
# What unregistering an account does in order

Unregistering an account takes it out of the manager's own mapping before it stops anything, and that order is what lets work already under way notice it has gone.

## The order

The account is removed from the mapping first, by a removal that answers with what it removed — so finding nothing there is what refuses the whole call.

The published amendable set for that account is dropped. Every admission still waiting is failed. Only then is the worker's task cancelled and waited for, with the interruption that raises swallowed.

## Why the removal comes first

An admission part-way through its work [looks again at what the manager holds](the-two-checks-around-an-append.md) under that account's name, and compares it by identity. The removal is what makes that comparison fail.

So the account is unreachable from the moment of the removal, while its worker is still running and will keep running until the cancel lands.

## The refusal that is said twice

Every admission still waiting is failed carrying the same words a fresh call would have been refused with. A caller cannot tell from the words whether it arrived before the account went or was already waiting when it did.

## Related

- [The two checks around an append](the-two-checks-around-an-append.md)
- [What admitting an event refuses](what-admitting-an-event-refuses.md)
- [The last record a stopping host writes](the-last-record-a-stopping-host-writes.md)
