---
row: N8-04
baseline: 49aa659
created: 2026-10-28 18:45 UTC
modified: 2026-10-29 09:37 UTC
evidence:
  - claim: "The rewrite keeps the strategy events stamped at or after a cutoff and writes those back, dropping every other record"
    source: "`nexus/infrastructure/wal.py` 289-292 before 295-303"
  - claim: "A checkpoint rewrites the log in place, with no temporary file and no rename, and does not push the directory"
    source: "`nexus/infrastructure/wal.py` 294-303 against `nexus/infrastructure/snapshot.py` 46-51"
  - claim: "That rewrite checks the marker first, so a file carrying a marker that reads wrong raises rather than being written over; one shorter than the marker passes the check unread and is written over whatever it holds"
    source: "`nexus/infrastructure/wal.py` 287 before 294, the refusal raised at 248-250, the check passing a short file at 242-243"
  - claim: "The log is left as it was wherever the failure fell before the open that rewrites it, and cut down to however much of the rewrite had been put down wherever it fell after"
    source: "`nexus/infrastructure/snapshot.py` 45-51 before 53, the earlier failures at `nexus/infrastructure/wal.py` 287-288, the kept events filtered at 289-292, the emptying open at 294 before 295-303"
---
# How the checkpoint rewrites the log

The rewrite behind [a checkpoint](what-a-checkpoint-holds.md) empties the log file and writes the surviving records back into that same file, in place.

## What in place means

No temporary file is written and no rename happens. [The snapshot beside it](what-a-checkpoint-holds.md) is written the other way about: to a temporary file, pushed to the disk, then renamed over the old snapshot, with the directory pushed too. The log rewrite pushes the directory at no point.

So between the moment the file is emptied and the moment the last surviving record is back in it, the log on disk holds less than the host's history.

## The one guard in front of it

The rewrite reads the marker before it opens the file to empty it. A file carrying a marker that reads wrong raises, and the rewrite stops without touching it.

The guard has a gap: a file too short to carry a marker passes it unread, and is then written over whatever it held.

## What a half-finished rewrite leaves

Where the failure falls before the file is opened, the log is left exactly as it was.

Where it falls after, the log holds however much of the rewrite had been put down.

What the rewrite is putting back is [the strategy events it keeps](what-the-thirty-day-cut-leaves.md), so what a failure there loses is whichever of those had not yet gone down.

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
- [The timer that checkpoints while a host runs](the-timer-that-checkpoints-while-a-host-runs.md)

---

Created 2026-10-28 18:45 UTC · Last modified 2026-10-29 09:37 UTC
