---
row: P180-01
baseline: 49aa659
created: 2026-11-09 13:09 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "A place in the queue is reserved before the acceptance is built"
    source: "`execution_manager.py` 3513, then 3514, then 3515-3520"
  - claim: "A full queue has the acceptance and any call-off against the command forgotten, and the command refused"
    source: "`execution_manager.py` 3550, then 3551, then 3555, then 3556, then 3557-3560, then 3561"
  - claim: "The reservation is given back whatever happens"
    source: "`execution_manager.py` 3562, then 3563"
  - claim: "Otherwise the command is installed and its trade remembered"
    source: "`execution_manager.py` 3565, then 3566"
  - claim: "The acceptance is applied to the trading record directly, not by the routing that poisons an account on failure"
    source: "`execution_manager.py` 3573, against 3769, then 3772, then 3773"
  - claim: "An account parked by a failed startup is refused before any of it"
    source: "`execution_manager.py` 3438, then 3439-3443"
---
# What a command's acceptance leaves behind if the queue is full

Taking a command in reserves a place in the account's queue, records the acceptance, and only then puts the command on that queue — so a queue found full has a durable acceptance to undo.

## The undoing

A full queue has the acceptance and any call-off standing against the command forgotten, and the command refused to the caller. The reservation is given back whatever happens, on this road and every other.

[The reservation](what-a-queue-reservation-is-for.md) is what makes the full queue unreachable in the first place: a place is held before the acceptance is built. The undoing exists for a reservation that failed to do its job.

## What follows a successful put

The command is installed and its trade remembered.

The acceptance is then applied to the trading record directly, rather than by the routing that [poisons an account](what-poisons-an-account.md) when an applying fails. A failure applying this one event fails this one command, and leaves the account able to take others.

## Before all of it

An account parked by a failed startup is refused, as is a poisoned one.

## Related

- [What a queue reservation is for](what-a-queue-reservation-is-for.md)
- [What poisons an account](what-poisons-an-account.md)
- [What a failure at startup does](what-a-failure-at-startup-does.md)
