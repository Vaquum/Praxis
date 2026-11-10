---
row: N44-02
baseline: 49aa659
created: 2026-11-08 17:10 UTC
modified: 2026-11-08 17:10 UTC
evidence:
  - claim: "The check answers nothing for a file that is not there"
    source: "`nexus/infrastructure/wal.py` 239-240"
  - claim: "It answers nothing for a file too small to hold a marker"
    source: "`nexus/infrastructure/wal.py` 242-243"
  - claim: "It raises for a file big enough whose marker is wrong, or short"
    source: "`nexus/infrastructure/wal.py` 245-250"
  - claim: "The store makes it as it is built, before its own first reading"
    source: "`nexus/infrastructure/state_store.py` 114, ahead of 115"
  - claim: "A recovery makes it again before reading, and so does a plain reading of the events"
    source: "`nexus/infrastructure/state_store.py` 259, or 344"
  - claim: "The strict reading makes no such call, testing the marker itself instead"
    source: "`nexus/infrastructure/wal.py` 132 into 137-139"
  - claim: "A write into a file whose marker is wrong is refused where the file is big enough to hold one"
    source: "`nexus/infrastructure/wal.py` 66-70"
---
# The check a boot makes before reading

A check stands apart from [the two readings](the-two-readings-of-the-log.md): it raises where the file is big enough to hold the log's marker and does not hold it.

## What it lets by

A file that is not there. A file too small to hold a marker at all.

## What it raises on

A file of any real size whose opening bytes are not the marker. That is a file which is not this log: something else written to the same path, or a log whose head was overwritten.

## Where it is made

As the store is built, before the store's own first reading of the log. Again by [a recovery](what-a-recovery-takes-before-it-rebuilds.md), and again by a plain reading of the events.

The strict reading makes no such call. It tests the marker itself, and raises there, so the check exists for the roads that read tolerantly.

## Why those roads need it

The tolerant reading answers nothing for a wrong marker, which looks exactly like a log holding no records. A write into such a file is refused — but only at the first write, which may be far from the start.

The check moves that failure to the moment the store is built, where it can be read as what it is.

## Related

- [The two readings of the log](the-two-readings-of-the-log.md)
- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [What a recovery takes before it rebuilds](what-a-recovery-takes-before-it-rebuilds.md)
