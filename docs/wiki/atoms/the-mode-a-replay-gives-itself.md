---
row: P28-02
baseline: 49aa659
created: 2026-11-11 11:00 UTC
modified: 2026-11-11 11:00 UTC
evidence:
  - claim: "A replay sets the account's mode to active itself, before it drives any bar"
    source: "`run_replay.py` 161 into 205-207, ahead of 163-166"
  - claim: "It writes that under the positions lock, naming the replay as what moved it and the clock's moment as when"
    source: "`run_replay.py` 205 and 208-209"
  - claim: "A run raises where the launcher left it without a trading side, a loop or a record"
    source: "`run_replay.py` 153-159"
---
# The mode a replay gives itself

A [replay](replay.md) puts the account into the active mode itself, before the first bar is driven.

## Why it has to

[The mode an account is in](what-stops-a-health-turn.md) is normally moved by the loop that reads health. A replay has no venue answering and starts no such loop, so nothing else would move the account out of whatever mode it was built in.

The write is made under the lock that guards the positions — the same lock the health loop writes that mode under.

## What the record says

The mode is active. What moved it is recorded as the replay. When it moved is taken from [the replay's own clock](replay.md), so the moment belongs to the replayed history rather than to the hour the replay was run in.

## What the run requires first

Before any of this, the run reads back the trading side, the loop and the record the launcher built. A run finding any of the three missing raises, rather than driving bars against half a host.

## Related

- [Replay](replay.md)
- [How a replay settles a bar](how-a-replay-settles-a-bar.md)
- [What stops a health turn](what-stops-a-health-turn.md)
