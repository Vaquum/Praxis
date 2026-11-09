---
row: N59-04
baseline: 49aa659
created: 2026-11-08 18:43 UTC
modified: 2026-11-08 18:43 UTC
evidence:
  - claim: "The file is read by the YAML reader first, which turns a bare decimal into a machine fraction before any figure is made from it"
    source: "`nexus/infrastructure/manifest.py` 387, read into the conversions at 406, 427 and 538"
  - claim: "The conversion is made from that value written back out as text, so what it converts is the reader's rendering rather than the file's own characters"
    source: "`nexus/infrastructure/manifest.py` 406, or 427, or 538, or 303"
  - claim: "A figure quoted in the file arrives as text and converts character for character"
    source: "`nexus/infrastructure/manifest.py` 406, the reader leaving a quoted value as text"
  - claim: "Every money figure the manifest carries is converted this way, the ceiling, the pool, each share, and the optional figures beside them"
    source: "`nexus/infrastructure/manifest.py` 406, and 427, and 538, and 303"
---
# What a money figure loses on the way in

A money figure in [a manifest](the-settings-a-host-is-given.md) reaches [the record](the-two-refusals-the-manifest-record-adds.md) by two steps, and the first of them can change it.

## The two steps

The YAML reader reads the file. A bare decimal becomes a machine fraction there, which holds about seventeen digits.

The figure is then made by converting that value written back out as text. So the conversion reads the reader's rendering of the fraction, which is a separate thing from the characters the file holds.

## What that costs

A ceiling written to more places than a machine fraction holds arrives rounded to what that fraction could keep. Every later check and every sum then uses the rounded one, and nothing reports that the figure moved.

## Writing it so it survives

Quoting the figure in the file leaves it as text for the reader, and the conversion then takes it character for character. Quoted, those same digits arrive whole.

The ceiling, the pool, each strategy's share and the optional figures beside them are all converted the same way, so the same holds for each.

## Related

- [The settings a host is given](the-settings-a-host-is-given.md)
- [The two refusals the manifest record adds](the-two-refusals-the-manifest-record-adds.md)
