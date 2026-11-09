---
row: N63-07
baseline: 49aa659
created: 2026-11-08 19:26 UTC
modified: 2026-11-08 19:26 UTC
evidence:
  - claim: "Writing a snapshot copies the five collections it carries directly into local ones before any of the five is walked"
    source: "`nexus/infrastructure/wal_codec.py` 75-79, walked at 85, 91, 93, 94 and 95"
  - claim: "The two nested records that carry a collection copy theirs the same way, each as its own writing is reached, so the copies are not all taken at one moment"
    source: "`nexus/infrastructure/wal_codec.py` 170, walked at 181, and 267, walked at 286, reached in turn at 83 and 84"
  - claim: "The copies reach the collections and not what they hold, so each entry walked is the very thing the state holds"
    source: "`nexus/infrastructure/wal_codec.py` 75, copying one level"
  - claim: "Every money figure is written as text, and the version is the one number written as a number"
    source: "`nexus/infrastructure/wal_codec.py` 93, or 173-182, or 270-284, against 82"
  - claim: "The readings that take those figures back accept a number as readily as text, so a payload written by something else need not have used text"
    source: "`nexus/infrastructure/wal_codec.py` 135, or 198, or 309"
---
# The copies taken before a record is written

Writing a snapshot of an account's state takes a copy of every collection in it before writing any of them.

## The copies

The five collections a snapshot carries directly are copied into local ones first, and the writing walks the copies. The two nested records that carry a collection of their own do the same — each as its own writing is reached, which is after the five.

So each collection is walked as it stood when its own copy was taken, and a collection growing midway through its own walk cannot make the bytes disagree with themselves.

## How far a copy reaches

A copy reaches the collection and not what the collection holds. Each entry walked is the very thing the state holds, and what is written out of it is read off that thing at the moment of writing.

The copies are also taken at different moments, each before its own walk. So the bytes are not one state caught at one instant: they are each collection caught at its own, with every entry read later still.

[What order the collections are written in](what-two-writings-of-one-state-give.md) is settled for two of them and left alone for the rest.

## Figures as text

Every money figure is written as text, which is why a figure's exactness survives the crossing. The version is the one number written as a number.

The readings that take those figures back accept a number as readily as text, so a payload written by something else need not have used text to be read.

## Related

- [The version a saved record is read at](the-version-a-saved-record-is-read-at.md)
- [What a malformed saved record is refused as](what-a-malformed-saved-record-is-refused-as.md)
- [What two writings of one state give](what-two-writings-of-one-state-give.md)
