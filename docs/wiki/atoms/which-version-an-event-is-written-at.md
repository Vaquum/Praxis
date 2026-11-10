---
row: N63-02
baseline: 49aa659
created: 2026-11-08 19:26 UTC
modified: 2026-11-08 19:26 UTC
evidence:
  - claim: "An event carrying an outcome name is written at the second version with that name in it, and one with no name at the first version without it"
    source: "`nexus/infrastructure/wal_codec.py` 581-589, or 591-597"
  - claim: "The second version's reader refuses a name that is not text, that is empty, or that is only spaces, with a complaint naming what arrived"
    source: "`nexus/infrastructure/wal_codec.py` 678-683"
  - claim: "A name absent altogether fails on the reading of the key instead, and is reported as a malformed payload"
    source: "`nexus/infrastructure/wal_codec.py` 677, caught at 691-693"
  - claim: "So the writer never tags a payload at the second version without a usable name, and that refusal answers only a payload no writer here made"
    source: "`nexus/infrastructure/wal_codec.py` 581 standing ahead of 583, against the refusal at 678"
  - claim: "The first version's reader builds the event without a name, leaving the empty one the record declares"
    source: "`nexus/infrastructure/wal_codec.py` 651-656"
  - claim: "Both readers otherwise ask the same four things of the payload and build from them the same way"
    source: "`nexus/infrastructure/wal_codec.py` 651-656, against 684-690"
---
# Which version an event is written at

An event going into [the log](how-a-record-reaches-the-log.md) is written at one of two versions, and which one turns on a single field.

## The field that decides

An event carrying a name for the outcome it came from is written at the second version, with that name in the payload. One carrying no name is written at the first, and the payload has no such field.

The choice is made from the event itself, so nothing is written at the second version without a name to put in it.

## What the second reader insists on

A name that is not text, that is empty, or that holds only spaces is refused, and the complaint carries what arrived.

A name absent altogether never reaches that refusal: reading the key fails first, and what comes back is [the complaint a malformed payload gets](what-a-malformed-saved-record-is-refused-as.md).

Because the writer only reaches the second version with a name in hand, that refusal answers a payload no writer here made: one corrupted in the log, or written by something else.

## What the first reader does

It builds the event from the other four fields and leaves the name as the empty one the event's own record declares.

Both readers otherwise ask the same four things and build from them the same way, so the versions differ in that one field and nothing else.

## What follows from the empty name

A name is what lets a repeated delivery be spotted and dropped. An event read back at the first version has no name, so it is counted as it stands.

## Related

- [The version a saved record is read at](the-version-a-saved-record-is-read-at.md)
- [What a malformed saved record is refused as](what-a-malformed-saved-record-is-refused-as.md)
