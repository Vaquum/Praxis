---
row: P98-03
baseline: 49aa659
created: 2026-11-14 02:30 UTC
modified: 2026-11-14 02:30 UTC
evidence:
  - claim: "Registering a queue for an account happens under a lock of its own"
    source: "`praxis/trading.py` 312, then 313"
  - claim: "Unregistering takes the same lock and tolerates an account that has none"
    source: "`praxis/trading.py` 322, then 323"
  - claim: "Routing looks the queue up under that lock and lets the lock go before anything is put"
    source: "`praxis/trading.py` 335, then 336, ahead of 345"
  - claim: "An account with no queue has its outcome dropped, with a warning naming the account and the command"
    source: "`praxis/trading.py` 338 into 339-341, then 343"
  - claim: "The putting is the kind that refuses rather than waits"
    source: "`praxis/trading.py` 345"
---
# What routing an outcome drops

Outcomes are handed to a queue per account, and an outcome with no queue to go to is dropped.

## The lock

Registering a queue for an account happens under a lock of its own. Unregistering takes the same lock, and tolerates an account that has none — so unregistering twice is as harmless as unregistering once.

## What routing holds the lock for

The lookup, and nothing more. The lock is let go before anything is put on the queue it found.

So a queue unregistered between the lookup and the put still receives that outcome. The lock makes the mapping safe to change; it does not make the handover atomic with the change.

## The outcome with nowhere to go

Dropped, with a warning naming the account and the command. Nothing is retried and nothing is held, so an outcome arriving for an account whose queue has gone is gone with it.

## The putting

The kind that refuses rather than waits. A queue that is full therefore raises into whoever was routing, rather than blocking them until the reader catches up.

So a slow reader becomes an error on the writing side rather than back-pressure, and the outcome that raised is neither queued nor dropped — it is wherever its caller's failure left it.

## Related

- [What the facade refuses once a start has begun](what-the-facade-refuses-once-a-start-has-begun.md)
