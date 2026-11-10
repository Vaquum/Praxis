---
row: P127-02
baseline: 49aa659
created: 2026-11-09 09:56 UTC
modified: 2026-11-09 09:56 UTC
evidence:
  - claim: "The predicting loop is started first, and a timer loop after it where the account has one"
    source: "`launcher.py` 4668, then 4670 into 4671"
  - claim: "Then the outcome loop, the health loop, the saving timer, the marking loop, and the watch over timed-out handovers, each in turn"
    source: "`launcher.py` 4673, then 4674, then 4675, then 4676, then 4677"
  - claim: "An ordinary stop stops the health loop, the marking loop, the saving timer and that watch, and no others"
    source: "`launcher.py` 4004, then 4005, then 4006, then 4007"
  - claim: "The predicting loop, the timer loop and the outcome loop are handed to the stopping sequence instead"
    source: "`launcher.py` 4018, and 4019, and 4020, into 4030"
  - claim: "The four stopped directly are the four the sequence is not given"
    source: "`launcher.py` 4004-4007, against 4009-4029"
---
# The order an account's loops start and stop in

An account runs seven loops of its own, started in a fixed order as its thread comes up, and stopped by two different things on the way down.

## Starting

The predicting loop first. A timer loop after it, where the account has one at all. Then the outcome loop, the health loop, the saving timer, the marking loop, and [the watch over timed-out handovers](how-the-watch-keeps-itself-going.md), each in turn.

So the loop that produces work starts before the loop that consumes its outcomes.

## Stopping

An ordinary stop stops four of them by hand: the health loop, the marking loop, the saving timer, and the watch.

The predicting loop, the timer loop and the outcome loop are handed to [the stopping sequence](what-a-stopping-host-halts-first.md) instead, which stops them as part of a larger ordering.

## Where the split falls

The four stopped by hand are exactly the four the sequence is not given, and the three the sequence is given are exactly the three not stopped by hand. Nothing is stopped twice and nothing is left running.

The three handed over are the predicting, the timing and the consuming — the three that pass work between them.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [When an account can be delivered to](when-an-account-can-be-delivered-to.md)
- [How the watch keeps itself going](how-the-watch-keeps-itself-going.md)
