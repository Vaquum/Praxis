---
row: N72-07
baseline: 49aa659
created: 2026-11-08 21:25 UTC
modified: 2026-11-08 21:25 UTC
evidence:
  - claim: "Reading the manifest sits inside one attempt naming the ordinary kind of failure, each such failure becoming one complaint naming the step and carrying the failure's words"
    source: "`nexus/startup/sequencer.py` 495, and 497, raising at 498"
  - claim: "Recovering the state asks the store, and where the store has nothing a fresh state is made from the manifest's pool"
    source: "`nexus/startup/sequencer.py` 239-240, then 246"
  - claim: "A store with nothing and no manifest in hand stops the start with a complaint saying a fresh state cannot be made"
    source: "`nexus/startup/sequencer.py` 241-245"
  - claim: "A complaint of the starting's own kind is let through the attempt around it unchanged, whichever step raised it, and an ordinary failure of any other kind is wrapped"
    source: "`nexus/startup/sequencer.py` 247-248, against 249-250"
  - claim: "A first start and a recovery take the same road, the difference being only whether the store had anything"
    source: "`nexus/startup/sequencer.py` 239-246"
  - claim: "Registering the account with the trading side is skipped with a warning where either the road to it or the manifest is absent, the warning written on each such attempt"
    source: "`nexus/startup/sequencer.py` 255-257"
  - claim: "Where both are there, a failure of the registering stops the start"
    source: "`nexus/startup/sequencer.py` 259-262"
---
# What a start wraps, and what it lets through

Several steps of a start put their work inside one attempt and turn any failure into one complaint. One of them makes an exception of its own complaints.

## Reading the manifest

One attempt around the whole reading, naming the ordinary kind of failure. Each such failure — a missing file, a malformed one, a figure the record refuses — becomes one complaint naming the step and carrying the failure's own words.

So the complaints the manifest's own reading makes, each careful about which field was wrong, arrive as the tail of a single sentence about loading.

## Recovering the state

The store is asked. Where it has nothing, a fresh state is made from the manifest's pool — so a first start and a recovery take the same road, differing only in whether the store had anything.

Where the store has nothing and no manifest is in hand, the start stops with a complaint saying a fresh state cannot be made.

A complaint of the starting's own kind is let through the attempt around it unchanged, whichever step raised it, while an ordinary failure of any other kind is wrapped. So this step tells a complaint already shaped for a caller apart from one that is not.

## Registering with the trading side

Skipped, with a warning, where either the road to it or the manifest is absent. The warning is written on each such attempt rather than once, nothing here remembering that it was written.

Where both are there, a failure of the registering stops the start.

## Related

- [Starting a host](starting-a-host.md)
- [How the strategies are built](how-the-strategies-are-built.md)
