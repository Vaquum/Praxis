---
row: N44-01
baseline: 49aa659
created: 2026-11-12 01:30 UTC
modified: 2026-11-12 01:30 UTC
evidence:
  - claim: "Both readings answer nothing for a file that is not there"
    source: "`nexus/infrastructure/wal.py` 126-127, and 190-191"
  - claim: "Both answer nothing for a file whose marker is too short to be one"
    source: "`nexus/infrastructure/wal.py` 133-136, and 197-198"
  - claim: "A marker that is there and wrong raises on the strict reading"
    source: "`nexus/infrastructure/wal.py` 137-139"
  - claim: "The same marker answers nothing on the tolerant reading"
    source: "`nexus/infrastructure/wal.py` 197-198"
  - claim: "A record longer than the cap raises on the strict reading and ends the tolerant one quietly"
    source: "`nexus/infrastructure/wal.py` 149-154, against 209-210"
  - claim: "A record whose check does not match raises on the strict reading and ends the tolerant one quietly"
    source: "`nexus/infrastructure/wal.py` 161-163, against 217-218"
  - claim: "A tail cut short ends both quietly, each keeping what it read up to there, so long as the length it claims is within the cap"
    source: "`nexus/infrastructure/wal.py` 155-156, or 158-159, against 211-212, or 214-215, the cap tested first at 149"
---
# The two readings of the log

[The log](how-a-record-reaches-the-log.md) can be read two ways. Both walk it from the start, record by record; they part company over what to do with damage.

## Where they agree

A missing file reads as a log with no records, on both.

A file whose opening bytes are too few to be the log's marker answers nothing, on both. A fresh file and an empty one therefore read as a log with no records rather than as a problem.

A tail cut short — a record whose length runs past the end of the file, or whose bytes run out — ends both readings quietly. Each keeps the records it read before that point.

The cap is tested first, so a torn record whose claimed length is also past the cap raises on the strict reading rather than ending it.

## Where they part

A marker that is there and wrong raises on the strict reading. On the tolerant one it answers nothing at all, as though the file held no records.

A record claiming a length past the cap raises on the strict reading, and ends the tolerant one quietly.

A record whose check does not match its bytes raises on the strict reading, and ends the tolerant one quietly.

## Which is used where

A recovery reads tolerantly, so a host killed part-way through a write can still start. [The check that stands apart](the-check-a-boot-makes-before-reading.md) is what turns a wrong marker back into a failure on that road.

## Related

- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [The check a boot makes before reading](the-check-a-boot-makes-before-reading.md)
- [What a recovery takes before it rebuilds](what-a-recovery-takes-before-it-rebuilds.md)
