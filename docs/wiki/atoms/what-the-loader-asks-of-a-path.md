---
row: N17-06
baseline: 49aa659
created: 2026-11-09 20:00 UTC
modified: 2026-11-09 20:00 UTC
evidence:
  - claim: "A strategy's file must be given as a relative path"
    source: "`nexus/strategy/loader.py` 55-57"
  - claim: "It must end in the usual suffix for a module"
    source: "`nexus/strategy/loader.py` 59-61"
  - claim: "The base and the joined path are both resolved, and the joined one is refused where it falls outside the base"
    source: "`nexus/strategy/loader.py` 63-64 into 66-70"
  - claim: "The file must be there"
    source: "`nexus/strategy/loader.py` 72-74"
---
# What the loader asks of a path

Three checks stand between a line of a manifest and a file being read, and one of them is a guard.

## Relative, and a module

The path must be given relative, not absolute. It must end in the usual suffix for a module.

## Inside the base

The base is resolved, the path is joined to it, and the result is resolved too. The joined path is then refused where it falls outside the base.

Resolving before testing is what makes this hold: a path climbing out with steps upward is caught, and so is a link inside the base pointing at a file outside it. Running the loader on both shows the same refusal, naming the place the path really led.

## There at all

Past the guard, the file must be there.

## Related

- [What the loader asks of what it found](what-the-loader-asks-of-what-it-found.md)
- [What a strategy must provide](what-a-strategy-must-provide.md)
