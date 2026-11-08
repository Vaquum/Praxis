---
row: N63-08
baseline: 49aa659
created: 2026-11-12 22:00 UTC
modified: 2026-11-12 22:00 UTC
evidence:
  - claim: "An event's version is turned into a whole number before any reader is chosen, the one place in the codec where a version is converted"
    source: "`nexus/infrastructure/wal_codec.py` 616, against the snapshot's at 114"
  - claim: "The turning is a cutting down rather than a test, so a version written as a fraction is read as the whole number below it"
    source: "`nexus/infrastructure/wal_codec.py` 616 into 621-622"
  - claim: "A version that will not convert gets a complaint naming two grounds"
    source: "`nexus/infrastructure/wal_codec.py` 617-619"
  - claim: "A figure too large to be made whole fails on a third ground that complaint does not answer, so it escapes undressed"
    source: "`nexus/infrastructure/wal_codec.py` 617, catching two kinds"
---
# What happens to an event's version on the way in

[An event's version](the-version-a-saved-record-is-read-at.md) is turned into a whole number before any reader is chosen. It is the one version in the codec that is converted at all.

## What the turning gives back

The turning gives back the whole number at or below what it was handed. A version written as a fraction just above the first therefore reads as the first, and the fraction is reported nowhere.

So a payload whose version was damaged into a fraction is read by a reader rather than refused, and read by whichever reader the whole part names.

## The complaint, and what it misses

A version that will not convert at all gets a complaint of its own, naming two grounds: a value of the wrong kind, and one whose text is no number.

A figure too large to be made whole fails on a third ground, which that complaint does not name. It escapes as it was raised, so a caller sees a failure from the arithmetic rather than anything about a version.

## Why it matters here and nowhere else

A snapshot's version is never converted. It is compared as it arrived, so a snapshot's fraction is refused by name where an event's is cut down and read.

## Related

- [The version a saved record is read at](the-version-a-saved-record-is-read-at.md)
- [Which version an event is written at](which-version-an-event-is-written-at.md)
