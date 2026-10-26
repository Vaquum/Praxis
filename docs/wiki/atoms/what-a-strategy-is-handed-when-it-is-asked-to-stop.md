---
row: N6-02
baseline: 49aa659
created: 2026-10-26 16:10 UTC
modified: 2026-10-26 18:10 UTC
evidence:
  - claim: "The host lists every position it holds once, under a lock where one was supplied, and gives each strategy the ones carrying its own name"
    source: "`nexus/startup/shutdown_sequencer.py` 300-303 into 308-311"
  - claim: "The positions in that list are the host's own objects, carried through unchanged, and each can be altered in place"
    source: "`nexus/startup/shutdown_sequencer.py` 303 and 308-311 into 319-320, the shape left open at `nexus/core/domain/position.py` 20-21"
  - claim: "It is given what is left of its slice of the pool once what it has deployed is taken off, floored at nought"
    source: "`nexus/startup/shutdown_sequencer.py` 313-315"
  - claim: "The slice is the settings' pool at the share those settings give the strategy, a share refused unless it is above nought and at or below a hundred"
    source: "`nexus/startup/shutdown_sequencer.py` 313, the share refused at `nexus/infrastructure/manifest.py` 159-161"
  - claim: "It is given the operational mode, which the host set to halted a moment earlier"
    source: "`nexus/startup/shutdown_sequencer.py` 316 and 322, against 183"
  - claim: "The settings handed with them carry nothing at all"
    source: "`nexus/startup/shutdown_sequencer.py` 318"
  - claim: "What was kept is sorted after every strategy has been asked: the exits and the aborts go on, an entry or a change is logged and left out"
    source: "`nexus/startup/shutdown_sequencer.py` 343-363 into 382-386"
  - claim: "Each strategy in the host's settings is asked in turn, by its trimmed name"
    source: "`nexus/startup/shutdown_sequencer.py` 305-306 into 326"
  - claim: "Its answer is kept only where it answers with something"
    source: "`nexus/startup/shutdown_sequencer.py` 327-328"
  - claim: "A strategy that raises is logged and nothing is kept from it, the host going on to the next"
    source: "`nexus/startup/shutdown_sequencer.py` 329-330 under the loop at 305"
---
# What a strategy is handed when it is asked to stop

A strategy asked what it wants done as the host stops is handed three things: its own positions, the money it still has room for, and the mode the host is now in.

## Its own positions

The host lists every position it holds once, under a lock where one was supplied, and gives each strategy the ones carrying its name.

The [positions](holdings.md) in that list are the host's own objects, so a strategy altering one alters what the host holds.

## The money it has room for

Its slice of the settings' pool — that pool at the share those settings give it, a share refused unless it is above nought and at or below a hundred — less what it already has deployed, floored at nought. A strategy that has deployed more than its slice is told it has none.

## The mode

The mode as it stands, which [the host set to halted](what-a-stopping-host-halts-first.md) a moment earlier. The settings handed alongside carry nothing at all, so a strategy reading its own settings here reads an empty set.

## What becomes of the answer

Each strategy in the host's settings is asked in turn, by its trimmed name, and its answer is kept only where it answers with something. A strategy that raises is logged and nothing is kept from it; the host goes on to the next.

Once every strategy has been asked, what was kept is sorted: [the exits](the-sale-a-host-sends-as-it-stops.md) and [the aborts](the-abort-a-host-sends-as-it-stops.md) go on, and an entry or a change is logged and left out.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [The sale a host sends as it stops](the-sale-a-host-sends-as-it-stops.md)

---

Created 2026-10-26 16:10 UTC · Last modified 2026-10-26 18:10 UTC
