---
row: N9-03
baseline: 49aa659
created: 2026-11-03 15:40 UTC
modified: 2026-11-05 11:10 UTC
evidence:
  - claim: "One road through the log opens the file for writing and puts nothing in it, so the file is left empty and the marker goes with the rest"
    source: "`nexus/infrastructure/wal.py` 259 before 260-261"
  - claim: "No call to that road stands anywhere under `nexus/`"
    source: "`nexus/infrastructure/wal.py` 258-261, with no caller anywhere under `nexus/`"
  - claim: "The rewrite beside it writes a marker back at the head of what it keeps"
    source: "`nexus/infrastructure/wal.py` 294 before 295"
  - claim: "A file left that short is handed the road an append takes for a file written afresh, the length against the marker being the test that settles which"
    source: "`nexus/infrastructure/wal.py` 259 read at 66 into 81-83, against the other road at 68-73 under the test at 67"
---
# The road that empties the log

The log carries a road that empties the file outright: it opens the file for writing, puts nothing in it, and pushes the empty file to the disk.

## What it leaves behind

An empty file, the opening marker gone with everything else. [The rewrite standing beside it](how-the-checkpoint-rewrites-the-log.md) in the same module writes a marker back at the head of whatever it keeps.

## What nothing takes it

No call to this road stands anywhere under the Nexus package. [The checkpoint](what-a-checkpoint-holds.md) asks for the rewrite instead, which is why [the thirty-day cut](what-the-thirty-day-cut-leaves.md) is what a log actually gets.

## Which road the next append takes

[An append](how-a-record-reaches-the-log.md) has two of them, and a file this road emptied is handed the one that writes the file afresh. What settles that is the file being shorter than a marker, which an emptied file always is.

So the write after the emptying repairs the file rather than refusing it, and the marker goes back down with it.

## Related

- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
- [What a checkpoint holds](what-a-checkpoint-holds.md)
