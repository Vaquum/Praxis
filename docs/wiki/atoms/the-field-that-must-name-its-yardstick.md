---
row: N17-05
baseline: 49aa659
created: 2026-11-09 20:00 UTC
modified: 2026-11-09 20:00 UTC
evidence:
  - claim: "A reference price source may be left out, and where given must be text"
    source: "`nexus/instance_config.py` 189-193"
  - claim: "It is trimmed and lowered, and refused where nothing is left"
    source: "`nexus/instance_config.py` 194-199"
  - claim: "It is refused unless it matches the one name allowed"
    source: "`nexus/instance_config.py` 201-210, the one name at 26"
  - claim: "The trimmed and lowered value is written back over the field"
    source: "`nexus/instance_config.py` 212-216"
  - claim: "A deviation cap of either kind with no reference price source is refused"
    source: "`nexus/instance_config.py` 218-227"
  - claim: "That is the only check this record makes weighing one of its fields against another"
    source: "`nexus/instance_config.py` 89-285, which compares two of its fields at 218-221 and nowhere else"
---
# The field that must name its yardstick

One field of the configuration names what a deviation is measured against, and the caps that use it cannot be set without it.

## What the name must be

It may be left out. Where given it must be text, is trimmed and lowered, and is refused where nothing is left after that. Then it is refused unless it matches the one name the record allows.

The lowered value is written back over the field, so a caller passing the name in capitals finds the record holding it in lower case.

One name is allowed. A second source would need the set widened, not just the configuration changed.

## The cap that needs it

A deviation cap, whether the account-level one or any per-strategy one, is refused where no source is named. A cap has nothing to measure against without one.

That is the only check this record makes weighing one of its own fields against another. Every other asks one field about itself.

## Related

- [What an instance's configuration refuses](what-an-instances-configuration-refuses.md)
- [The keys this record rewrites](the-keys-this-record-rewrites.md)
