---
row: N18-02
baseline: 49aa659
created: 2026-11-08 10:55 UTC
modified: 2026-11-08 10:55 UTC
evidence:
  - claim: "Three kinds of entry are named for the log"
    source: "`nexus/infrastructure/wal_entry.py` 19-21"
  - claim: "An entry's number is refused below nought"
    source: "`nexus/infrastructure/wal_entry.py` 43-45"
  - claim: "Nothing asks that number for its type, so a true-or-false or a fraction at or above nought is let by"
    source: "`nexus/infrastructure/wal_entry.py` 40-57, which asks a type at 47, 51 and 55 and not of the number"
  - claim: "Its kind must be one of the named ones and what it carries must be bytes"
    source: "`nexus/infrastructure/wal_entry.py` 51-53, or 55-57"
  - claim: "Its moment must be a moment, with no zone demanded of it"
    source: "`nexus/infrastructure/wal_entry.py` 47-49"
---
# What an entry in the log refuses

One entry in the write-ahead log is refused for failing any one of four checks.

## The three kinds

An entry is a whole-state write, a change to the state, or a strategy's own event. Its kind must be one of those three.

## The number that orders the log

Refused below nought, and asked nothing else. Three of this record's four checks ask a type; this one does not.

So a true-or-false stands as a number here, and so does a fraction. Either is kept as it came.

## The moment

A moment, with no zone demanded. [Two other moments on this side](the-moments-with-no-marker.md) are held to that same weaker rule, where the records crossing to the trading side demand the universal-time marker itself.

## What it carries

Bytes. A record carrying text instead is refused.

## Related

- [What a record of processing refuses](what-a-record-of-processing-refuses.md)
- [The moments with no marker](the-moments-with-no-marker.md)
- [When a read raises instead of stopping](when-a-read-raises-instead-of-stopping.md)
