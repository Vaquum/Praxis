---
row: N17-03
baseline: 49aa659
created: 2026-11-09 20:00 UTC
modified: 2026-11-09 20:00 UTC
evidence:
  - claim: "Each key of the per-strategy caps must be text, and is trimmed before it is used"
    source: "`nexus/instance_config.py` 153 into 154-159, trimmed at 161"
  - claim: "A key with nothing left once trimmed is refused"
    source: "`nexus/instance_config.py` 161-167"
  - claim: "A key that collides with one already taken, after the trimming, is refused"
    source: "`nexus/instance_config.py` 168-173"
  - claim: "Each value must be a finite decimal at or above nought"
    source: "`nexus/instance_config.py` 174-178"
  - claim: "The trimmed mapping is sealed over the field the original arrived in"
    source: "`nexus/instance_config.py` 183-187"
  - claim: "The capital shares are walked the same way, their keys held to the same two refusals and their own mapping sealed the same way"
    source: "`nexus/instance_config.py` 242-245, or 246-249, or 250-255, with 269-273"
---
# The keys this record rewrites

Two of the configuration's mappings have their keys trimmed as they are read, and each refuses the clash its own trimming can create.

## The trimming

Each key must be text. It is trimmed, and one with nothing left after that is refused.

What is kept is the trimmed key. So a caller naming a strategy with a space on the end finds the record holding the name without it.

## The clash the trimming makes

Two keys differing only in blank space trim to one. The record refuses that: a key colliding with one already taken is turned back by name.

So the rewriting cannot silently drop an entry. A mapping that would have lost one is refused instead of being quietly made smaller.

## What is kept

Each value must be a finite decimal at or above nought. The trimmed mapping is then sealed over the field the original arrived in, so [what the sealing reaches and what it leaves alone](the-sealing-three-records-do.md) applies here too.

The capital shares are walked the same way, with the same two refusals on their keys and the same sealing at the end.

## Related

- [What an instance's configuration refuses](what-an-instances-configuration-refuses.md)
- [The one check that reads a mapping whole](the-one-check-that-reads-a-mapping-whole.md)
- [The sealing three records do](the-sealing-three-records-do.md)
