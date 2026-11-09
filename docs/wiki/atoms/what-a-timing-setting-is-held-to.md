---
row: P117-01
baseline: 49aa659
created: 2026-11-15 03:00 UTC
modified: 2026-11-15 03:00 UTC
evidence:
  - claim: "A timing setting is read from the environment, and a default stands in where it is absent or holds nothing"
    source: "`launcher.py` 227, then 228 into 229"
  - claim: "A value that will not read as a number refuses the start, the refusal naming the variable, what it held and the shape expected"
    source: "`launcher.py` 231-232 into 233, then 234-238"
  - claim: "A value that is not finite, or that stands at or below nought, refuses the start the same way"
    source: "`launcher.py` 240 into 241-246"
  - claim: "Otherwise it is handed back as given"
    source: "`launcher.py` 248"
  - claim: "Five settings are read this way: how often the whole state is saved, how often holdings are marked, how long an unclear send waits before a warning, how often such sends are looked over, and how often a mark is sampled"
    source: "`launcher.py` 4591-4594, and 4601-4604, and 4619-4622, and 4623-4626, and 254-256, the defaults at 207-211"
  - claim: "The sampling cadence alone is then refused unless it is a whole number of seconds, and handed back as a whole number"
    source: "`launcher.py` 258 into 259-263, then 265"
  - claim: "A cap read from the same environment is answered with nothing where its setting holds nothing, where a timing setting is answered with its default"
    source: "`launcher.py` 696 into 697, against 228 into 229"
  - claim: "A cap of the wrong shape refuses with a failure of another kind"
    source: "`launcher.py` 705-707, against 240-246"
---
# What a timing setting is held to

A timing setting is a number of seconds read from the environment, and five of them settle how often the host does something.

## The five

How often the whole state is saved, how often holdings are marked, how long an unclear send waits before a warning, how often such sends are looked over, and how often a mark is sampled. Each has a figure standing behind it, used where the setting is not given.

## What the reading insists on

Absent, or holding nothing, and that figure stands in. Holding anything that will not read as a number, and the start is refused, the refusal naming the variable, what it held, and the shape expected. Holding a figure that is not finite, or one at or below nought, and the start is refused the same way.

So an endless figure is turned away as firmly as a misspelt one, and a wait of no time at all with it.

## The one held tighter

The sampling cadence is then refused unless it is a whole number of seconds, and handed back as a whole number. The other four take a fraction.

## How a cap differs

[A cap](the-deployment-caps.md) is read from the same environment by a reader of its own, and the two part twice. A cap whose setting holds nothing is answered with nothing, where a timing setting is answered with its figure. And a cap of the wrong shape refuses with a failure of another kind, so anything sorting failures by kind sees the two apart.

## Related

- [The deployment caps](the-deployment-caps.md)
- [The settings a host is given](the-settings-a-host-is-given.md)
