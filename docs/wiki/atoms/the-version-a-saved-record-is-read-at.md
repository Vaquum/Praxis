---
row: N63-01
baseline: 49aa659
created: 2026-11-12 21:00 UTC
modified: 2026-11-12 21:00 UTC
evidence:
  - claim: "A saved snapshot's version is read with the first version standing in where none is written, so a payload carrying no version is read as the oldest rather than turned away"
    source: "`nexus/infrastructure/wal_codec.py` 114"
  - claim: "Only the first is read, and any other version is refused by name"
    source: "`nexus/infrastructure/wal_codec.py` 116-117, then 119-120"
  - claim: "Two event versions are read, and any other is refused by name"
    source: "`nexus/infrastructure/wal_codec.py` 621-622, and 624-625, then 627-628"
  - claim: "The payload is unpacked with text read back as text, and what it unpacked to must be a mapping before either version is looked at, the complaint for that one naming what arrived instead"
    source: "`nexus/infrastructure/wal_codec.py` 110-113, and 611-614"
---
# The version a saved record is read at

Every record this codec writes into [the log a host keeps](how-a-record-reaches-the-log.md) carries the version it was written at, and that number decides which reader gets it back.

## What comes first

The payload is unpacked with text read back as text, and what it unpacks to must be a mapping. That is checked before any version is looked at, and its complaint names what arrived instead — the one complaint here that says what the thing was.

## The version that stands in

The version is read with the first version standing in where the field is absent. A payload carrying no version is therefore read as the oldest rather than turned away.

## A snapshot

One version is read. Any other number is refused, and the complaint names it, so a snapshot written by a later host arriving at an earlier one says so plainly.

## An event

An event's version is read the same way, [turned into a whole number first](what-happens-to-an-events-version-on-the-way-in.md). Past that, two versions are read and any other number is refused by name, as with a snapshot.

## So

A payload that is no mapping, and a number no reader answers to, are each told apart. A payload written before versions were carried cannot be told from one whose version field was lost.

## Related

- [What a malformed saved record is refused as](what-a-malformed-saved-record-is-refused-as.md)
- [Which version an event is written at](which-version-an-event-is-written-at.md)
- [What happens to an event's version on the way in](what-happens-to-an-events-version-on-the-way-in.md)
