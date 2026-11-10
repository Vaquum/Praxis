---
row: P28-01
baseline: 49aa659
created: 2026-11-08 16:17 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "Each bar ends with a settling, after the price is set and the prediction ticked"
    source: "`run_replay.py` 252, after 246-250"
  - claim: "A round of settling waits for the account's queue of commands to empty, then drains outcomes one at a time until none is left"
    source: "`run_replay.py` 264-266 into 268-271, the account looked up at `execution_manager.py` 3599, then 3600 into 3601, or the wait at 3603"
  - claim: "A round that drains no outcome ends the settling"
    source: "`run_replay.py` 272-273"
  - claim: "Eight rounds are allowed, and a settling whose every round drained something raises after the eighth"
    source: "`run_replay.py` 263 with the count at 52, raising at 275-276"
  - claim: "Each wait is given thirty seconds"
    source: "`run_replay.py` 266 with the span at 51"
  - claim: "The wait covers the queue alone, so work the queue has already handed on — a scheme with slices still due — outlives the settling"
    source: "`execution_manager.py` 3603 against the queue marked done at 4021, the next slice timed at 5925-5927"
---
# How a replay settles a bar

A [replay](replay.md) settles each bar before it drives the next: the account's queue of commands is emptied, and the outcomes that produced are read.

## What one round does

It waits for the queue of commands to empty — every command handed to the account's own worker has been taken up. Then it drains outcomes, one at a time, until none is left.

A round that drains no outcome at all ends the settling.

## Why it repeats

Reading an outcome can have the strategy ask for more work, and that work needs taking up and reading in turn. So the two steps repeat as a pair.

Eight rounds are allowed. A settling whose every round drained something raises after the eighth — including the case where the eighth drained the last outcome there was, since what the round tests is whether it drained nothing rather than whether anything is left.

Each wait is given thirty seconds of its own, so a bar can also end the run by not emptying in time.

## What the wait does not cover

Emptying the queue means the commands have been taken up, not finished. [Work fed out over time](work-fed-out-over-time.md) is timed from the account loop's own clock, and a scheme whose next slice is due later has already left the queue.

So a bar can settle with work still to come, and that work arrives during a later bar.

## Related

- [Replay](replay.md)
- [The mode a replay gives itself](the-mode-a-replay-gives-itself.md)
- [Work fed out over time](work-fed-out-over-time.md)
