---
row: P182-01
baseline: 49aa659
created: 2026-11-09 13:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "Three queues are drained in turn: the events waiting to be taken in, the news from outside, and the work to be reacted to"
    source: "`execution_manager.py` 3734, then 3735, then 3736, then 3737"
  - claim: "One round is all the account's worker asks for"
    source: "`execution_manager.py` 3739, reached from 3907"
  - claim: "Where the caller asked for empty, the round repeats until none of the three holds anything"
    source: "`execution_manager.py` 3739, then 3740, reading 3746-3750"
  - claim: "The call a boot makes drains only for an account marked as booting"
    source: "`execution_manager.py` 3687, then 3688, then 3689"
  - claim: "Marking an account as booting is an ask of its own, and a name the manager does not hold is left alone"
    source: "`execution_manager.py` 3619, then 3620 into 3621"
  - claim: "The mark is cleared when the boot finishes"
    source: "`execution_manager.py` 3670, then 3671 into 3672"
---
# Draining an account's outside events

An event arriving from outside can be waiting in any of three queues, and draining means emptying all three in the order they feed each other.

## The order

The events waiting to be taken in, then the news from outside, then the work to be reacted to. An event taken in is recorded before it is reacted to, so draining one queue and not the others leaves a picture that lags what the account has already been handed.

## One round or many

[The account's own worker](how-waiting-work-is-drained.md) asks for one round. A boot asks for empty, and the round then repeats until none of the three holds anything — because reacting to one event can hand in another, which a single round would leave behind.

## Who may ask

The call a boot makes drains only for an account marked as booting. Marking an account as booting is an ask of its own, and a name the manager does not hold is left alone. The mark is cleared when the boot finishes.

So the draining a boot does cannot run while that worker is running, and the worker's own draining is one round of the same three.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [What a caller waiting on an admitted event is told](what-a-caller-waiting-on-an-admitted-event-is-told.md)
- [What a failure reacting to an event costs](what-a-failure-reacting-to-an-event-costs.md)
