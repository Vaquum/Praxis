---
row: N3-03
baseline: 49aa659
created: 2026-10-22 15:20 UTC
modified: 2026-11-13 12:00 UTC
evidence:
  - claim: "A fill that came back with a result builds one event naming the strategy, the amount, the moment and the outcome it came from"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 260-268"
  - claim: "Which fills come back with a result, and which raise instead, is decided before any of this"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 256-260"
  - claim: "The event is appended, and only then do the figures move, all of it under the lock that guards them"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 268 and 285 before 286-291"
  - claim: "Nothing there catches a failure, so an append that fails stops the pass with the figures untouched"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 285-291"
  - claim: "Appending takes its own lock, writes the entry under the sequence number standing, and raises that number after"
    source: "`nexus/infrastructure/state_store.py` 236-245"
  - claim: "The strategy's own total always takes the result and its high-water mark is always set to the greater of itself and that total; the three rolling windows take the size of the result only where it is a loss"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 812-823"
  - claim: "The account's total is replaced, and the figures worked out from it again: what the account is worth, the high marks, how far down it is, and the worst it has been"
    source: "`nexus/core/domain/risk_state.py` 280-281 into 238-271"
  - claim: "The pass that rebuilds rolling losses takes that same lock, and writes those three windows and nothing else"
    source: "`nexus/infrastructure/state_store.py` 377 and 382-390"
---
# Where a realized result is written down

A realized result is what a sale came to, and it is written to the record before it is counted anywhere.

## The event and the order

[A fill that came back with a result](which-fills-come-back-with-a-result.md) is the only one that reaches any of this.

One event is built, naming the strategy, what the result came to, when it happened, and which outcome it came from. It is appended to the record first. Only then do the figures move, and all of it happens under the one lock that guards them: the strategy's own total takes the result, its high-water mark is set to the greater of itself and that total, a loss has its size added to each of three rolling windows while a gain leaves them alone, and the account's total is replaced, with [what it is worth and how far down it is](how-far-down-the-account-is.md) worked out from it again.

Appending takes a second lock of its own, writes the entry under the sequence number standing, and raises that number after.

## What the order is for

Nothing catches a failure between the append and the figures, so an append that fails stops the pass there, with the figures as they were and the caller told.

Were the figures moved first, a failed append would leave the account counting a result the record is missing. The pass that rebuilds rolling losses would not put it back: it writes those three windows and nothing else. It also takes the same lock, so it cannot read the figures between the write and the count.

## Related

- [What an exit outcome changes](what-an-exit-outcome-changes.md)
- [How far down the account is](how-far-down-the-account-is.md)

---

Created 2026-10-22 15:20 UTC · Last modified 2026-10-23 09:00 UTC
