---
row: N7-07
baseline: 49aa659
created: 2026-10-27 11:20 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "A start reads the file named for each strategy its manifest names and hands the bytes to that strategy"
    source: "`nexus/startup/sequencer.py` 536-537 and 543-547 into 554-555"
  - claim: "Empty bytes are handed over where there is no such file, and where reading one fails"
    source: "`nexus/startup/sequencer.py` 551-552, and 548-550"
  - claim: "So a strategy cannot tell a missing file from an unreadable one, both arriving as empty bytes on one road"
    source: "`nexus/startup/sequencer.py` 548-550 and 551-552 into 554-555"
  - claim: "A strategy that raises while taking its state back is logged and the start goes on"
    source: "`nexus/startup/sequencer.py` 556-557"
  - claim: "A strategy name carrying a path separator is refused and nothing is handed to it at all"
    source: "`nexus/startup/sequencer.py` 539-541"
  - claim: "Nothing at all is read where the directory is unset, and the start says so and moves on"
    source: "`nexus/startup/sequencer.py` 532-534"
  - claim: "The launcher gives the start the setting as it stands, while giving the stopping a fallback where the settings name none"
    source: "`praxis/launcher.py` 4081 against 4014-4017, the setting left unset at 4929-4932, the strategies folder resolved to text at 2449"
---
# What a start does with a strategy's saved state

A start reads the file named for each strategy [its manifest](the-settings-a-host-is-given.md) names and hands the bytes inside to that strategy, so it can rebuild whatever it kept across the stop.

## What it hands over

The bytes from the file, where there is one. Empty bytes where there is no such file — and empty bytes where there is a file but reading it fails. A strategy cannot tell those two apart: a missing file and an unreadable one both arrive as empty bytes, by the same road.

A strategy that raises while taking its state back is logged, and the start goes on to the next.

## What it refuses

A name carrying a path separator is refused, and nothing is handed to that strategy at all — not even the empty bytes a missing file would give it. Where the directory itself is unset, nothing is read for anyone and the start says so.

## Where the two sides look

The launcher gives the start this setting as it stands, and gives [the stopping](what-a-stopping-host-saves-of-its-strategies.md) a fallback directory where the settings name none. So a host whose settings leave it unset saves files on the way down that its own next start never looks for.

## Related

- [What a stopping host saves of its strategies](what-a-stopping-host-saves-of-its-strategies.md)
- [What a restart puts back](what-a-restart-puts-back.md)

---

Created 2026-10-27 11:20 UTC · Last modified 2026-10-27 11:20 UTC
