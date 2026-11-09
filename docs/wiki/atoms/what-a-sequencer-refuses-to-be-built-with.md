---
row: N83-01
baseline: 49aa659
created: 2026-11-13 17:30 UTC
modified: 2026-11-13 17:30 UTC
evidence:
  - claim: "Five of the things a sequencer is built with must be present and of their own kind, each weighed in turn"
    source: "`nexus/startup/shutdown_sequencer.py` 118 into 119-120, then 122 into 123-124, then 126 into 127-128, then 130 into 131-132, then 134 into 135-136"
  - claim: "The configuration may be absent, and is weighed for its kind only where it is there"
    source: "`nexus/startup/shutdown_sequencer.py` 138 into 139-140"
  - claim: "Where both a configuration and an account name are given, the two must name the same account"
    source: "`nexus/startup/shutdown_sequencer.py` 142-146 into 147-151"
  - claim: "That last check is skipped where either is absent, so a sequencer can be built knowing one account name or none"
    source: "`nexus/startup/shutdown_sequencer.py` 143-144, both tested before the comparison at 145"
---
# What a sequencer refuses to be built with

Building the thing that brings a host down weighs seven things, and raises on the first that fails.

## The five that must be there

The runner, the manifest, the store, the state and the path the strategy state is kept at. Each must be present and of its own kind, and each is weighed in turn, so the first wrong one is the one reported.

## The one that need not

The configuration. It is weighed for its kind only where it is there, so a sequencer can be built without one.

## The one that compares

Where both a configuration and an account name are given, the two must name the same account. The check is skipped where either is absent.

So three builds are allowed: one knowing the account name twice and agreeing, one knowing it once, and one knowing it not at all. What is refused is knowing it twice and disagreeing.

## Why the order matters

Each check raises, so none of the later ones runs after an earlier failure. A build handing in a wrong runner and a mismatched account name is reported as the wrong runner, and the mismatch is never reached.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
