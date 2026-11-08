---
row: N76-02
baseline: 49aa659
created: 2026-11-13 07:30 UTC
modified: 2026-11-13 07:30 UTC
evidence:
  - claim: "A record is packed as four named fields: its place in the order, its moment, its kind, and its payload"
    source: "`nexus/infrastructure/wal.py` 319-324"
  - claim: "The moment is turned into text and the kind into that kind's own value, so neither is packed as the object the host held"
    source: "`nexus/infrastructure/wal.py` 321, and 322"
  - claim: "The four are packed together and the packing's answer taken as bytes outright"
    source: "`nexus/infrastructure/wal.py` 325"
  - claim: "Forcing a folder opens it for reading alone"
    source: "`nexus/infrastructure/wal.py` 309"
  - claim: "The handle is closed in a clause that runs however the forcing ended"
    source: "`nexus/infrastructure/wal.py` 310-311, then 312-313"
---
# What packs a record and what forces a folder

[The log](how-a-record-reaches-the-log.md) reaches its file through two small routines of its own: one turns a record into bytes, the other makes a folder's own change survive a power cut.

## The four fields

A record is packed as four named fields — its place in the order, its moment, its kind, and its payload.

Because the place in the order is one of the four, a record read back carries its own position rather than depending on where in the file it was found.

## What the fields are turned into

The moment is turned into text. The kind is turned into that kind's own value. So neither is packed as the object the host held, and [a reading](the-two-readings-of-the-log.md) has to turn both back.

The payload goes in as it was handed over.

## The packing

The four are packed together, and the packing's answer is taken as bytes outright — so what the check is taken over, and what the length counts, is this one string of bytes.

## The folder forcing

Forcing a folder opens it for reading alone. The handle is closed in a clause that runs however the forcing ended, so a folder that refuses to be forced does not also leak a handle.

## Related

- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [The two readings of the log](the-two-readings-of-the-log.md)
