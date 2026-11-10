---
row: N10-04
baseline: 49aa659
created: 2026-11-07 04:30 UTC
modified: 2026-11-07 04:30 UTC
evidence:
  - claim: "Asked for a strategy, it refuses a name that is not text, one that is empty once trimmed, and one it holds no wrapper for"
    source: "`nexus/strategy/runner.py` 57-59, or else 63-65, or else 69-71"
  - claim: "Built, it refuses anything that is not a dictionary, a key that is not usable text, a value that is not a wrapper, a wrapper whose own name disagrees with its key, and two keys that trim to one name"
    source: "`nexus/strategy/runner.py` 25-27, or 32-34, or 38-40, or 42-44, or 46-48"
  - claim: "The name is trimmed both as the wrappers are taken in and as one is looked up"
    source: "`nexus/strategy/runner.py` 36 at the build against 61 at the lookup"
---
# What the router refuses

The thing that routes to a strategy refuses three things when it is asked for one, and five more when it is built.

## Asked

A name that is not text. A name with nothing left in it once it is trimmed. A name it holds no wrapper for. Each of the three raises, and none of them reaches [the wrapper](the-wrapper-every-strategy-sits-behind.md) at all.

## Built

A set of wrappers that is not a dictionary. A key that is not usable text. A value that is not a wrapper. A wrapper whose own name disagrees with the key it was filed under. Two keys that come to the same name once trimmed.

## Why trimming comes up twice

The name is trimmed as the wrappers are taken in and again as one is looked up, so a name given with blank space round it finds the same wrapper as one without.

## Related

- [The wrapper every strategy sits behind](the-wrapper-every-strategy-sits-behind.md)
- [Which roads reach a strategy](which-roads-reach-a-strategy.md)
