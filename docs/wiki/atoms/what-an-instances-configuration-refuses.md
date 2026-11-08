---
row: N17-01
baseline: 49aa659
created: 2026-11-09 20:00 UTC
modified: 2026-11-10 17:30 UTC
evidence:
  - claim: "The account and the venue must each be text with something left in them once trimmed"
    source: "`nexus/instance_config.py` 89-91, or 93-95"
  - claim: "The window for spotting a duplicate must be a whole number above nought, a true-or-false refused outright"
    source: "`nexus/instance_config.py` 97-103, or 104-106"
  - claim: "A cap on how fast entries may go in, and a limit on how stale the book may be, may each be left out, and where one is given it is held to the same rule"
    source: "`nexus/instance_config.py` 108 into 109-118, or 120 into 121-133"
  - claim: "A cap on the spread and one on deviation may each be left out, and where one is given it must be a finite decimal at or above nought"
    source: "`nexus/instance_config.py` 135-139 into 140-143"
  - claim: "The self-trade setting must be one of the named ones"
    source: "`nexus/instance_config.py` 229-231"
  - claim: "Two shutdown timeouts are walked and each refused unless it is a finite number above nought, a true-or-false refused"
    source: "`nexus/instance_config.py` 275-278 into 279-287"
---
# What an instance's configuration refuses

The record of how one instance is configured carries twenty-seven refusals, and the plainest of them hold its single fields.

## The two that must be there

The account and the venue, each text with something left once the blank space is trimmed off.

## The figures that must be whole

The window for spotting a duplicate must be a whole number above nought. A true-or-false is refused outright, though such a thing counts as a whole number.

A cap on how fast entries may go in, and a limit on how stale the book may be, may each be left out. Where one is given it is held to that same rule.

## The figures that may be fractions

A cap on the spread and one on deviation may each be left out too. Where one is given it must be a finite decimal at or above nought — so nought is allowed, and a cap of nought is not the same as no cap at all.

## The named setting and the two timeouts

The self-trade setting must be one of the named ones. The two shutdown timeouts are walked together and each refused unless it is a finite number above nought, a true-or-false again refused.

## Related

- [The mapping this record accepts and its neighbours do not](the-mapping-this-record-accepts-and-its-neighbours-do-not.md)
- [The keys this record rewrites](the-keys-this-record-rewrites.md)
- [The one check that reads a mapping whole](the-one-check-that-reads-a-mapping-whole.md)
- [The field that must name its yardstick](the-field-that-must-name-its-yardstick.md)
