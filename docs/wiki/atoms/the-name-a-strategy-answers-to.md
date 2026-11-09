---
row: N22-02
baseline: 49aa659
created: 2026-11-08 15:43 UTC
modified: 2026-11-08 15:43 UTC
evidence:
  - claim: "A strategy's name must be text, and what is kept is that text trimmed"
    source: "`nexus/strategy/base.py` 33-35, trimmed at 37 and kept at 43"
  - claim: "A name left empty by the trimming is refused"
    source: "`nexus/strategy/base.py` 39-41"
  - claim: "The wrapper answers to the name the strategy kept"
    source: "`nexus/strategy/executor.py` 39"
  - claim: "The routing trims the name both as it files a wrapper and as it looks one up, so a name given with blank space around it finds the wrapper filed without it"
    source: "`nexus/strategy/runner.py` 36 and 61, the lookup at 67"
  - claim: "Each of the eight ways in goes through that one lookup and hands the call to the wrapper it found"
    source: "`nexus/strategy/runner.py` 95, or 119, or 143, or 167, or 189, or 204, or 217, or 230, each through 67-73"
---
# The name a strategy answers to

A strategy is built with a name, and what it keeps is that name trimmed of the blank space around it.

## What is refused

A name that is not text. A name left empty once the trimming is done.

So a name of blank space alone is refused here. [The shared check Praxis names its records by](the-escape-in-the-shared-check-for-a-name.md) keeps such a name instead, which is one of the places the two sides differ over the same question.

## What the name is for

[The wrapper](the-wrapper-every-strategy-sits-behind.md) answers to the name its strategy kept, carrying none of its own.

[The routing](what-the-router-refuses.md) trims as well, both when it files a wrapper under a name and when it looks one up. A call naming a strategy with blank space around the name therefore finds the wrapper filed without it.

Each of [the eight ways in](which-roads-reach-a-strategy.md) goes through that one lookup and hands the call to the wrapper it found. None of them reads the call, and none does anything with what comes back.

## Related

- [The wrapper every strategy sits behind](the-wrapper-every-strategy-sits-behind.md)
- [What the router refuses](what-the-router-refuses.md)
- [Which roads reach a strategy](which-roads-reach-a-strategy.md)
