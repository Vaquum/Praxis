---
row: P178-01
baseline: 49aa659
created: 2026-11-09 13:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "Applying a piece of outside news poisons the account where it fails, and the drain goes on"
    source: "`execution_manager.py` 3768, then 3769, then 3772, then 3773, then 3780"
  - claim: "An event applied without failing is then reacted to"
    source: "`execution_manager.py` 3769, then 3781"
  - claim: "Applying an event a recovery owner admitted poisons it the same way"
    source: "`execution_manager.py` 3249, then 3250, then 3253, then 3254"
  - claim: "The account's own loop dying poisons it"
    source: "`execution_manager.py` 4025, then 4026"
  - claim: "A failure ending a command left on a dead account's queue poisons it"
    source: "`execution_manager.py` 7003, then 7011"
  - claim: "The task being stopped travels on each of those roads rather than poisoning anything"
    source: "`execution_manager.py` 3770, then 3771, or 3251, then 3252, or 4022, then 4024, or 7002"
  - claim: "A poisoned account refuses to take an event, refuses to record and apply one, and refuses to take a command"
    source: "`execution_manager.py` 3183, and 3229, and 3235, and 3434"
  - claim: "It is no longer counted able to carry orders"
    source: "`execution_manager.py` 3348"
  - claim: "Nothing in the running system lifts it: the mark is only ever set, never cleared"
    source: "`execution_manager.py` 601, against 3773, and 3254, and 4026, and 7011"
  - claim: "A poisoned account has its waiting news taken off the queue and dropped unapplied"
    source: "`execution_manager.py` 3764, then 3765, then 3766 into 3767"
---
# What poisons an account

A poisoned account is one that has stopped being trustworthy about its own state, and four failures can make it so.

## The four

Applying a piece of outside news, where that applying fails. Applying an event a recovery owner admitted, where that fails. The account's own loop dying. And a failure while ending a command left on a dead account's queue.

Each of the four is a failure of the machinery that keeps the account's picture of itself true, which is why none of them is retried.

## What travels instead

The task being stopped. On each of those four roads it is let through rather than counted as a failure, so shutting an account down does not poison it.

## What a poisoned account does

Refuses to take an event, refuses to record and apply one, and refuses to take a command. It is no longer counted able to carry orders. Its waiting news is taken off the queue and dropped unapplied — the queue empties and nothing of it is read.

The mark is only ever set, never cleared: nothing in the running system lifts it, and the account comes back only with the process.

## Related

- [What admitting an event refuses](what-admitting-an-event-refuses.md)
- [What a failure reacting to an event costs](what-a-failure-reacting-to-an-event-costs.md)
- [What a failure at startup does](what-a-failure-at-startup-does.md)
