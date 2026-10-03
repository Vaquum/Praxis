---
row: P4-17
baseline: 49aa659
created: 2026-10-03 20:49 UTC
modified: 2026-10-03 21:03 UTC
evidence:
  - claim: "One address starts a run and another reports on it"
    source: "`replay_api.py` 172-173"
  - claim: "A peer that is not the local machine is refused"
    source: "`replay_api.py` 48-51 and 63-64, the two addresses allowed at 42, fitted at 171"
  - claim: "The listener binds to the local address only"
    source: "`replay_api.py` 187"
  - claim: "The strategy's text is put into the scenario and the run loads it as a module"
    source: "`replay_api.py` 227 and 109 into `run_replay.py` 110-112 and 321-328, reached through `launcher.py` 4077-4085 and Nexus `loader.py` 102-112"
  - claim: "A body that is not JSON, or is JSON but not an object, is refused"
    source: "`replay_api.py` 119-125"
  - claim: "A request names a series, a gap, a window, an account, a pair, starting money, the pair's rules and the strategy's text"
    source: "`replay_api.py` 197-228 and 247-254"
  - claim: "The gap must be above nought"
    source: "`replay_api.py` 198 and 200-202"
  - claim: "The window must not run backwards"
    source: "`replay_api.py` 207-209"
  - claim: "The starting money and all five of the pair's rules must each be a finite number above nought"
    source: "`replay_api.py` 235-241, called at 225 and 247-254"
  - claim: "The window is turned into bars on the listening thread, before a name is given or work queued"
    source: "`replay_api.py` 128 into `load_replay_bars.py` 62-104, ahead of `replay_api.py` 148-155"
  - claim: "A window resolving to no usable bar is refused"
    source: "`replay_api.py` 132-135"
  - claim: "So is one resolving to more bars than the limit set when the service was built, fifty thousand unless named"
    source: "`replay_api.py` 137-146, the default at 43"
---
# Asking for a replay from outside

A [replay](replay.md) can be asked for over HTTP. One address starts a run; another [reports on one already started](what-a-replay-run-reports-back.md).

## Only from this machine

A peer that is not the local machine is refused, and the listener binds to the local address alone. A request carries the text of a strategy, which the run writes out and loads as a module.

## What a request must carry

A series and a gap, a window of two moments, an account, a trading pair, starting money, the five rules for that pair, and the strategy's own text.

A body that is not JSON is refused, and so is one that is JSON but not an object. The gap must be above nought. The window must not run backwards. The starting money, and each of the five rules, must be a finite number above nought.

## What the window must resolve to

The window is turned into [bars](where-a-replays-bars-come-from.md) on the listening thread, before any name is given out. One resolving to no usable bar is refused, and so is one resolving to more bars than the limit set when the service was built — fifty thousand, unless another was named.

## Related

- [What a replay run reports back](what-a-replay-run-reports-back.md)
- [Where a replay's bars come from](where-a-replays-bars-come-from.md)
- [What a replay reports](what-a-replay-reports.md)
