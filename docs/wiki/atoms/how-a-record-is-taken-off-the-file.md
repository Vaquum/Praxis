---
row: N76-03
baseline: 49aa659
created: 2026-11-13 07:30 UTC
modified: 2026-11-13 07:30 UTC
evidence:
  - claim: "Every walk of the log measures the file's size before opening it"
    source: "`nexus/infrastructure/wal.py` 94, or 129, or 193"
  - claim: "A walk opens the file once and reads forward through the one handle to the end"
    source: "`nexus/infrastructure/wal.py` 96, or 131, or 195"
  - claim: "The marker is read off the front of the file before any record is taken"
    source: "`nexus/infrastructure/wal.py` 97, or 132, or 196"
  - claim: "A record is taken by reading a head of a fixed size, and the length and the check are unpacked from that head"
    source: "`nexus/infrastructure/wal.py` 102 then 105, or 143 then 148, or 202 then 205-208"
  - claim: "Each walk's loop is endless as written, so it is left only through an ending reached inside it"
    source: "`nexus/infrastructure/wal.py` 100, or 142, or 201"
  - claim: "Every ending inside the truncation scan's loop is an answer, so the answer standing after that loop cannot be reached"
    source: "`nexus/infrastructure/wal.py` 117, against the answers at 104, or 110, or 113, or 116"
---
# How a record is taken off the file

Three roads walk [the log's](how-a-record-reaches-the-log.md) file — the scan that finds where to truncate, and [the two readings](the-two-readings-of-the-log.md) — and all three take a record the same way.

## The size and the handle

The file's size is measured before the file is opened. The walk then opens it once and reads forward through that one handle to the end, so the size it weighs lengths against is the size as of the moment before the reading began.

## Taking a record

The marker is read off the front of the file first, before any record. Then a head of a fixed size is read. The length and the check are unpacked from that head, and the payload read after it.

So the file is self-describing from the front: a walk never needs to know where a record ends before it has read that record's head.

## Leaving the loop

Each of the three loops is endless as written. A walk leaves one only through an ending it reaches inside: a head too short, a length over the cap or past what is left, a payload cut off, or a check that does not match. [Which of those ends a walk quietly and which raises](the-two-readings-of-the-log.md) is what separates the three.

## The answer that cannot be reached

In the truncation scan every one of those endings is an answer. So the answer standing after its loop cannot be reached, whatever the file holds.

## Related

- [The two readings of the log](the-two-readings-of-the-log.md)
- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [What packs a record and what forces a folder](what-packs-a-record-and-what-forces-a-folder.md)
