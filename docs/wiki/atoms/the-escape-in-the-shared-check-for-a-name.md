---
row: P8-02
baseline: 49aa659
created: 2026-11-08 11:11 UTC
modified: 2026-11-08 11:11 UTC
evidence:
  - claim: "The shared check for a name lets a none through where the caller asked for optional"
    source: "`praxis/core/domain/_require_str.py` 25-26"
  - claim: "Otherwise it refuses a none and an empty text alike"
    source: "`praxis/core/domain/_require_str.py` 28-30, reached rather than 26"
  - claim: "It never trims, so a name of blank space alone is kept"
    source: "`praxis/core/domain/_require_str.py` 28, which tests the value's truth and not its content once trimmed"
  - claim: "The records on the Nexus side trim before refusing"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 101-103, or `nexus/infrastructure/praxis_connector/trade_outcome.py` 92-94"
---
# The escape in the shared check for a name

One check holds every name on the Praxis side, and two things it does not do decide what a name may be.

## The escape

A caller may ask for the field to be optional. Where it does, a none is let through and the check ends there.

Where the caller asks for nothing of the kind, a none is refused, and so is an empty text, by the same line. The two are caught together rather than separately.

## What it never does

It never trims. The line asks whether the value is truthy, not whether anything is left once the blank space comes off.

So a name of blank space alone is kept. A record whose names all go through this check can carry a name that looks empty everywhere it is printed and is not empty here.

## The seam

The records on the Nexus side trim before refusing. A name of blank space is turned back there and kept here, so the same name crossing the seam meets two different rules, and the stricter one is on the far side.

## Related

- [The questions a record answers about itself](the-questions-a-record-answers-about-itself.md)
- [What a fill's own record requires](what-a-fills-own-record-requires.md)
- [What a command is checked for](what-a-command-is-checked-for.md)
