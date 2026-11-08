---
row: N17-04
baseline: 49aa659
created: 2026-11-09 20:00 UTC
modified: 2026-11-09 20:00 UTC
evidence:
  - claim: "Each capital share must be a finite decimal above nought and at or below a hundred"
    source: "`nexus/instance_config.py` 256-258, or 259-261"
  - claim: "The shares are added together as the walk goes"
    source: "`nexus/instance_config.py` 262"
  - claim: "A total above a hundred is refused once the walk is done"
    source: "`nexus/instance_config.py` 265-267"
  - claim: "Every other check this record makes reads one field, or one entry of a mapping, and never the entries together"
    source: "`nexus/instance_config.py` 89-285, which adds across entries at 262 and nowhere else"
---
# The one check that reads a mapping whole

One check of the configuration reads every entry of a mapping together. Every other reads one field, or one entry.

## What each share must be

A finite decimal above nought and at or below a hundred. So a share of nought is refused and a share of exactly a hundred is allowed — one strategy may be given everything.

## What they must come to

The shares are added as the walk goes, and a total above a hundred is refused once the walk is done.

So a set of shares each inside the range can still be turned back together: two of sixty each pass on their own and fail as a pair. A total below a hundred is allowed, which leaves part of the pool allotted to nobody.

## Why it stands out

Every other check this record makes weighs one field, or one entry of a mapping, against a constant or a type. This one is the only place the entries are read as a group, and so the only place where what is wrong cannot be pointed at a single entry.

## Related

- [What an instance's configuration refuses](what-an-instances-configuration-refuses.md)
- [The keys this record rewrites](the-keys-this-record-rewrites.md)
