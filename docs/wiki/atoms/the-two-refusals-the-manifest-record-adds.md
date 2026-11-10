---
row: N59-01
baseline: 49aa659
created: 2026-11-08 18:43 UTC
modified: 2026-11-08 18:43 UTC
evidence:
  - claim: "The loader requires the account's name to have something in it once trimmed, and the ceiling and the pool to convert to a figure from the value the file was read as, to be finite, and to stand above nought, with the pool at or under the ceiling"
    source: "`nexus/infrastructure/manifest.py` 393-396, then 406-419, then 427-441"
  - claim: "It requires the strategies to arrive as a list with something in it, and builds one record per entry"
    source: "`nexus/infrastructure/manifest.py` 443-446, built at 549-556 and collected at 548"
  - claim: "The record built from all that asks the name, both figures and the pool against the ceiling over again, and asks the strategies to be a sealed run of records of that kind"
    source: "`nexus/infrastructure/manifest.py` 226-228, or 232-241, or 243-252, or 254-259, or 261-263, or 269-271"
  - claim: "Each of those is settled before the record is reached, so none of them can refuse a manifest that came from a file"
    source: "`nexus/infrastructure/manifest.py` 393-446 ahead of the build at 559-569"
  - claim: "A strategy name used twice is refused by the record, and the loader makes no such comparison"
    source: "`nexus/infrastructure/manifest.py` 273-275, with no comparison between entries in the loop at 450-557"
  - claim: "The shares adding to more than a hundred is refused by the record, and the loader reads each share without weighing it against the rest"
    source: "`nexus/infrastructure/manifest.py` 278 into 280-282, each share read at 532-541"
  - claim: "The name is trimmed by the loader and trimmed again by the record, the second time on a name already trimmed"
    source: "`nexus/infrastructure/manifest.py` 398, then 230"
---
# The two refusals the manifest record adds

[A host's manifest](the-settings-a-host-is-given.md) is checked as it is read and checked again by the record built from what was read, and two of the record's refusals are the only ones that road can reach.

## What the reading settles

The account's name must have something in it once trimmed. The ceiling and the pool must convert to a figure from [the value the file was read as](what-a-money-figure-loses-on-the-way-in.md), must be finite, must stand above nought, and the pool must stand at or under the ceiling. The strategies must arrive as a list with something in it, and one record is built per entry.

## What the record asks over

All of it. The name, both figures, the pool against the ceiling, and the strategies as a sealed run of records of the right kind.

Every one of those was settled before the record was reached. So on the road from a file, none of them can turn a manifest back — they are there for a manifest put together in code, where nothing has been read.

## The two that can

A strategy name used twice. The loader reads the entries one at a time and never compares one with another, so the record is where a repeat is caught.

The shares adding to more than a hundred. The loader reads each share and weighs it against nothing else.

## The trim done twice

The loader trims the name after requiring it to have something in it. The record requires the same and trims again — the second trim on a name that has already lost its edges.

## Related

- [The settings a host is given](the-settings-a-host-is-given.md)
- [The order a strategy entry is read in](the-order-a-strategy-entry-is-read-in.md)
- [What a money figure loses on the way in](what-a-money-figure-loses-on-the-way-in.md)
- [Which accounts are refused](which-accounts-are-refused.md)
