---
row: N23-01
baseline: 49aa659
created: 2026-11-08 15:48 UTC
modified: 2026-11-08 15:48 UTC
evidence:
  - claim: "Starting takes the loop's lock and does nothing at all where the loop is already running"
    source: "`nexus/strategy/timer_loop.py` 68-70"
  - claim: "Otherwise it marks the loop running and schedules one countdown for every timer every strategy declares"
    source: "`nexus/strategy/timer_loop.py` 72 into 74-76"
  - claim: "Stopping takes the same lock, clears that mark, cancels every countdown it is holding and forgets them all"
    source: "`nexus/strategy/timer_loop.py` 81-87"
  - claim: "Nothing stops a stopped loop being started again, the mark being the only thing either reads"
    source: "`nexus/strategy/timer_loop.py` 82 against 69"
  - claim: "The timers the loop was handed are copied as it is built"
    source: "`nexus/strategy/timer_loop.py` 52, walked at 74"
  - claim: "A countdown is filed under its strategy and its own name, so a second timer of the same name for the same strategy would displace the first"
    source: "`nexus/strategy/timer_loop.py` 101-102"
---
# Starting and stopping the timers

The loop that runs [a strategy's timers](what-a-turn-of-a-timer-does.md) is started and stopped through one lock, and a mark it keeps is all either of them reads.

## Starting

Where the loop is already running, starting returns at once, leaving the countdowns it already set going as they are.

Otherwise it marks the loop running and sets a countdown going for every timer every strategy declared. The timers it works from were copied as the loop was built, so a caller that changes its own mapping afterwards changes nothing the loop will schedule.

Each countdown is filed under its strategy's name and the timer's own. Two timers of one name for one strategy would therefore leave one countdown filed, the second displacing the first.

## Stopping

Stopping clears the running mark, cancels every countdown the loop is holding, and forgets all of them.

Clearing the mark is all that distinguishes a stopped loop from a fresh one, so a stopped loop can be started again and will schedule the same set over.

## What stopping does not reach

Cancelling reaches a countdown that has not yet fired. One already firing is not cancelled at all: it [reads the mark itself](what-a-turn-of-a-timer-does.md), and gives up where it finds the mark gone.

Both of its readings happen before it calls the strategy, and the lock is let go between the second reading and the call. A turn that passed both readings therefore runs on, however soon after stopping clears the mark.

## Related

- [What a turn of a timer does](what-a-turn-of-a-timer-does.md)
- [Which roads reach a strategy](which-roads-reach-a-strategy.md)
