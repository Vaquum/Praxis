---
row: P3-02
baseline: 49aa659
created: 2026-09-28 09:00 UTC
modified: 2026-09-28 17:06 UTC
evidence:
  - claim: "It holds one instant and hands it back when asked the time"
    source: "`replay_clock.py` 39-40"
  - claim: "It changes only when told, by a checked assignment"
    source: "`replay_clock.py` 54-60"
  - claim: "A time without a zone is refused"
    source: "`replay_clock.py` 50-52"
  - claim: "It refuses to go backwards"
    source: "`replay_clock.py` 56-58"
  - claim: "Reading is held under a lock"
    source: "`replay_clock.py` 39, the lock made at 34"
  - claim: "So is moving it"
    source: "`replay_clock.py` 54, into the write at 60"
  - claim: "A replay moves it once per bar"
    source: "`run_replay.py` 247"
  - claim: "It is handed to the parts being replayed as their clock"
    source: "`run_replay.py` 116 and 141"
  - claim: "A slice's due time is worked out by adding its gap to the instant this gives"
    source: "`execution_manager.py` 5926, the gap coming from the settings"
---
# The replay clock

The **replay clock** is the clock a [replay](replay.md) runs on. It holds one instant, hands that instant back to anything asking the time, and changes only when told to.

It is handed to the parts being replayed as their clock, so the time they read is this one rather than the machine's.

## Moving it

The run moves the clock once per bar, to that bar's close.

A time without a zone on it is refused, and so is a time before the one already held. The clock can stand still or go forward; it cannot go back.

## Why it is held apart

Reading the time and moving it are each held under a lock, so a reader cannot catch the clock half-moved. That matters because the parts being replayed are the live ones, and they read the time from more than one thread.

## What it does not stop

The clock standing still is not the same as no time passing. Waits inside the run are real waits, and the machine's own clock still runs; what this fixes is the instant Praxis reads when it asks.

A [slice's](work-fed-out-over-time.md) due time, for instance, is that instant plus the gap from the settings — so the gap is configured, and the clock decides only what it is added to.

## Related

- [Replay](replay.md)
- [The replay venue](the-replay-venue.md)
