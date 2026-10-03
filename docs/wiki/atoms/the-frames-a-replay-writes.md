---
row: P4-39
baseline: 49aa659
created: 2026-10-03 20:43 UTC
modified: 2026-10-03 20:47 UTC
evidence:
  - claim: "A run writes a price frame and a prediction frame of its own, whatever its bars came from"
    source: "`materialize_bar_frames.py` 80-82 and 86-99, called at `run_replay.py` 237-245"
  - claim: "It writes them before each bar is dispatched"
    source: "`run_replay.py` 237-245 ahead of 247-250"
  - claim: "Each write carries every bar so far, rather than the latest alone"
    source: "`run_replay.py` 225 and 231-232"
  - claim: "Every prediction written is marked usable"
    source: "`materialize_bar_frames.py` 91, the mark at 29"
  - claim: "The price frame gets an opening-stamp column only where opening stamps were handed in"
    source: "`materialize_bar_frames.py` 76-78"
  - claim: "A manifest is written at the root above the predictions, stamped with that bar's closing moment"
    source: "`materialize_bar_frames.py` 101-105, the moment passed at `run_replay.py` 241"
  - claim: "The loop reading it refuses a manifest older than two minutes"
    source: "Nexus `predict_loop.py` 359-371, the stamp read at 445-455"
  - claim: "That loop is given the replay's clock, which is moved to the bar before the loop is run"
    source: "`run_replay.py` 141 into `launcher.py` 4551-4558, advanced at `run_replay.py` 247"
  - claim: "The predictions are written under one name and the loader of real history reads another"
    source: "`materialize_bar_frames.py` 28 and 99 against `load_replay_bars.py` 28 and 63"
---
# The frames a replay writes

Every [replay](replay.md) run writes two frames of its own per series, a price frame and a prediction frame, whatever its bars came from. They are written before each bar is dispatched.

## Growing as the walk goes

Each write carries every bar so far, rather than the latest alone. The frames therefore grow one row at a time as the walk proceeds, and at any point they hold the history up to and including the bar about to be dispatched.

Every prediction written is marked usable. The price frame gets an opening-stamp column only where opening stamps were handed in, which is what makes the written series read as the dollar kind.

## The manifest and the clock

A manifest is written at the root above the predictions, stamped with that bar's own closing moment.

The loop that reads it refuses a manifest older than two minutes. That loop is given [the replay's clock](the-replay-clock.md), and the clock is moved to the bar before the loop is run — so the stamp is current by the clock doing the asking, however old it is by the real one.

## Not a round trip

The predictions are written under one name, and [the loader of real history](where-a-replays-bars-come-from.md) reads another. What a run writes is therefore not what that loader would pick up.

## Related

- [Where a replay's bars come from](where-a-replays-bars-come-from.md)
- [The replay clock](the-replay-clock.md)
