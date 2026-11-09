---
row: N7-01
baseline: 49aa659
created: 2026-10-27 08:14 UTC
modified: 2026-10-27 08:14 UTC
evidence:
  - claim: "Each strategy the host's manifest names is asked for its own state as bytes, and one that raises has empty bytes kept under its name"
    source: "`nexus/startup/shutdown_sequencer.py` 814-822"
  - claim: "The writing answers at once where nothing at all was kept, which the asking above never leaves it, having put an entry under every name the manifest carries"
    source: "`nexus/startup/shutdown_sequencer.py` 832-833 against 814-822"
  - claim: "A strategy whose bytes came back empty is passed over inside the writing, so the file it had before stands"
    source: "`nexus/startup/shutdown_sequencer.py` 843-844 inside the loop at 842"
  - claim: "A strategy name carrying a path separator is refused rather than written"
    source: "`nexus/startup/shutdown_sequencer.py` 846-848"
  - claim: "Each remaining lot of bytes goes to a temporary file, is pushed to the disk, and the temporary is renamed over the file named for that strategy"
    source: "`nexus/startup/shutdown_sequencer.py` 850-851 into 853-858"
---
# What a stopping host saves of its strategies

A stopping host asks each strategy for its own state as bytes and writes those bytes to a file named for that strategy, for [a later start to read back](what-a-start-does-with-a-strategys-saved-state.md) where its own settings point it at the same directory.

## The asking

Each strategy [the host's manifest](the-settings-a-host-is-given.md) names is asked in turn. One that raises has empty bytes kept under its name, and the host goes on to the next.

## The writing

The writing answers at once where nothing at all was kept — which the asking above never leaves it, having put an entry under every name the manifest carries. Inside the writing, a strategy whose bytes came back empty is passed over — so the raise above leaves the file that strategy had before standing, rather than emptying it.

A name carrying a path separator is refused rather than written. Each remaining lot of bytes goes to a temporary file, is pushed to the disk, and the temporary is renamed over the target — so a file holds either the old bytes or the new ones, never a part of each.

[What a failure in any of that costs](what-a-failed-save-costs-the-stopping.md) depends on which failure it is.

## Related

- [What a failed save costs the stopping](what-a-failed-save-costs-the-stopping.md)
- [What a start does with a strategy's saved state](what-a-start-does-with-a-strategys-saved-state.md)

---

Created 2026-10-27 08:14 UTC · Last modified 2026-10-27 08:14 UTC
